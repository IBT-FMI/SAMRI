from os import path, listdir, getcwd, remove
if not __package__:
	import sys
	pkg_root = path.abspath(path.join(path.dirname(path.realpath(__file__)),"../../.."))
	sys.path.insert(0, pkg_root)
try:
	from ..extra_functions import get_data_selection, get_scan, write_events_file
except ValueError:
	from samri.pipelines.extra_functions import get_data_selection, get_scan, write_events_file

import inspect
import re
import shutil
from copy import deepcopy
from itertools import product

import argh
import nipype.interfaces.ants as ants
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
import pandas as pd
from nipype.interfaces import afni, fsl, nipy

from nodes import functional_registration, structural_registration, composite_registration
from utils import ss_to_path, sss_filename, fslmaths_invert_values
from utils import STIM_PROTOCOL_DICTIONARY
from utils import Bru2, MELODIC

#set all outputs to compressed NIfTI
afni.base.AFNICommand.set_default_output_type('NIFTI_GZ')
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

#relative paths
thisscriptspath = path.dirname(path.realpath(__file__))
scan_classification_file_path = path.join(thisscriptspath,"..","scan_type_classification.csv")

@argh.arg('-f', '--functional_scan_types', nargs='+', type=str)
@argh.arg('--structural_scan_types', nargs='+', type=str)
@argh.arg('--sessions', nargs='+', type=str)
@argh.arg('--subjects', nargs='+', type=str)
@argh.arg('--exclude_subjects', nargs='+', type=str)
@argh.arg('--measurements', nargs='+', type=str)
@argh.arg('--exclude_measurements', nargs='+', type=str)
def diagnose(measurements_base,
	functional_scan_types=[],
	structural_scan_types=[],
	sessions=[],
	subjects=[],
	measurements=[],
	exclude_subjects=[],
	exclude_measurements=[],
	actual_size=False,
	components=None,
	keep_work=False,
	loud=False,
	n_procs=8,
	realign=False,
	tr=1,
	workflow_name="diagnostic"
	):

	measurements_base = path.abspath(path.expanduser(measurements_base))

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
	data_selection=get_data_selection(measurements_base, sessions, scan_types=scan_types, subjects=subjects, exclude_subjects=exclude_subjects, measurements=measurements, exclude_measurements=exclude_measurements)
	if not subjects:
		subjects = set(list(data_selection["subject"]))
	if not sessions:
		sessions = set(list(data_selection["session"]))

	# here we start to define the nipype workflow elements (nodes, connectons, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_session']), name="infosource")
	infosource.iterables = [('subject_session', subjects_sessions)]

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type']))
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.measurements_base = measurements_base
	get_f_scan.iterables = ("scan_type", functional_scan_types)

	f_bru2nii = pe.Node(interface=Bru2(), name="f_bru2nii")
	f_bru2nii.inputs.actual_size=actual_size

	bids_filename = pe.Node(name='bids_filename', interface=util.Function(function=sss_filename,input_names=inspect.getargspec(sss_filename)[0], output_names=['filename']))
	bids_filename.inputs.suffix = "MELODIC"
	bids_filename.inputs.extension = ""

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(measurements_base,workflow_name)
	datasink.inputs.parameterization = False

	melodic = pe.Node(interface=MELODIC(), name="melodic")
	melodic.inputs.tr_sec = tr
	melodic.inputs.report = True
	if components:
		melodic.inputs.dim = components

	workflow_connections = [
		(infosource, get_f_scan, [('subject_session', 'selector')]),
		(get_f_scan, f_bru2nii, [('scan_path', 'input_dir')]),
		(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
		(infosource, bids_filename, [('subject_session', 'subject_session')]),
		(get_f_scan, bids_filename, [('scan_type', 'scan')]),
		(bids_filename, melodic, [('filename', 'out_dir')]),
		(melodic, datasink, [('out_dir', 'func')]),
		]

	#ADDING SELECTABLE NODES AND EXTENDING WORKFLOW AS APPROPRIATE:
	if structural_scan_types:
		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type']))
		get_s_scan.inputs.data_selection = data_selection
		get_s_scan.inputs.measurements_base = measurements_base
		get_s_scan.iterables = ("scan_type", structural_scan_types)

		s_bru2nii = pe.Node(interface=Bru2(), name="s_bru2nii")
		s_bru2nii.inputs.force_conversion=True
		s_bru2nii.inputs.actual_size=actual_size

		s_bids_filename = pe.Node(name='s_bids_filename', interface=util.Function(function=sss_filename,input_names=inspect.getargspec(sss_filename)[0], output_names=['filename']))
		s_bids_filename.inputs.extension = ""
		s_bids_filename.inputs.scan_prefix = False

		workflow_connections.extend([
			(infosource, get_s_scan, [('subject_session', 'selector')]),
			(infosource, s_bids_filename, [('subject_session', 'subject_session')]),
			(get_s_scan, s_bru2nii, [('scan_path','input_dir')]),
			(get_s_scan, s_bids_filename, [('scan_type', 'scan')]),
			(s_bids_filename, s_bru2nii, [('filename','output_filename')]),
			(s_bru2nii, datasink, [('nii_file', 'anat')]),
			])

	if realign:
		realigner = pe.Node(interface=nipy.SpaceTimeRealigner(), name="realigner")
		realigner.inputs.slice_times = "asc_alt_2"
		realigner.inputs.tr = tr
		realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
		workflow_connections.extend([
			(f_bru2nii, realigner, [('nii_file', 'in_file')]),
			(realigner, melodic, [('out_file', 'in_files')]),
			])
	else:
		workflow_connections.extend([
			(f_bru2nii, melodic, [('nii_file', 'in_files')]),
			])

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = path.join(measurements_base)
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	if not loud:
		try:
			workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : n_procs})
		except RuntimeError:
			print("WARNING: Some expected scans have not been found (or another TypeError has occured).")
		for f in listdir(getcwd()):
			if re.search("crash.*?get_s_scan|get_f_scan.*?pklz", f):
				remove(path.join(getcwd(), f))
	else:
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : n_procs})
	if not keep_work:
		shutil.rmtree(path.join(workflow.base_dir,workdir_name))
