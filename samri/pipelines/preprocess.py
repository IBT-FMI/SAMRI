from os import path, listdir, getcwd, remove
from samri.pipelines.extra_functions import get_data_selection, get_bids_scan, write_bids_metadata_file, write_bids_events_file, force_dummy_scans, BIDS_METADATA_EXTRACTION_DICTS
from samri.pipelines.extra_interfaces import VoxelResize

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

from samri.pipelines.nodes import *
from samri.pipelines.utils import bids_naming, ss_to_path, sss_filename, fslmaths_invert_values
from samri.utilities import N_PROCS
from samri.fetch.templates import fetch_rat_waxholm, fetch_mouse_DSURQE

from bids.grabbids import BIDSLayout
from bids.grabbids import BIDSValidator
import os

DUMMY_SCANS=10
N_PROCS=max(N_PROCS-4, 2)


debug = True
#set all outputs to compressed NIfTI
afni.base.AFNICommand.set_default_output_type('NIFTI_GZ')
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')


def filterData(df, col_name, entries):

	res_df = pd.DataFrame()
	in_df = df[col_name].dropna().unique().tolist()
	for entry in entries:
		if(entry in in_df):
			_df = df[df[col_name] == entry]
			res_df = res_df.append(_df)
	return res_df

def bids_data_selection(base, structural_match, functional_match, subjects, sessions):
	validate = BIDSValidator()
	for x in os.walk(base):
		print(x[0])
		print(validate.is_bids(x[0]))
	layout = BIDSLayout(base)
	df = layout.as_data_frame()
	# drop event files
	df = df[df.type != 'events']
	# rm .json
	df = df.loc[df.path.str.contains('.nii')]
	# generate scan types for later
	df['scan_type'] = ""
	#print(df.path.str.startswith('task', beg=0,end=len('task')))
	beg = df.path.str.find('task-')
	end = df.path.str.find('.')
	#df.loc[df.modality == 'func', 'scan_type'] = 'acq-'+df['acq']+'_task-'+  df.path.str.partition('task-')[2].str.partition('.')[0]
	#df.loc[df.modality == 'anat', 'scan_type'] = 'acq-'+df['acq']+'_' + df['type']
	#TODO: fix task!=type
	df.loc[df.modality == 'func', 'task'] = df.path.str.partition('task-')[2].str.partition('_')[0]
	df.loc[df.modality == 'func', 'scan_type'] = 'task-' + df['task'] + '_acq-'+ df['acq']
	df.loc[df.modality == 'anat', 'scan_type'] = 'acq-'+df['acq'] +'_' + df['type']

	#TODO: make nicer, generalize to all functional match entries... dict vs list von subjects,etc. und acq / acquistion mismatch
	res_df = pd.DataFrame()
	if(functional_match):
		_df = filterData(df, 'task', functional_match['task'])
		try:
			_df = filterData(df, 'type', functional_match['type'])
		except:
			pass
		res_df = res_df.append(_df)
		if(structural_match):
			_df = filterData(df, 'acq', structural_match['acquisition'])
			res_df = res_df.append(_df)
	df = res_df
	if(subjects):
		df = filterData(df, 'subject', subjects)
	if(sessions):
		df = filterData(df, 'session', sessions)

	return df

def legacy_bruker(bids_base, template,
	DEBUG=False,
	exclude={},
	functional_match={},
	structural_match={},
	sessions=[],
	subjects=[],
	actual_size=True,
	functional_blur_xy=False,
	functional_registration_method="structural",
	highpass_sigma=225,
	lowpass_sigma=None,
	negative_contrast_agent=False,
	n_procs=N_PROCS,
	realign="time",
	registration_mask=False,
	tr=1,
	very_nasty_bruker_delay_hack=False,
	workflow_name="generic",
	keep_work=False,
	autorotate=False,
	strict=False,
	verbose=False,
	):
	'''
	Perform realignment and registration

	Parameters
	----------

	realign: {"space","time","spacetime",""}
		Parameter that dictates slictiming correction and realignment of slices. "time" (FSL.SliceTimer) is default, since it works safely. Use others only with caution!

	'''
	if template:
		if template == "mouse":
			from samri.fetch.templates import fetch_rat_waxholm, fetch_mouse_DSURQE
			template = fetch_mouse_DSURQE()['template']
			registration_mask = fetch_mouse_DSURQE()['mask']
		elif template == "rat":
			from samri.fetch.templates import fetch_rat_waxholm, fetch_mouse_DSURQE
			template = fetch_rat_waxholm()['template']
			registration_mask = fetch_rat_waxholm()['mask']
		else:
			pass
	else:
		raise ValueError("No species or template specified")
		return -1

	bids_base = path.abspath(path.expanduser(bids_base))

	data_selection = bids_data_selection(bids_base, structural_match, functional_match, subjects, sessions)

	# generate functional and structural scan types
	functional_scan_types = data_selection.loc[data_selection.modality == 'func']['scan_type'].values
	structural_scan_types = data_selection.loc[data_selection.modality == 'anat']['scan_type'].values

	# we start to define nipype workflow elements (nodes, connections, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()

	_func_ind = data_selection[data_selection["modality"] == "func"]
	func_ind = _func_ind.index.tolist()

	_struct_ind = data_selection[data_selection["modality"] == "anat"]
	struct_ind = _struct_ind.index.tolist()
	sel = data_selection.index.tolist()

	if True:
		print(data_selection)
		print(subjects_sessions)

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'file_name', 'events_name', 'subject_session']))
	get_f_scan.inputs.ignore_exception = True
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.bids_base = bids_base
	get_f_scan.iterables = ("ind_type", func_ind)

	dummy_scans = pe.Node(name='dummy_scans', interface=util.Function(function=force_dummy_scans,input_names=inspect.getargspec(force_dummy_scans)[0], output_names=['out_file','deleted_scans']))
	dummy_scans.inputs.desired_dummy_scans = DUMMY_SCANS

	events_file = pe.Node(name='events_file', interface=util.Function(function=write_bids_events_file,input_names=inspect.getargspec(write_bids_events_file)[0], output_names=['out_file']))

	temporal_mean = pe.Node(interface=fsl.MeanImage(), name="temporal_mean")

	f_resize = pe.Node(interface=VoxelResize(), name="f_resize")

	f_percentile = pe.Node(interface=fsl.ImageStats(), name="f_percentile")
	f_percentileinputs.op_string = '-p 98'

	f_threshold = pe.Node(interface=fsl.Threshold(), name="f_threshold")

	f_fast = pe.Node(interface=fsl.FAST(), name="f_fast")
	f_fast.inputs.no_pve = True
	f_fast.inputs.output_biascorrected = True

	f_deleteorient = pe.Node(interface=fsl.FSLOrient(), name="f_deleteorient")
	f_deleteorient.inputs.main_option = 'deleteorient'

	f_mean_deleteorient = pe.Node(interface=fsl.FSLOrient(), name="f_deleteorient")
	f_mean_deleteorient.inputs.main_option = 'deleteorient'

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(bids_base,"preprocessing",workflow_name)
	datasink.inputs.parameterization = False
	if not (strict or verbose):
		datasink.inputs.ignore_exception = True

	workflow_connections = [
		(get_f_scan, dummy_scans, [('nii_path', 'in_file')]),
		(get_f_scan, dummy_scans, [('scan_path', 'scan_dir')]),
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
		# here we divide by 1 assuming 10 percent noise
		(f_percentile, f_threshold, [(('out_stat', lambda x: x/10.), 'thresh')]),
		(temporal_mean, f_threshold, [('out_file', 'in_file')]),
		(f_threshold, f_fast, [('out_file', 'in_files')]),
		(f_fast, f_bet, [('restored_image', 'in_file')]),
		(f_bet, f_deleteorient, [('out_file', 'in_file')]),
		]

	if realign == "space":
		realigner = pe.Node(interface=spm.Realign(), name="realigner")
		realigner.inputs.register_to_mean = True
		workflow_connections.extend([
			(f_resize, realigner, [('out_file', 'in_file')]),
			])

	elif realign == "spacetime":
		realigner = pe.Node(interface=nipy.SpaceTimeRealigner(), name="realigner")
		realigner.inputs.slice_times = "asc_alt_2"
		realigner.inputs.tr = tr
		realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
		workflow_connections.extend([
			(f_resize, realigner, [('out_file', 'in_file')]),
			])

	elif realign == "time":
		realigner = pe.Node(interface=fsl.SliceTimer(), name="slicetimer")
		realigner.inputs.time_repetition = tr
		workflow_connections.extend([
			(f_resize, realigner, [('out_file', 'in_file')]),
			])

	if structural_scan_types.any():
		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_bids_scan, input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'file_name', 'events_name', 'subject_session']))
		get_s_scan.inputs.ignore_exception = True
		get_s_scan.inputs.data_selection = data_selection
		get_s_scan.inputs.bids_base = bids_base

		s_cutoff = pe.Node(interface=fsl.ImageMaths(), name="s_cutoff")
		s_cutoff.inputs.op_string = "-thrP 20 -uthrp 98"

		s_resize = pe.Node(interface=VoxelResize(), name="s_resize")

		s_BET = pe.Node(interface=fsl.BET(), name="s_BET")
		s_BET.inputs.mask = True
		s_BET.inputs.frac = 0.3
		s_BET.inputs.robust = True

		ants_introduction = pe.Node(interface=ants.legacy.antsIntroduction(), name='ants_introduction')
		ants_introduction.inputs.dimension = 3
		ants_introduction.inputs.reference = template
		ants_introduction.inputs.bias_field_correction = 1
		ants_introduction.inputs.transformation_model = 'GR'
		ants_introduction.inputs.max_iterations = [8,15,8]

		s_mask = pe.Node(interface=fsl.ApplyMask(), name="s_mask")
		s_register, s_warp, f_warp = structural_registration(template)

		workflow_connections.extend([
			(get_s_scan, s_reg_biascorrect, [('nii_path', 'input_image')]),
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
				(get_s_scan, s_warp, [('nii_path', 'input_image')]),
				(s_warp, datasink, [('output_image', 'anat')]),
				])


		if autorotate:
			s_rotated = autorotate(template)

		workflow_connections.extend([
			(get_f_scan, get_s_scan, [('subject_session', 'selector')]),
			(get_s_scan, s_warp, [('nii_name','output_image')]),
			(get_s_scan, s_biascorrect, [('nii_path', 'input_image')]),
			])

	if functional_registration_method == "functional":

		f_antsintroduction = pe.Node(interface=ants.legacy.antsIntroduction(), name='ants_introduction')
		f_antsintroduction.inputs.dimension = 3
		f_antsintroduction.inputs.reference_image = template
		f_antsintroduction.inputs.bias_field_correction = 1
		f_antsintroduction.inputs.transformation_model = 'GR'
		f_antsintroduction.inputs.max_iterations = [8,15,8]

		workflow_connections.extend([
			(f_deleteorient, f_antsintroduction, [('out_file', 'input_image')]),
			(f_biascorrect, f_register, [('output_image', 'moving_image')]),
			(f_register, f_warp, [('composite_transform', 'transforms')]),
				(realigner, f_warp, [('realigned_files', 'input_image')]),
			])
		if realign == "space":
			workflow_connections.extend([
				(realigner, temporal_mean, [('realigned_files', 'in_file')]),
				(realigner, f_deleteorient, [('realigned_files', 'in_file')]),
				])
		elif realign == "spacetime":
			workflow_connections.extend([
				(realigner, temporal_mean, [('out_file', 'in_file')]),
				(realigner, f_deleteorient, [('out_file', 'in_file')]),
				])
		elif realign == "time":
			workflow_connections.extend([
				(realigner, temporal_mean, [('slice_time_corrected_file', 'in_file')]),
				(realigner, f_deleteorient, [('slice_time_corrected_file', 'in_file')]),
				])
		else:
			workflow_connections.extend([
				(f_resize, temporal_mean, [('out_file', 'in_file')]),
				(f_resize, f_deleteorient, [('out_file', 'in_file')]),
				])
	elif functional_registration_method == "structural":
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
	elif functional_registration_method == "composite":
		if not structural_scan_types.any():
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



	invert = pe.Node(interface=fsl.ImageMaths(), name="invert")
	blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
	blur.inputs.fwhmxy = functional_blur_xy
	if functional_blur_xy and negative_contrast_agent:
		workflow_connections.extend([
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, invert, [(('out_file', fslmaths_invert_values), 'op_string')]),
			(blur, invert, [('out_file', 'in_file')]),
			(get_f_scan, invert, [('nii_name','output_image')]),
			(invert, datasink, [('out_file', 'func')]),
			])

	elif functional_blur_xy:
		workflow_connections.extend([
			(get_f_scan, blur, [('nii_name','output_image')]),
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, datasink, [('out_file', 'func')]),
			])

	elif negative_contrast_agent:
		workflow_connections.extend([
			(get_f_scan, invert, [('nii_name','out_file')]),
			(f_warp, invert, [(('output_image', fslmaths_invert_values), 'op_string')]),
			(f_warp, invert, [('output_image', 'in_file')]),
			(invert, datasink, [('out_file', 'func')]),
			])
	else:
		workflow_connections.extend([
			(get_f_scan, f_warp, [('nii_name','output_image')]),
			(f_warp, datasink, [('output_image', 'func')]),
			])


	workflow_config = {'execution': {'crashdump_dir': path.join(bids_base,'preprocessing/crashdump'),}}
	if debug:
		workflow_config['logging'] = {
			'workflow_level':'DEBUG',
			'utils_level':'DEBUG',
			'interface_level':'DEBUG',
			'filemanip_level':'DEBUG',
			'log_to_file':'true',
			}

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = path.join(bids_base,"preprocessing")
	workflow.config = workflow_config
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs, 'memory_gb' : 500})
	if not keep_work:
		shutil.rmtree(path.join(workflow.base_dir,workdir_name))


def bruker(bids_base, template,
	DEBUG=False,
	exclude={},
	functional_match={},
	structural_match={},
	sessions=[],
	subjects=[],
	actual_size=True,
	functional_blur_xy=False,
	functional_registration_method="structural",
	highpass_sigma=225,
	lowpass_sigma=None,
	negative_contrast_agent=False,
	n_procs=N_PROCS,
	realign="time",
	registration_mask=False,
	tr=1,
	very_nasty_bruker_delay_hack=False,
	workflow_name="generic",
	keep_work=False,
	autorotate=False,
	strict=False,
	verbose=False,
	):
	'''

	realign: {"space","time","spacetime",""}
		Parameter that dictates slictiming correction and realignment of slices. "time" (FSL.SliceTimer) is default, since it works safely. Use others only with caution!

	'''
	if template:
		if template == "mouse":
			from samri.fetch.templates import fetch_rat_waxholm, fetch_mouse_DSURQE
			template = fetch_mouse_DSURQE()['template']
			registration_mask = fetch_mouse_DSURQE()['mask']
		elif template == "rat":
			from samri.fetch.templates import fetch_rat_waxholm, fetch_mouse_DSURQE
			template = fetch_rat_waxholm()['template']
			registration_mask = fetch_rat_waxholm()['mask']
		else:
			pass
	else:
		raise ValueError("No species or template specified")
		return -1

	bids_base = path.abspath(path.expanduser(bids_base))

	data_selection = bids_data_selection(bids_base, structural_match, functional_match, subjects, sessions)

	# generate functional and structural scan types
	functional_scan_types = data_selection.loc[data_selection.modality == 'func']['scan_type'].values
	structural_scan_types = data_selection.loc[data_selection.modality == 'anat']['scan_type'].values

	# we start to define nipype workflow elements (nodes, connections, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()

	_func_ind = data_selection[data_selection["modality"] == "func"]
	func_ind = _func_ind.index.tolist()

	_struct_ind = data_selection[data_selection["modality"] == "anat"]
	struct_ind = _struct_ind.index.tolist()
	sel = data_selection.index.tolist()

	if True:
		print(data_selection)
		print(subjects_sessions)

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'file_name', 'events_name', 'subject_session']))
	get_f_scan.inputs.ignore_exception = True
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.bids_base = bids_base
	get_f_scan.iterables = ("ind_type", func_ind)

	dummy_scans = pe.Node(name='dummy_scans', interface=util.Function(function=force_dummy_scans,input_names=inspect.getargspec(force_dummy_scans)[0], output_names=['out_file','deleted_scans']))
	dummy_scans.inputs.desired_dummy_scans = DUMMY_SCANS

	events_file = pe.Node(name='events_file', interface=util.Function(function=write_bids_events_file,input_names=inspect.getargspec(write_bids_events_file)[0], output_names=['out_file']))

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(bids_base,"preprocessing",workflow_name)
	datasink.inputs.parameterization = False
	if not (strict or verbose):
		datasink.inputs.ignore_exception = True

	workflow_connections = [
		(get_f_scan, dummy_scans, [('nii_path', 'in_file')]),
		(get_f_scan, dummy_scans, [('scan_path', 'scan_dir')]),
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
	if actual_size:
		s_biascorrect, f_biascorrect = real_size_nodes()
	else:
		s_biascorrect, f_biascorrect = inflated_size_nodes()

	if structural_scan_types.any():
		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_bids_scan, input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'file_name', 'events_name', 'subject_session']))
		get_s_scan.inputs.ignore_exception = True
		get_s_scan.inputs.data_selection = data_selection
		get_s_scan.inputs.bids_base = bids_base

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
					(get_s_scan, s_warp, [('nii_path', 'input_image')]),
					(s_warp, datasink, [('output_image', 'anat')]),
					])
		else:
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
				(get_s_scan, s_reg_biascorrect, [('nii_path', 'input_image')]),
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
					(get_s_scan, s_warp, [('nii_path', 'input_image')]),
					(s_warp, datasink, [('output_image', 'anat')]),
					])


		if autorotate:
			s_rotated = autorotate(template)

		workflow_connections.extend([
			(get_f_scan, get_s_scan, [('subject_session', 'selector')]),
			(get_s_scan, s_warp, [('nii_name','output_image')]),
			(get_s_scan, s_biascorrect, [('nii_path', 'input_image')]),
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
	elif functional_registration_method == "composite":
		if not structural_scan_types.any():
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


	invert = pe.Node(interface=fsl.ImageMaths(), name="invert")
	blur = pe.Node(interface=afni.preprocess.BlurToFWHM(), name="blur")
	blur.inputs.fwhmxy = functional_blur_xy
	if functional_blur_xy and negative_contrast_agent:
		workflow_connections.extend([
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, invert, [(('out_file', fslmaths_invert_values), 'op_string')]),
			(blur, invert, [('out_file', 'in_file')]),
			(get_f_scan, invert, [('nii_name','output_image')]),
			(invert, datasink, [('out_file', 'func')]),
			])

	elif functional_blur_xy:
		workflow_connections.extend([
			(get_f_scan, blur, [('nii_name','output_image')]),
			(f_warp, blur, [('output_image', 'in_file')]),
			(blur, datasink, [('out_file', 'func')]),
			])

	elif negative_contrast_agent:
		workflow_connections.extend([
			(get_f_scan, invert, [('nii_name','out_file')]),
			(f_warp, invert, [(('output_image', fslmaths_invert_values), 'op_string')]),
			(f_warp, invert, [('output_image', 'in_file')]),
			(invert, datasink, [('out_file', 'func')]),
			])
	else:
		workflow_connections.extend([
			(get_f_scan, f_warp, [('nii_name','output_image')]),
			(f_warp, datasink, [('output_image', 'func')]),
			])


	workflow_config = {'execution': {'crashdump_dir': path.join(bids_base,'preprocessing/crashdump'),}}
	if debug:
		workflow_config['logging'] = {
			'workflow_level':'DEBUG',
			'utils_level':'DEBUG',
			'interface_level':'DEBUG',
			'filemanip_level':'DEBUG',
			'log_to_file':'true',
			}

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = path.join(bids_base,"preprocessing")
	workflow.config = workflow_config
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs, 'memory_gb' : 500})
	if not keep_work:
		shutil.rmtree(path.join(workflow.base_dir,workdir_name))

