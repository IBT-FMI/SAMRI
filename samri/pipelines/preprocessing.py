from os import path, listdir, getcwd, remove
try:
	from ..extra_functions import get_data_selection, get_scan, write_events_file, force_dummy_scans
except (SystemError, ValueError, ImportError):
	from samri.pipelines.extra_functions import get_data_selection, get_scan, write_events_file, force_dummy_scans

import re
import inspect
import shutil
from copy import deepcopy
from itertools import product

import nipype.interfaces.ants as ants
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
import pandas as pd
from nipype.interfaces import afni, bru2nii, fsl, nipy

from nodes import *
from utils import ss_to_path, sss_filename, fslmaths_invert_values
from utils import STIM_PROTOCOL_DICTIONARY
from samri.utilities import N_PROCS

DUMMY_SCANS=10
N_PROCS=max(N_PROCS-4, 2)

#set all outputs to compressed NIfTI
afni.base.AFNICommand.set_default_output_type('NIFTI_GZ')
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

#relative paths
thisscriptspath = path.dirname(path.realpath(__file__))
scan_classification_file_path = path.join(thisscriptspath,"scan_type_classification.csv")

def bruker(measurements_base,
	functional_scan_types=[],
	structural_scan_types=[],
	sessions=[],
	subjects=[],
	measurements=[],
	exclude_subjects=[],
	exclude_measurements=[],
	actual_size=False,
	functional_blur_xy=False,
	functional_registration_method="structural",
	highpass_sigma=225,
	lowpass_sigma=None,
	negative_contrast_agent=False,
	n_procs=N_PROCS,
	realign="time",
	registration_mask=False,
	template="/home/chymera/ni_data/templates/ds_QBI_chr.nii.gz",
	tr=1,
	very_nasty_bruker_delay_hack=False,
	workflow_name="generic",
	keep_work=False,
	autorotate=False,
	strict=False,
	):
	'''

	realign: {"space","time","spacetime",""}
		Parameter that dictates slictiming correction and realignment of slices. "time" (FSL.SliceTimer) is default, since it works safely. Use others only with caution!

	'''

	measurements_base = path.abspath(path.expanduser(measurements_base))

	#select all functional/sturctural scan types unless specified
	if not functional_scan_types or not structural_scan_types:
		scan_classification = pd.read_csv(scan_classification_file_path)
		if not functional_scan_types:
			functional_scan_types = list(scan_classification[(scan_classification["categories"] == "functional")]["scan_type"])
		if not structural_scan_types:
			structural_scan_types = list(scan_classification[(scan_classification["categories"] == "structural")]["scan_type"])

	#hack to allow structural scan type disabling:
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

	# we currently only support one structural scan type per session
	if structural_registration and structural_scan_types:
		structural_scan_types = [structural_scan_types[0]]

	# we start to define nipype workflow elements (nodes, connections, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_session']), name="infosource")
	infosource.iterables = [('subject_session', subjects_sessions)]

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type']))
	if not strict:
		get_f_scan.inputs.ignore_exception = True
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.measurements_base = measurements_base
	get_f_scan.iterables = ("scan_type", functional_scan_types)

	f_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="f_bru2nii")
	f_bru2nii.inputs.actual_size=actual_size

	dummy_scans = pe.Node(name='dummy_scans', interface=util.Function(function=force_dummy_scans,input_names=inspect.getargspec(force_dummy_scans)[0], output_names=['out_file']))
	dummy_scans.inputs.desired_dummy_scans = DUMMY_SCANS

	events_file = pe.Node(name='events_file', interface=util.Function(function=write_events_file,input_names=inspect.getargspec(write_events_file)[0], output_names=['out_file']))
	events_file.inputs.dummy_scans_ms = DUMMY_SCANS * tr * 1000
	events_file.inputs.stim_protocol_dictionary = STIM_PROTOCOL_DICTIONARY
	events_file.inputs.very_nasty_bruker_delay_hack = very_nasty_bruker_delay_hack

	bandpass = pe.Node(interface=fsl.maths.TemporalFilter(), name="bandpass")
	bandpass.inputs.highpass_sigma = highpass_sigma
	if lowpass_sigma:
		bandpass.inputs.lowpass_sigma = lowpass_sigma
	else:
		bandpass.inputs.lowpass_sigma = tr

	bids_filename = pe.Node(name='bids_filename', interface=util.Function(function=sss_filename,input_names=inspect.getargspec(sss_filename)[0], output_names=['filename']))

	bids_stim_filename = pe.Node(name='bids_stim_filename', interface=util.Function(function=sss_filename,input_names=inspect.getargspec(sss_filename)[0], output_names=['filename']))
	bids_stim_filename.inputs.suffix = "events"
	bids_stim_filename.inputs.extension = ".tsv"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	if not strict:
		datasink.inputs.ignore_exception = True
	datasink.inputs.base_directory = path.join(measurements_base,"preprocessing",workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, get_f_scan, [('subject_session', 'selector')]),
		(infosource, bids_stim_filename, [('subject_session', 'subject_session')]),
		(get_f_scan, bids_stim_filename, [('scan_type', 'scan')]),
		(get_f_scan, f_bru2nii, [('scan_path', 'input_dir')]),
		(f_bru2nii, dummy_scans, [('nii_file', 'in_file')]),
		(get_f_scan, dummy_scans, [('scan_path', 'scan_dir')]),
		(get_f_scan, events_file, [
			('scan_type', 'scan_type'),
			('scan_path', 'scan_dir')
			]),
		(events_file, datasink, [('out_file', 'func.@events')]),
		(bids_stim_filename, events_file, [('filename', 'out_file')]),
		(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
		(infosource, bids_filename, [('subject_session', 'subject_session')]),
		(get_f_scan, bids_filename, [('scan_type', 'scan')]),
		(bids_filename, bandpass, [('filename', 'out_file')]),
		(bandpass, datasink, [('out_file', 'func')]),
		]

	if realign == "space":
		realigner = pe.Node(interface=spm.Realign(), name="realigner")
		realigner.inputs.register_to_mean = True
		workflow_connections.extend([
			(dummy_scans, realigner, [('out_file', 'in_file')]),
			])

	elif realign == "spacetime":
		realigner = pe.Node(interface=nipy.SpaceTimeRealigner(), name="realigner")
		realigner.inputs.slice_times = "asc_alt_2"
		realigner.inputs.tr = tr
		realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
		workflow_connections.extend([
			(dummy_scans, realigner, [('out_file', 'in_file')]),
			])

	elif realign == "time":
		realigner = pe.Node(interface=fsl.SliceTimer(), name="slicetimer")
		realigner.inputs.time_repetition = tr
		workflow_connections.extend([
			(dummy_scans, realigner, [('out_file', 'in_file')]),
			])

	#ADDING SELECTABLE NODES AND EXTENDING WORKFLOW AS APPROPRIATE:
	if actual_size:
		s_biascorrect, f_biascorrect = real_size_nodes()
	else:
		s_biascorrect, f_biascorrect = inflated_size_nodes()

	if structural_scan_types:
		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_scan, input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type']))
		if not strict:
			get_s_scan.inputs.ignore_exception = True
		get_s_scan.inputs.data_selection = data_selection
		get_s_scan.inputs.measurements_base = measurements_base
		get_s_scan.iterables = ("scan_type", structural_scan_types)

		s_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="s_bru2nii")
		s_bru2nii.inputs.force_conversion=True
		s_bru2nii.inputs.actual_size=actual_size

		s_bids_filename = pe.Node(name='s_bids_filename', interface=util.Function(function=sss_filename,input_names=inspect.getargspec(sss_filename)[0], output_names=['filename']))
		s_bids_filename.inputs.scan_prefix = False

		if actual_size:
			s_register, s_warp, _, _ = DSURQEc_structural_registration(template, registration_mask)
			#TODO: incl. in func registration
			if autorotate:
				workflow_connections.extend([
					(s_biascorrect, s_rotated, [('output_image', 'out_file')]),
					(s_rotated, s_register, [('out_file', 'moving_image')]),
					])
			else:
				workflow_connections.extend([
					(s_biascorrect, s_register, [('output_image', 'moving_image')]),
					(s_register, s_warp, [('composite_transform', 'transforms')]),
					(s_bru2nii, s_warp, [('nii_file', 'input_image')]),
					(s_warp, datasink, [('output_image', 'anat')]),
					])
			s_reg_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="s_reg_biascorrect")
			s_reg_biascorrect.inputs.dimension = 3
			s_reg_biascorrect.inputs.bspline_fitting_distance = 95
			s_reg_biascorrect.inputs.shrink_factor = 2
			s_reg_biascorrect.inputs.n_iterations = [500,500,500,500]
			s_reg_biascorrect.inputs.convergence_threshold = 1e-14

			s_cutoff = pe.Node(interface=fsl.ImageMaths(), name="s_cutoff")
			s_cutoff.inputs.op_string = "-thrP 20 -uthrp 98"

			s_BET = pe.Node(interface=fsl.BET(), name="s_BET")
			s_BET.inputs.mask = True
			s_BET.inputs.frac = 0.3
			s_BET.inputs.robust = True

			s_mask = pe.Node(interface=fsl.ApplyMask(), name="s_mask")
			s_register, s_warp, f_warp = structural_registration(template)

			workflow_connections.extend([
				(s_bru2nii, s_reg_biascorrect, [('nii_file', 'input_image')]),
				(s_reg_biascorrect, s_cutoff, [('output_image', 'in_file')]),
				(s_cutoff, s_BET, [('out_file', 'in_file')]),
				(s_biascorrect, s_mask, [('output_image', 'in_file')]),
				(s_BET, s_mask, [('mask_file', 'mask_file')]),
				])

			#TODO: incl. in func registration
			if autorotate:
				workflow_connections.extend([
					(s_mask, s_rotated, [('out_file', 'out_file')]),
					(s_rotated, s_register, [('out_file', 'moving_image')]),
					])
			else:
				workflow_connections.extend([
					(s_mask, s_register, [('out_file', 'moving_image')]),
					(s_register, s_warp, [('composite_transform', 'transforms')]),
					(s_bru2nii, s_warp, [('nii_file', 'input_image')]),
					(s_warp, datasink, [('output_image', 'anat')]),
					])


		if autorotate:
			s_rotated = autorotate(template)

		workflow_connections.extend([
			(infosource, get_s_scan, [('subject_session', 'selector')]),
			(infosource, s_bids_filename, [('subject_session', 'subject_session')]),
			(get_s_scan, s_bru2nii, [('scan_path','input_dir')]),
			(get_s_scan, s_bids_filename, [('scan_type', 'scan')]),
			(s_bids_filename, s_warp, [('filename','output_image')]),
			(s_bru2nii, s_biascorrect, [('nii_file', 'input_image')]),
			])



	if functional_registration_method == "structural":
		if not structural_scan_types:
			raise ValueError('The option `registration="structural"` requires there to be a structural scan type.')
		workflow_connections.extend([
			(s_register, f_warp, [('composite_transform', 'transforms')]),
			])
		if realign == "space":
			workflow_connections.extend([
				(realigner, f_warp, [('realigned_files', 'input_image')]),
				])
		elif realign == "spacetime":
			workflow_connections.extend([
				(realigner, f_warp, [('out_file', 'input_image')]),
				])
		elif realign == "time":
			workflow_connections.extend([
				(realigner, f_warp, [('slice_time_corrected_file', 'input_image')]),
				])
		else:
			workflow_connections.extend([
				(dummy_scans, f_warp, [('out_file', 'input_image')]),
				])


	if functional_registration_method == "composite":
		if not structural_scan_types:
			raise ValueError('The option `registration="composite"` requires there to be a structural scan type.')
		_, _, f_register, f_warp = DSURQEc_structural_registration(template, registration_mask)

		temporal_mean = pe.Node(interface=fsl.MeanImage(), name="temporal_mean")

		merge = pe.Node(util.Merge(2), name='merge')

		workflow_connections.extend([
			(temporal_mean, f_biascorrect, [('out_file', 'input_image')]),
			(f_biascorrect, f_register, [('output_image', 'moving_image')]),
			(s_biascorrect, f_register, [('output_image', 'fixed_image')]),
			(f_register, merge, [('composite_transform', 'in1')]),
			(s_register, merge, [('composite_transform', 'in2')]),
			(merge, f_warp, [('out', 'transforms')]),
			])
		if realign == "space":
			workflow_connections.extend([
				(realigner, temporal_mean, [('realigned_files', 'in_file')]),
				(realigner, f_warp, [('realigned_files', 'input_image')]),
				])
		elif realign == "spacetime":
			workflow_connections.extend([
				(realigner, temporal_mean, [('out_file', 'in_file')]),
				(realigner, f_warp, [('out_file', 'input_image')]),
				])
		elif realign == "time":
			workflow_connections.extend([
				(realigner, temporal_mean, [('slice_time_corrected_file', 'in_file')]),
				(realigner, f_warp, [('slice_time_corrected_file', 'input_image')]),
				])
		else:
			workflow_connections.extend([
				(dummy_scans, temporal_mean, [('out_file', 'in_file')]),
				(dummy_scans, f_warp, [('out_file', 'input_image')]),
				])

	elif functional_registration_method == "functional":
		f_register, f_warp = functional_registration(template)

		temporal_mean = pe.Node(interface=fsl.MeanImage(), name="temporal_mean")

		#f_cutoff = pe.Node(interface=fsl.ImageMaths(), name="f_cutoff")
		#f_cutoff.inputs.op_string = "-thrP 30"

		#f_BET = pe.Node(interface=fsl.BET(), name="f_BET")
		#f_BET.inputs.mask = True
		#f_BET.inputs.frac = 0.5

		workflow_connections.extend([
			(temporal_mean, f_biascorrect, [('out_file', 'input_image')]),
			#(f_biascorrect, f_cutoff, [('output_image', 'in_file')]),
			#(f_cutoff, f_BET, [('out_file', 'in_file')]),
			#(f_BET, f_register, [('out_file', 'moving_image')]),
			(f_biascorrect, f_register, [('output_image', 'moving_image')]),
			(f_register, f_warp, [('composite_transform', 'transforms')]),
			])
		if realign:
			workflow_connections.extend([
				(realigner, temporal_mean, [('out_file', 'in_file')]),
				(realigner, f_warp, [('out_file', 'input_image')]),
				])
		else:
			workflow_connections.extend([
				(dummy_scans, temporal_mean, [('out_file', 'input_image')]),
				(dummy_scans, f_warp, [('out_file', 'input_image')]),
				])


	invert = pe.Node(interface=fsl.ImageMaths(), name="invert")
	if functional_blur_xy and negative_contrast_agent:
		blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
		blur.inputs.fwhmxy = functional_blur_xy
		workflow_connections.extend([
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, invert, [(('out_file', fslmaths_invert_values), 'op_string')]),
			(blur, invert, [('out_file', 'in_file')]),
			(invert, bandpass, [('out_file', 'in_file')]),
			])
	elif functional_blur_xy:
		blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
		blur.inputs.fwhmxy = functional_blur_xy
		workflow_connections.extend([
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, bandpass, [('out_file', 'in_file')]),
			])
	elif negative_contrast_agent:
		blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
		blur.inputs.fwhmxy = functional_blur_xy
		workflow_connections.extend([
			(f_warp, invert, [(('output_image', fslmaths_invert_values), 'op_string')]),
			(f_warp, invert, [('output_image', 'in_file')]),
			(invert, bandpass, [('out_file', 'in_file')]),
			])
	else:
		workflow_connections.extend([
			(f_warp, bandpass, [('output_image', 'in_file')]),
			])

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = path.join(measurements_base,"preprocessing")
	workflow.config = {"execution": {"crashdump_dir": path.join(measurements_base,"preprocessing/crashdump")}}
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : n_procs})
	if not keep_work:
		shutil.rmtree(path.join(workflow.base_dir,workdir_name))

if __name__ == "__main__":
	bruker("/home/chymera/ni_data/ofM.dr/",
		exclude_measurements=['20151027_121613_4013_1_1'],
		functional_scan_types=["EPI_CBV_chr_longSOA","EPI_CBV_jb_long"],
		subjects=["5703","5704","5706",],
		# subjects=["4007","4008","4011","4012","5689","5690","5691"],
		workflow_name="composite",
		very_nasty_bruker_delay_hack=True,
		negative_contrast_agent=True,
		functional_blur_xy=4,
		functional_registration_method="composite",
		keep_work=True,
		template="~/ni_data/templates/ds_QBI_chr.nii.gz",
		)
