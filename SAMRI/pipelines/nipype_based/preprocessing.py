from os import path, listdir, getcwd, remove
if not __package__:
	import sys
	pkg_root = path.abspath(path.join(path.dirname(path.realpath(__file__)),"../../.."))
	sys.path.insert(0, pkg_root)
from SAMRI.pipelines.extra_functions import get_data_selection, get_scan

import inspect
import re
import pandas as pd
import nipype.interfaces.ants as ants
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from copy import deepcopy
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ImageMaths, FSLCommand
from nipype.interfaces.fsl.maths import TemporalFilter
from nipype.interfaces.nipy import SpaceTimeRealigner
from nipype.interfaces.afni import Bandpass
from nipype.interfaces.afni.base import AFNICommand
from nipype.interfaces.afni.preprocess import BlurToFWHM
from nipype.interfaces.dcmstack import DcmStack
from extra_interfaces import DcmToNii, MEICA, VoxelResize, Bru2, GetBrukerTiming
from nodes import ants_standard_registration_warp
from itertools import product

#set all outputs to compressed NIfTI
AFNICommand.set_default_output_type('NIFTI_GZ')
FSLCommand.set_default_output_type('NIFTI_GZ')

#relative paths
thisscriptspath = path.dirname(path.realpath(__file__))
scan_classification_file_path = path.join(thisscriptspath,"scan_type_classification.csv")

def bru_preproc_lite(measurements_base, functional_scan_types=[], structural_scan_types=[], tr=1, conditions=[], subjects=[], exclude_subjects=[], measurements=[], exclude_measurements=[], actual_size=False, realign=False):

	#select all functional/sturctural scan types unless specified
	if not functional_scan_types or not structural_scan_types:
		 scan_classification = pd.read_csv(scan_classification_file_path)
		 if not functional_scan_types:
			 functional_scan_types = list(scan_classification[(scan_classification["categories"] == "functional")]["scan_type"])
		 if not structural_scan_types:
			 structural_scan_types = list(scan_classification[(scan_classification["categories"] == "structural")]["scan_type"])

	# define measurement directories to be processed, and populate the list either with the given include_measurements, or with an intelligent selection
	scan_types = functional_scan_types[:]
	scan_types.extend(structural_scan_types)
	data_selection=get_data_selection(measurements_base, conditions, scan_types=scan_types, subjects=subjects, exclude_subjects=exclude_subjects, measurements=measurements, exclude_measurements=exclude_measurements)
	if not subjects:
		subjects = set(list(data_selection["subject"]))
	if not conditions:
		conditions = set(list(data_selection["condition"]))

	infosource = pe.Node(interface=util.IdentityInterface(fields=['condition','subject']), name="infosource")
	infosource.iterables = [('subject',subjects),('condition',conditions)]

	get_functional_scan = pe.Node(name='get_functional_scan', interface=util.Function(function=get_scan,input_names=["measurements_base","data_selection","condition","subject","scan_type"], output_names=['scan_path','scan_type']))
	get_functional_scan.inputs.data_selection = data_selection
	get_functional_scan.inputs.measurements_base = measurements_base
	get_functional_scan.iterables = ("scan_type", functional_scan_types)

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	functional_bru2nii.inputs.actual_size=actual_size

	if structural_scan_types:
		get_structural_scan = pe.Node(name='get_structural_scan', interface=util.Function(function=get_scan,input_names=["measurements_base","data_selection","condition","subject","scan_type"], output_names=['scan_path','scan_type']))
		get_structural_scan.inputs.data_selection = data_selection
		get_structural_scan.inputs.measurements_base = measurements_base
		get_structural_scan.iterables = ("scan_type", structural_scan_types)

		structural_bru2nii = pe.Node(interface=Bru2(), name="structural_bru2nii")
		structural_bru2nii.inputs.force_conversion=True
		structural_bru2nii.inputs.actual_size=actual_size

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	workflow = pe.Workflow(name="PreprocessingLite")

	workflow_connections = [
		(infosource, get_functional_scan, [('condition', 'condition'),('subject', 'subject')]),
		(get_functional_scan, functional_bru2nii, [('scan_path', 'input_dir')]),
		]
	if realign:
		workflow_connections.extend([
			(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
			])
	if structural_scan_types:
		workflow_connections.extend([
			(infosource, get_structural_scan, [('condition', 'condition'),('subject', 'subject')]),
			(get_structural_scan, structural_bru2nii, [('scan_path','input_dir')]),
			])

	workflow.connect(workflow_connections)
	# workflow.run(plugin="MultiProc")
	return workflow

def bru_preproc(measurements_base, functional_scan_types, structural_scan_types=[], workflow_name="generic", tr=1, conditions=[], subjects=[], exclude_subjects=[], measurements=[], exclude_measurements=[], actual_size=False, template="/home/chymera/NIdata/templates/ds_QBI_chr.nii.gz", blur_xy=False, structural_registration=False, quiet=True):

	#select all functional/sturctural scan types unless specified
	if not functional_scan_types or not structural_scan_types:
		 scan_classification = pd.read_csv(scan_classification_file_path)
		 if not functional_scan_types:
			 functional_scan_types = list(scan_classification[(scan_classification["categories"] == "functional")]["scan_type"])
		 if not structural_scan_types:
			 structural_scan_types = list(scan_classification[(scan_classification["categories"] == "structural")]["scan_type"])

	#hack to allow structural scan type disaling:
	if structural_scan_types == -1:
		structural_scan_types = []

	# define measurement directories to be processed, and populate the list either with the given include_measurements, or with an intelligent selection
	scan_types = deepcopy(functional_scan_types)
	scan_types.extend(structural_scan_types)
	data_selection=get_data_selection(measurements_base, conditions, scan_types=scan_types, subjects=subjects, exclude_subjects=exclude_subjects, measurements=measurements, exclude_measurements=exclude_measurements)
	if not subjects:
		subjects = set(list(data_selection["subject"]))
	if not conditions:
		conditions = set(list(data_selection["condition"]))

	if structural_registration:
		structural_scan_types = structural_scan_types[0]

	# here we start to define the nipype workflow elements (nodes, connectons, meta)
	conditions_subjects = data_selection[["condition","subject"]].drop_duplicates().values.tolist()
	infosource = pe.Node(interface=util.IdentityInterface(fields=['condition_subject']), name="infosource")
	infosource.iterables = [('condition_subject', conditions_subjects)]

	get_functional_scan = pe.Node(name='get_functional_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type']))
	get_functional_scan.inputs.data_selection = data_selection
	get_functional_scan.inputs.measurements_base = measurements_base
	get_functional_scan.iterables = ("scan_type", functional_scan_types)

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	functional_bru2nii.inputs.actual_size=actual_size

	timing_metadata = pe.Node(interface=GetBrukerTiming(), name="timing_metadata")

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = 1.
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	temporal_mean = pe.Node(interface=MeanImage(), name="temporal_mean")

	functional_register, functional_warp = ants_standard_registration_warp(template, "functional_register", "functional_warp")

	functional_FAST = pe.Node(interface=FAST(), name="functional_FAST")
	functional_FAST.inputs.segments = False
	functional_FAST.inputs.output_biascorrected = True
	functional_FAST.inputs.bias_iters = 8

	functional_cutoff = pe.Node(interface=ImageMaths(), name="functional_cutoff")
	functional_cutoff.inputs.op_string = "-thrP 30"

	functional_BET = pe.Node(interface=BET(), name="functional_BET")
	functional_BET.inputs.mask = True
	functional_BET.inputs.frac = 0.5

	functional_bandpass = pe.Node(interface=TemporalFilter(), name="functional_bandpass")
	functional_bandpass.inputs.highpass_sigma = 180
	functional_bandpass.inputs.lowpass_sigma = 1

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(measurements_base,"preprocessing",workflow_name,"results")
	#remove iterfield names
	# datasink.inputs.substitutions = [('_condition_', ''),('_subject_', '.')]

	workflow_connections = [
		(infosource, get_functional_scan, [('condition_subject', 'selector')]),
		(get_functional_scan, functional_bru2nii, [('scan_path', 'input_dir')]),
		(get_functional_scan, timing_metadata, [('scan_path', 'scan_directory')]),
		(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
		(realigner, temporal_mean, [('out_file', 'in_file')]),
		(temporal_mean, functional_FAST, [('out_file', 'in_files')]),
		(functional_FAST, functional_cutoff, [('restored_image', 'in_file')]),
		(functional_cutoff, functional_BET, [('out_file', 'in_file')]),
		(functional_BET, functional_register, [('out_file', 'moving_image')]),
		(functional_register, functional_warp, [('composite_transform', 'transforms')]),
		(realigner, functional_warp, [('out_file', 'input_image')]),
		(functional_bandpass, datasink, [('out_file', 'func')]),
		]

	if blur_xy:
		blur = pe.Node(interface=BlurToFWHM(), name="blur")
		blur.inputs.fwhmxy = blur_xy
		workflow_connections.extend([
			(functional_warp, blur, [('output_image', 'in_file')]),
			(blur, functional_bandpass, [('out_file', 'in_file')]),
			])
	else:
		workflow_connections.extend([
			(functional_warp, functional_bandpass, [('output_image', 'in_file')]),
			])

	if structural_scan_types:
		get_structural_scan = pe.Node(name='get_structural_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type']))
		get_structural_scan.inputs.data_selection = data_selection
		get_structural_scan.inputs.measurements_base = measurements_base
		get_structural_scan.iterables = ("scan_type", structural_scan_types)

		structural_bru2nii = pe.Node(interface=Bru2(), name="structural_bru2nii")
		structural_bru2nii.inputs.force_conversion=True
		structural_bru2nii.inputs.actual_size=actual_size

		structural_FAST = pe.Node(interface=FAST(), name="structural_FAST")
		structural_FAST.inputs.segments = False
		structural_FAST.inputs.output_biascorrected = True
		structural_FAST.inputs.bias_iters = 8

		structural_cutoff = pe.Node(interface=ImageMaths(), name="structural_cutoff")
		structural_cutoff.inputs.op_string = "-thrP 45"
		structural_register, structural_warp = ants_standard_registration_warp(template, "structural_register", "structural_warp")

		structural_BET = pe.Node(interface=BET(), name="structural_BET")
		structural_BET.inputs.mask = True
		structural_BET.inputs.frac = 0.5


		workflow_connections.extend([
			(infosource, get_structural_scan, [('condition_subject', 'selector')]),
			(get_structural_scan, structural_bru2nii, [('scan_path','input_dir')]),
			(structural_bru2nii, structural_FAST, [('nii_file', 'in_files')]),
			(structural_FAST, structural_cutoff, [('restored_image', 'in_file')]),
			(structural_cutoff, structural_BET, [('out_file', 'in_file')]),
			(structural_BET, structural_register, [('out_file', 'moving_image')]),
			(structural_register, datasink, [('warped_image', 'anat')]),
			])

		if structural_registration:
			structural_bandpass = pe.Node(interface=TemporalFilter(), name="structural_bandpass")
			structural_bandpass.inputs.highpass_sigma = 180
			structural_bandpass.inputs.lowpass_sigma = 1

			workflow_connections.extend([
			(structural_register, structural_warp, [('composite_transform', 'transforms')]),
			(realigner, structural_warp, [('out_file', 'input_image')]),
			])

			if blur_xy:
				structural_blur = pe.Node(interface=BlurToFWHM(), name="blur")
				blur.inputs.fwhmxy = blur_xy
				workflow_connections.extend([
					(structural_warp, structural_blur, [('output_image', 'in_file')]),
					(structural_blur, structural_bandpass, [('out_file', 'in_file')]),
					])
			else:
				workflow_connections.extend([
					(structural_warp, structural_bandpass, [('output_image', 'in_file')]),
					])


	workflow = pe.Workflow(name=workflow_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = path.join(measurements_base,"preprocessing")
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workflow_name,"graph.dot"), graph2use="hierarchical", format="png")
	if quiet:
		try:
			workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
		except RuntimeError:
			print "WARNING: Some expected scans have not been found (or another TypeError has occured)."
		for f in listdir(getcwd()):
			if re.search("crash.*?get_structural_scan|get_functional_scan.*", f):
				remove(path.join(getcwd(), f))
	else:
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})

if __name__ == "__main__":
	# bru_preproc_lite(measurements_base="/mnt/data/NIdata/ofM.erc/", functional_scan_types=["EPI_CBV_alej","EPI_CBV_jin6","EPI_CBV_jin10","EPI_CBV_jin20","EPI_CBV_jin40","EPI_CBV_jin60"], structural_scan_type="T2_TurboRARE", conditions=["ERC_ofM"], include_subjects=["5502","5503"])
	bru_preproc("/home/chymera/NIdata/ofM.erc/", ["EPI_CBV_jin10","EPI_CBV_jin60"], conditions=["ERC_ofM","ERC_ofM_r1"], structural_scan_types=-1)
