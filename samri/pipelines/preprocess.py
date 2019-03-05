import argh
import inspect
import json
import os
import re
import shutil
from copy import deepcopy
from itertools import product
from os import path

import multiprocessing as mp
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import pandas as pd
from nipype.interfaces import ants, afni, bru2nii, fsl, nipy
import nipype.interfaces.ants.legacy as antslegacy

from samri.fetch.templates import fetch_rat_waxholm
from samri.pipelines.extra_functions import get_bids_scan, write_bids_events_file, force_dummy_scans, BIDS_METADATA_EXTRACTION_DICTS
from samri.pipelines.extra_interfaces import VoxelResize, FSLOrient
from samri.pipelines.nodes import *
from samri.pipelines.utils import bids_data_selection, fslmaths_invert_values, ss_to_path, GENERIC_PHASES
from samri.utilities import N_PROCS

DUMMY_SCANS=10
N_PROCS=max(N_PROCS-2, 1)

#set all outputs to compressed NIfTI
afni.base.AFNICommand.set_default_output_type('NIFTI_GZ')
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

def divideby_10(x):
	"""This is a wrapper function needed in order for nipype workflow connections to accept inline division."""
	return x/10.

@argh.arg('-f','--functional-match', type=json.loads)
@argh.arg('-s','--structural-match', type=json.loads)
@argh.arg('-m','--registration-mask')
def legacy(bids_base, template,
	debug=False,
	functional_blur_xy=False,
	functional_match={},
	keep_work=False,
	n_jobs=False,
	n_jobs_percentage=0.8,
	out_base=None,
	realign="time",
	registration_mask=False,
	sessions=[],
	structural_match={},
	subjects=[],
	tr=1,
	workflow_name='legacy',
	):
	'''
	Legacy realignment and registration workflow representative of the tweaks and workarounds commonly used in the pre-SAMRI period.

	Parameters
	----------
	bids_base : str
		Path to the BIDS data set root.
	template : str
		Path to the template to register the data to.
	debug : bool, optional
		Whether to enable nipype debug mode.
		This increases logging.
	functional_blur_xy : float, optional
		Factor by which to smooth data in the xy-plane; if parameter evaluates to false, no smoothing will be applied.
		Ideally this value should correspond to the resolution or smoothness in the z-direction (assuing z represents the lower-resolution slice-encoding direction).
	functional_match : dict, optional
		Dictionary specifying a whitelist to use for functional data inclusion into the workflow; if dictionary is empty no whitelist is present and all data will be considered.
		The dictionary should have keys which are 'acquisition', 'task', or 'modality', and values which are lists of acceptable strings for the respective BIDS field.
	keep_work : bool, str
		Whether to keep the work directory after workflow conclusion (this directory contains all the intermediary processing commands, inputs, and outputs --- it is invaluable for debugging but many times larger in size than the actual output).
	n_jobs : int, optional
		Number of processors to maximally use for the workflow; if unspecified a best guess will be estimate based on `n_jobs_percentage` and hardware (but not on current load).
	n_jobs_percentage : float, optional
		Percentage of available processors (as in available hardware, not available free load) to maximally use for the workflow (this is overriden by `n_jobs`).
	out_base : str, optional
		Output base directory --- inside which a directory named `workflow_name` (as well as associated directories) will be created.
	realign : {"space","time","spacetime",""}, optional
		Parameter that dictates slictiming correction and realignment of slices. "time" (FSL.SliceTimer) is default, since it works safely. Use others only with caution!
	registration_mask : str, optional
		Mask to use for the registration process.
		This mask will constrain the area for similarity metric evaluation, but the data will not be cropped.
	sessions : list, optional
		A whitelist of sessions to include in the workflow, if the list is empty there is no whitelist and all sessions will be considered.
	structural_match : dict, optional
		Dictionary specifying a whitelist to use for structural data inclusion into the workflow; if dictionary is empty no whitelist is present and all data will be considered.
		The dictionary should have keys which are 'acquisition', or 'modality', and values which are lists of acceptable strings for the respective BIDS field.
	subjects : list, optional
		A whitelist of subjects to include in the workflow, if the list is empty there is no whitelist and all sessions will be considered.
	tr : float, optional
		Repetition time, explicitly.
		WARNING! This is a parameter waiting for deprecation.
	workflow_name : str, optional
		Top level name for the output directory.
	'''

	bids_base, out_base, out_dir, template, registration_mask, data_selection, functional_scan_types, structural_scan_types, subjects_sessions, func_ind, struct_ind = common_select(
			bids_base,
			out_base,
			workflow_name,
			template,
			registration_mask,
			functional_match,
			structural_match,
			subjects,
			sessions,
			)

	if not n_jobs:
		n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path', 'scan_type', 'task', 'nii_path', 'nii_name', 'events_name', 'subject_session','metadata_filename','dict_slice']))
	get_f_scan.inputs.ignore_exception = True
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.bids_base = bids_base
	get_f_scan.iterables = ("ind_type", func_ind)

	dummy_scans = pe.Node(name='dummy_scans', interface=util.Function(function=force_dummy_scans,input_names=inspect.getargspec(force_dummy_scans)[0], output_names=['out_file','deleted_scans']))
	dummy_scans.inputs.desired_dummy_scans = DUMMY_SCANS

	events_file = pe.Node(name='events_file', interface=util.Function(function=write_bids_events_file,input_names=inspect.getargspec(write_bids_events_file)[0], output_names=['out_file']))

	temporal_mean = pe.Node(interface=fsl.MeanImage(), name="temporal_mean")

	f_resize = pe.Node(interface=VoxelResize(), name="f_resize")
	f_resize.inputs.resize_factors = [10,10,10]

	f_percentile = pe.Node(interface=fsl.ImageStats(), name="f_percentile")
	f_percentile.inputs.op_string = '-p 98'

	f_threshold = pe.Node(interface=fsl.Threshold(), name="f_threshold")

	f_fast = pe.Node(interface=fsl.FAST(), name="f_fast")
	f_fast.inputs.no_pve = True
	f_fast.inputs.output_biascorrected = True

	f_bet = pe.Node(interface=fsl.BET(), name="f_BET")

	f_swapdim = pe.Node(interface=fsl.SwapDimensions(), name="f_swapdim")
	f_swapdim.inputs.new_dims = ('x','-z','-y')

	f_deleteorient = pe.Node(interface=FSLOrient(), name="f_deleteorient")
	f_deleteorient.inputs.main_option = 'deleteorient'

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = out_dir
	datasink.inputs.parameterization = False

	workflow_connections = [
		(get_f_scan, dummy_scans, [('nii_path', 'in_file')]),
		(dummy_scans, events_file, [('deleted_scans', 'forced_dummy_scans')]),
		(dummy_scans, f_resize, [('out_file', 'in_file')]),
		(get_f_scan, events_file, [
			('nii_path', 'timecourse_file'),
			('task', 'task'),
			('scan_path', 'scan_dir')
			]),
		(events_file, datasink, [('out_file', 'func.@events')]),
		(get_f_scan, events_file, [('events_name', 'out_file')]),
		(get_f_scan, datasink, [(('subject_session',ss_to_path), 'container')]),
		(temporal_mean, f_percentile, [('out_file', 'in_file')]),
		# here we divide by 10 assuming 10 percent noise
		(f_percentile, f_threshold, [(('out_stat', divideby_10), 'thresh')]),
		(temporal_mean, f_threshold, [('out_file', 'in_file')]),
		(f_threshold, f_fast, [('out_file', 'in_files')]),
		(f_fast, f_bet, [('restored_image', 'in_file')]),
		(f_resize, f_deleteorient, [('out_file', 'in_file')]),
		(f_deleteorient, f_swapdim, [('out_file', 'in_file')]),
		]

	if realign == "space":
		realigner = pe.Node(interface=spm.Realign(), name="realigner")
		realigner.inputs.register_to_mean = True
		workflow_connections.extend([
			(f_swapdim, realigner, [('out_file', 'in_file')]),
			])

	elif realign == "spacetime":
		realigner = pe.Node(interface=nipy.SpaceTimeRealigner(), name="realigner")
		realigner.inputs.slice_times = "asc_alt_2"
		realigner.inputs.tr = tr
		realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
		workflow_connections.extend([
			(f_swapdim, realigner, [('out_file', 'in_file')]),
			])

	elif realign == "time":
		realigner = pe.Node(interface=fsl.SliceTimer(), name="slicetimer")
		realigner.inputs.time_repetition = tr
		workflow_connections.extend([
			(f_swapdim, realigner, [('out_file', 'in_file')]),
			])

	f_antsintroduction = pe.Node(interface=antslegacy.antsIntroduction(), name='ants_introduction')
	f_antsintroduction.inputs.dimension = 3
	f_antsintroduction.inputs.reference_image = template
	#will need updating to `1`
	f_antsintroduction.inputs.bias_field_correction = True
	f_antsintroduction.inputs.transformation_model = 'GR'
	f_antsintroduction.inputs.max_iterations = [8,15,8]

	f_warp = pe.Node(interface=ants.WarpTimeSeriesImageMultiTransform(), name='f_warp')
	f_warp.inputs.reference_image = template
	f_warp.inputs.dimension = 4

	f_copysform2qform = pe.Node(interface=FSLOrient(), name='f_copysform2qform')
	f_copysform2qform.inputs.main_option = 'copysform2qform'

	warp_merge = pe.Node(util.Merge(2), name='warp_merge')

	workflow_connections.extend([
		(f_bet, f_antsintroduction, [('out_file', 'input_image')]),
		(f_antsintroduction, warp_merge, [('warp_field', 'in1')]),
		(f_antsintroduction, warp_merge, [('affine_transformation', 'in2')]),
		(warp_merge, f_warp, [('out', 'transformation_series')]),
		(f_warp, f_copysform2qform, [('output_image', 'in_file')]),
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
			(f_resize, temporal_mean, [('out_file', 'in_file')]),
			(f_swapdim, f_warp, [('out_file', 'input_image')]),
			])

	if functional_blur_xy:
		blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
		blur.inputs.fwhmxy = functional_blur_xy
		workflow_connections.extend([
			(get_f_scan, blur, [('nii_name','out_file')]),
			(f_copysform2qform, blur, [('out_file', 'in_file')]),
			(blur, datasink, [('out_file', 'func')]),
			])
	else:

		f_rename = pe.Node(util.Rename(), name='f_rename')

		workflow_connections.extend([
			(get_f_scan, f_rename, [('nii_name','format_string')]),
			(f_copysform2qform, f_rename, [('out_file', 'in_file')]),
			(f_rename, datasink, [('out_file', 'func')]),
			])


	workflow_config = {'execution': {'crashdump_dir': path.join(out_base,'crashdump'),}}
	if debug:
		workflow_config['logging'] = {
			'workflow_level':'DEBUG',
			'utils_level':'DEBUG',
			'interface_level':'DEBUG',
			'filemanip_level':'DEBUG',
			'log_to_file':'true',
			}

	workdir_name = workflow_name+"_work"
	#this gives the name of the workdir, the output name is passed to the datasink
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_base
	workflow.config = workflow_config
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_work:
		workdir = path.join(workflow.base_dir,workdir_name)
		try:
			shutil.rmtree(workdir)
		except OSError as e:
			if str(e) == 'Cannot call rmtree on a symbolic link':
				print('Not deleting top level workdir (`{}`), as it is a symlink. Deleting only contents instead'.format(workdir))
				for file_object in os.listdir(workdir):
					file_object_path = os.path.join(workdir, file_object)
					if os.path.isfile(file_object_path):
						os.unlink(file_object_path)
					else:
						shutil.rmtree(file_object_path)
			else:
				raise OSError(str(e))

@argh.arg('-f','--functional-match', type=json.loads)
@argh.arg('-s','--structural-match', type=json.loads)
@argh.arg('-m','--registration-mask')
def generic(bids_base, template,
	autorotate=False,
	debug=False,
	functional_blur_xy=False,
	functional_match={},
	functional_registration_method="composite",
	keep_work=False,
	n_jobs=False,
	n_jobs_percentage=0.8,
	out_base=None,
	realign="time",
	registration_mask="",
	sessions=[],
	structural_match={},
	subjects=[],
	tr=1,
	workflow_name='generic',
	params={},
	phase_dictionary=GENERIC_PHASES,
	):
	'''
	Generic preprocessing and registration workflow for small animal data in BIDS format.

	Parameters
	----------
	bids_base : str
		Path to the BIDS data set root.
	template : str
		Path to the template to register the data to.
	autorotate : bool, optional
		Whether to use a multi-rotation-state transformation start.
		This allows the registration to commence with the best rotational fit, and may help if the orientation of the data is malformed with respect to the header.
	debug : bool, optional
		Whether to enable nipype debug mode.
		This increases logging.
	functional_blur_xy : float, optional
		Factor by which to smooth data in the xy-plane; if parameter evaluates to false, no smoothing will be applied.
		Ideally this value should correspond to the resolution or smoothness in the z-direction (assuing z represents the lower-resolution slice-encoding direction).
	functional_match : dict, optional
		Dictionary specifying a whitelist to use for functional data inclusion into the workflow; if dictionary is empty no whitelist is present and all data will be considered.
		The dictionary should have keys which are 'acquisition', 'task', or 'modality', and values which are lists of acceptable strings for the respective BIDS field.
	functional_registration_method : {'composite','functional','structural'}, optional
		How to register the functional scan to the template.
		Values mean the following: 'composite' that it will be registered to the structural scan which will in turn be registered to the template, 'functional' that it will be registered directly, 'structural' that it will be registered exactly as the structural scan.
	keep_work : bool, str
		Whether to keep the work directory after workflow conclusion (this directory contains all the intermediary processing commands, inputs, and outputs --- it is invaluable for debugging but many times larger in size than the actual output).
	n_jobs : int, optional
		Number of processors to maximally use for the workflow; if unspecified a best guess will be estimate based on `n_jobs_percentage` and hardware (but not on current load).
	n_jobs_percentage : float, optional
		Percentage of available processors (as in available hardware, not available free load) to maximally use for the workflow (this is overriden by `n_jobs`).
	out_base : str, optional
		Output base directory --- inside which a directory named `workflow_name`(as well as associated directories) will be created.
	realign : {"space","time","spacetime",""}, optional
		Parameter that dictates slictiming correction and realignment of slices. "time" (FSL.SliceTimer) is default, since it works safely. Use others only with caution!
	registration_mask : str, optional
		Mask to use for the registration process.
		This mask will constrain the area for similarity metric evaluation, but the data will not be cropped.
	sessions : list, optional
		A whitelist of sessions to include in the workflow, if the list is empty there is no whitelist and all sessions will be considered.
	structural_match : dict, optional
		Dictionary specifying a whitelist to use for structural data inclusion into the workflow; if dictionary is empty no whitelist is present and all data will be considered.
		The dictionary should have keys which are 'acquisition', or 'modality', and values which are lists of acceptable strings for the respective BIDS field.
	subjects : list, optional
		A whitelist of subjects to include in the workflow, if the list is empty there is no whitelist and all sessions will be considered.
	tr : float, optional
		Repetition time, explicitly.
		WARNING! This is a parameter waiting for deprecation.
	workflow_name : str, optional
		Top level name for the output directory.
	'''

	bids_base, out_base, out_dir, template, registration_mask, data_selection, functional_scan_types, structural_scan_types, subjects_sessions, func_ind, struct_ind = common_select(
			bids_base,
			out_base,
			workflow_name,
			template,
			registration_mask,
			functional_match,
			structural_match,
			subjects,
			sessions,
			)

	if not n_jobs:
		n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'events_name', 'subject_session', 'metadata_filename', 'dict_slice']))
	get_f_scan.inputs.ignore_exception = True
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.bids_base = bids_base
	get_f_scan.iterables = ("ind_type", func_ind)

	dummy_scans = pe.Node(name='dummy_scans', interface=util.Function(function=force_dummy_scans,input_names=inspect.getargspec(force_dummy_scans)[0], output_names=['out_file','deleted_scans']))
	dummy_scans.inputs.desired_dummy_scans = DUMMY_SCANS

	events_file = pe.Node(name='events_file', interface=util.Function(function=write_bids_events_file,input_names=inspect.getargspec(write_bids_events_file)[0], output_names=['out_file']))

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = out_dir
	datasink.inputs.parameterization = False

	workflow_connections = [
		(get_f_scan, dummy_scans, [('nii_path', 'in_file')]),
		(dummy_scans, events_file, [('deleted_scans', 'forced_dummy_scans')]),
		(get_f_scan, events_file, [
			('nii_path', 'timecourse_file'),
			('task', 'task'),
			('scan_path', 'scan_dir')
			]),
		(events_file, datasink, [('out_file', 'func.@events')]),
		(get_f_scan, events_file, [('events_name', 'out_file')]),
		(get_f_scan, datasink, [(('subject_session',ss_to_path), 'container')]),
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
	s_biascorrect, f_biascorrect = real_size_nodes()

	if structural_scan_types.any():
		s_data_selection = deepcopy(data_selection)
		for match in structural_match.keys():
			s_data_selection = s_data_selection.loc[s_data_selection[match].isin(structural_match[match])]

		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_bids_scan, input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'events_name', 'subject_session', 'metadata_filename', 'dict_slice']))
		get_s_scan.inputs.ignore_exception = True
		get_s_scan.inputs.data_selection = s_data_selection
		get_s_scan.inputs.bids_base = bids_base

		s_register, s_warp, _, _ = generic_registration(template,
			structural_mask=registration_mask,
			phase_dictionary=phase_dictionary,
			)
		#TODO: incl. in func registration
		if autorotate:
			s_rotated = autorotate(template)
			workflow_connections.extend([
				(s_biascorrect, s_rotated, [('output_image', 'out_file')]),
				(s_rotated, s_register, [('out_file', 'moving_image')]),
				])
		else:
			workflow_connections.extend([
				(s_biascorrect, s_register, [('output_image', 'moving_image')]),
				(s_register, s_warp, [('composite_transform', 'transforms')]),
				(get_s_scan, s_warp, [('nii_path', 'input_image')]),
				(s_warp, datasink, [('output_image', 'anat')]),
				])

		workflow_connections.extend([
			(get_f_scan, get_s_scan, [('subject_session', 'selector')]),
			(get_s_scan, s_warp, [('nii_name','output_image')]),
			(get_s_scan, s_biascorrect, [('nii_path', 'input_image')]),
			])

	if functional_registration_method == "structural":
		if not structural_scan_types.any():
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
	elif functional_registration_method == "composite":
		if not structural_scan_types.any():
			raise ValueError('The option `registration="composite"` requires there to be a structural scan type.')
		_, _, f_register, f_warp = generic_registration(template,
			structural_mask=registration_mask,
			phase_dictionary=phase_dictionary,
			)
		temporal_mean = pe.Node(interface=fsl.MeanImage(), name="temporal_mean")

		merge = pe.Node(util.Merge(2), name='merge')

		workflow_connections.extend([
			(temporal_mean, f_biascorrect, [('out_file', 'input_image')]),
			(f_biascorrect, f_register, [('output_image', 'moving_image')]),
			(s_biascorrect, f_register, [('output_image', 'fixed_image')]),
			(s_register, merge, [('composite_transform', 'in1')]),
			(f_register, merge, [('composite_transform', 'in2')]),
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


	if functional_blur_xy:
		blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
		blur.inputs.fwhmxy = functional_blur_xy
		workflow_connections.extend([
			(get_f_scan, blur, [('nii_name','out_file')]),
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, datasink, [('out_file', 'func')]),
			])
	else:
		workflow_connections.extend([
			(get_f_scan, f_warp, [('nii_name','output_image')]),
			(f_warp, datasink, [('output_image', 'func')]),
			])


	workflow_config = {'execution': {'crashdump_dir': path.join(out_base,'crashdump'),}}
	if debug:
		workflow_config['logging'] = {
			'workflow_level':'DEBUG',
			'utils_level':'DEBUG',
			'interface_level':'DEBUG',
			'filemanip_level':'DEBUG',
			'log_to_file':'true',
			}

	workdir_name = workflow_name+"_work"
	#this gives the name of the workdir, the output name is passed to the datasink
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_base
	workflow.config = workflow_config
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_work:
		workdir = path.join(workflow.base_dir,workdir_name)
		try:
			shutil.rmtree(workdir)
		except OSError as e:
			if str(e) == 'Cannot call rmtree on a symbolic link':
				print('Not deleting top level workdir (`{}`), as it is a symlink. Deleting only contents instead'.format(workdir))
				for file_object in os.listdir(workdir):
					file_object_path = os.path.join(workdir, file_object)
					if os.path.isfile(file_object_path):
						os.unlink(file_object_path)
					else:
						shutil.rmtree(file_object_path)
			else:
				raise OSError(str(e))

def common_select(bids_base, out_base, workflow_name, template, registration_mask, functional_match, structural_match, subjects, sessions):
	"""Common selection and variable processing function for SAMRI preprocessing workflows."""

	if template:
		if template == "mouse":
			template = '/usr/share/mouse-brain-atlases/dsurqec_200micron.nii'
			registration_mask = '/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii'
		elif template == "rat":
			from samri.fetch.templates import fetch_rat_waxholm
			template = fetch_rat_waxholm()['template']
			registration_mask = fetch_rat_waxholm()['mask']
		else:
			if template:
				template = path.abspath(path.expanduser(template))
			if registration_mask:
				registration_mask = path.abspath(path.expanduser(registration_mask))
	else:
		raise ValueError("No species or template path specified")
		return -1

	bids_base = path.abspath(path.expanduser(bids_base))
	if not out_base:
		out_base = path.join(bids_base,'preprocessing')
	else:
		out_base = path.abspath(path.expanduser(out_base))
	out_dir = path.join(out_base,workflow_name)


	data_selection = bids_data_selection(bids_base, structural_match, functional_match, subjects, sessions)
	workdir = out_dir + '_work'
	if not os.path.exists(workdir):
		os.makedirs(workdir)
	data_selection.to_csv(path.join(workdir,'data_selection.csv'))

	# generate functional and structural scan types
	functional_scan_types = data_selection.loc[data_selection.type == 'func']['acq'].values
	structural_scan_types = data_selection.loc[data_selection.type == 'anat']['acq'].values
	# we start to define nipype workflow elements (nodes, connections, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()

	_func_ind = data_selection[data_selection["type"] == "func"]
	func_ind = _func_ind.index.tolist()

	_struct_ind = data_selection[data_selection["type"] == "anat"]
	struct_ind = _struct_ind.index.tolist()

	if True:
		print(data_selection)
		print(subjects_sessions)
	return bids_base, out_base, out_dir, template, registration_mask, data_selection, functional_scan_types, structural_scan_types, subjects_sessions, func_ind, struct_ind
