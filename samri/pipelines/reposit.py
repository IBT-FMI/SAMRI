from os import path, remove
from samri.pipelines.extra_functions import get_data_selection, get_scan, write_bids_metadata_file, write_bids_events_file, BIDS_METADATA_EXTRACTION_DICTS

import argh
import re
import inspect
import json
import os
import shutil
import time

import nipype.interfaces.io as nio
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
import pandas as pd
from nipype.interfaces import bru2nii

from samri.pipelines.utils import bids_naming, ss_to_path
from samri.utilities import N_PROCS

try:
	    FileNotFoundError
except NameError:
	    FileNotFoundError = IOError

N_PROCS=max(N_PROCS-4, 2)

@argh.arg('-d','--diffusion-match', type=json.loads)
@argh.arg('-f','--functional-match', type=json.loads)
@argh.arg('-s','--structural-match', type=json.loads)
@argh.arg('-m','--measurements', nargs='*', type=str)
def bru2bids(measurements_base,
	measurements=[],
	inflated_size=False,
	dataset_name=False,
	debug=False,
	diffusion_match={},
	exclude={},
	functional_match={},
	keep_crashdump=False,
	keep_work=False,
	n_procs=N_PROCS,
	out_base=None,
	structural_match={},
	):
	"""
	Convert and reorganize Bruker "raw" directories (2dseq and ParaVision-formatted metadata files) into a BIDS-organized file hierarchy containing NIfTI files and associated metadata.
	If any exist, this workflow also reposits COSplay event files (already written according to BIDS) in the correct place in the output hierarchy.

	Parameters
	----------

	measurements_base : str
		Path of the top level directory containing all the Bruker scan directories to be converted and reformatted.
	inflated_size : bool, optional
		Whether to inflate the voxel size reported by the scanner when converting the data to NIfTI.
		Setting this to `True` multiplies the voxel edge lengths by 10 (i.e. the volume by 1000); this is occasionally done in some small animal pipelines, which use routines designed exclusively for human data.
		Unless you are looking to reproduce such a workflow, this should be set to `True`.
	dataset_name : string, optional
		A dataset name that will be written into the BIDS metadata file.
		Generally not needed, as by default we use the dataset path to satisfy this BIDS requirement.
	debug : bool, optional
		Whether to enable debug support.
		This prints the data selection before passing it to the nipype workflow management system, and turns on debug support in nipype (leading to more verbose logging).
	diffusion_match : dict, optional
		A dictionary with any combination of "session", "subject", "task", and "acquisition" as keys and corresponding lists of identifiers as values.
		Only diffusion scans matching all identifiers will be included - i.e. this is a whitelist.
	exclude : dict, optional
		A dictionary with any combination of "session", "subject", "task" , and "acquisition" as keys and corresponding identifiers as values.
		Only scans not matching any of the listed criteria will be included in the workfolow - i.e. this is a blacklist (for functional and structural scans).
	functional_match : dict, optional
		A dictionary with any combination of "session", "subject", "task", and "acquisition" as keys and corresponding lists of identifiers as values.
		Only Functional scans matching all identifiers will be included - i.e. this is a whitelist.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	keep_crashdump : bool, optional
		Whether to keep the crashdump directory (containing all the crash reports for intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	n_procs : int, optional
		Maximum number of processes which to simultaneously spawn for the workflow.
		If not explicitly defined, this is automatically calculated from the number of available cores and under the assumption that the workflow will be the main process running for the duration that it is running.
	out_base : str, optional
		Base directory in which to place the BIDS reposited data.
		If not present the BIDS records will be created in the `measurements_base` directory.
	structural_match : dict, optional
		A dictionary with any combination of "session", "subject", "task", and "acquisition" as keys and corresponding lists of identifiers as values.
		Only structural scans matching all identifiers will be included - i.e. this is a whitelist.
	"""

	measurements_base = path.abspath(path.expanduser(measurements_base))
	if out_base:
		out_base = path.abspath(path.expanduser(out_base))
	else:
		out_base = measurements_base
	out_dir = path.join(out_base,'bids')

	# define measurement directories to be processed, and populate the list either with the given include_measurements, or with an intelligent selection
	functional_scan_types = diffusion_scan_types = structural_scan_types = []
	data_selection = pd.DataFrame([])
	if structural_match:
		s_data_selection = get_data_selection(measurements_base,
			match=structural_match,
			exclude=exclude,
			measurements=measurements,
			)
		structural_scan_types = list(s_data_selection['scan_type'].unique())
		data_selection = pd.concat([data_selection,s_data_selection])
	if functional_match:
		f_data_selection = get_data_selection(measurements_base,
			match=functional_match,
			exclude=exclude,
			measurements=measurements,
			)
		functional_scan_types = list(f_data_selection['scan_type'].unique())
		data_selection = pd.concat([data_selection,f_data_selection])
	if diffusion_match:
		d_data_selection = get_data_selection(measurements_base,
			match=diffusion_match,
			exclude=exclude,
			measurements=measurements,
			)
		diffusion_scan_types = list(d_data_selection['scan_type'].unique())
		data_selection = pd.concat([data_selection,d_data_selection])

	# we start to define nipype workflow elements (nodes, connections, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()
	if debug:
		print('Data selection:')
		print(data_selection)
		print('Iterating over:')
		print(subjects_sessions)
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_session'], mandatory_inputs=False), name="infosource")
	infosource.iterables = [('subject_session', subjects_sessions)]

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = out_dir
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
		]

	if functional_scan_types:
		get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type','task']))
		get_f_scan.inputs.ignore_exception = True
		get_f_scan.inputs.data_selection = data_selection
		get_f_scan.inputs.measurements_base = measurements_base
		get_f_scan.iterables = ("scan_type", functional_scan_types)

		f_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="f_bru2nii")
		f_bru2nii.inputs.actual_size = not inflated_size

		f_filename = pe.Node(name='f_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		f_filename.inputs.metadata = data_selection
		f_filename.inputs.extension=''

		f_metadata_filename = pe.Node(name='f_metadata_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		f_metadata_filename.inputs.extension = ".json"
		f_metadata_filename.inputs.metadata = data_selection

		f_metadata_file = pe.Node(name='metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getargspec(write_bids_metadata_file)[0], output_names=['out_file']))
		f_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

		events_filename = pe.Node(name='bids_stim_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		events_filename.inputs.suffix = "events"
		events_filename.inputs.extension = ".tsv"
		events_filename.inputs.metadata = data_selection
		events_filename.ignore_exception = True

		events_file = pe.Node(name='events_file', interface=util.Function(function=write_bids_events_file,input_names=inspect.getargspec(write_bids_events_file)[0], output_names=['out_file']))
		events_file.ignore_exception = True

		workflow_connections = [
			(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
			(infosource, get_f_scan, [('subject_session', 'selector')]),
			(infosource, f_metadata_filename, [('subject_session', 'subject_session')]),
			(infosource, f_filename, [('subject_session', 'subject_session')]),
			(infosource, events_filename, [('subject_session', 'subject_session')]),
			(get_f_scan, f_metadata_filename, [('scan_type', 'scan_type')]),
			(get_f_scan, f_filename, [('scan_type', 'scan_type')]),
			(get_f_scan, f_bru2nii, [('scan_path', 'input_dir')]),
			(get_f_scan, f_metadata_file, [('scan_path', 'scan_dir')]),
			(get_f_scan, f_metadata_file, [('task', 'task_name')]),
			(f_metadata_filename, f_metadata_file, [('filename', 'out_file')]),
			(f_filename, f_bru2nii, [('filename', 'output_filename')]),
			(events_filename, events_file, [('filename', 'out_file')]),
			(f_metadata_file, events_file, [('out_file', 'metadata_file')]),
			(f_bru2nii, events_file, [('nii_file', 'timecourse_file')]),
			(get_f_scan, events_filename, [('scan_type', 'scan_type')]),
			(f_bru2nii, datasink, [('nii_file', 'func')]),
			(get_f_scan, events_file, [
				('task', 'task'),
				('scan_path', 'scan_dir')
				]),
			(events_file, datasink, [('out_file', 'func.@events')]),
			(f_metadata_file, datasink, [('out_file', 'func.@metadata')]),
			]
		crashdump_dir = path.join(out_base,'bids_crashdump')
		workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
		if debug:
			workflow_config['logging'] = {
				'workflow_level':'DEBUG',
				'utils_level':'DEBUG',
				'interface_level':'DEBUG',
				'filemanip_level':'DEBUG',
				'log_to_file':'true',
				}

		workdir_name = 'bids_work'
		workflow = pe.Workflow(name=workdir_name)
		workflow.connect(workflow_connections)
		workflow.base_dir = path.join(out_base)
		workflow.config = workflow_config
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph_structural.dot"), graph2use="hierarchical", format="png")

		#Execute the workflow
		if not keep_work or not keep_crashdump:
			try:
				workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
			except RuntimeError:
				pass
		else:
			workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
		if not keep_work:
			shutil.rmtree(path.join(workflow.base_dir,workdir_name))
		if not keep_crashdump:
			try:
				shutil.rmtree(crashdump_dir)
			except (FileNotFoundError, OSError):
				pass

	if diffusion_scan_types:
		get_d_scan = pe.Node(name='get_d_scan', interface=util.Function(function=get_scan, input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type','task']))
		get_d_scan.inputs.ignore_exception = True
		get_d_scan.inputs.data_selection = data_selection
		get_d_scan.inputs.measurements_base = measurements_base
		get_d_scan.iterables = ("scan_type", diffusion_scan_types)

		d_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="d_bru2nii")
		d_bru2nii.inputs.force_conversion=True
		d_bru2nii.inputs.actual_size = not inflated_size

		d_filename = pe.Node(name='d_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		d_filename.inputs.metadata = data_selection
		d_filename.inputs.extension=''

		d_metadata_filename = pe.Node(name='d_metadata_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		d_metadata_filename.inputs.extension = ".json"
		d_metadata_filename.inputs.metadata = data_selection

		d_metadata_file = pe.Node(name='d_metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getargspec(write_bids_metadata_file)[0], output_names=['out_file']))
		d_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

		workflow_connections = [
			(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
			(infosource, get_d_scan, [('subject_session', 'selector')]),
			(infosource, d_filename, [('subject_session', 'subject_session')]),
			(infosource, d_metadata_filename, [('subject_session', 'subject_session')]),
			(get_d_scan, d_bru2nii, [('scan_path','input_dir')]),
			(get_d_scan, d_filename, [('scan_type', 'scan_type')]),
			(get_d_scan, d_metadata_filename, [('scan_type', 'scan_type')]),
			(get_d_scan, d_metadata_file, [('scan_path', 'scan_dir')]),
			(d_filename, d_bru2nii, [('filename','output_filename')]),
			(d_metadata_filename, d_metadata_file, [('filename', 'out_file')]),
			(d_bru2nii, datasink, [('nii_file', 'dwi')]),
			(d_metadata_file, datasink, [('out_file', 'dwi.@metadata')]),
			]
		crashdump_dir = path.join(out_base,'bids_crashdump')
		workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
		if debug:
			workflow_config['logging'] = {
				'workflow_level':'DEBUG',
				'utils_level':'DEBUG',
				'interface_level':'DEBUG',
				'filemanip_level':'DEBUG',
				'log_to_file':'true',
				}

		workdir_name = 'bids_work'
		workflow = pe.Workflow(name=workdir_name)
		workflow.connect(workflow_connections)
		workflow.base_dir = path.join(out_base)
		workflow.config = workflow_config
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph_diffusion.dot"), graph2use="hierarchical", format="png")

		#Execute the workflow
		if not keep_work or not keep_crashdump:
			try:
				workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
			except RuntimeError:
				pass
		else:
			workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
		if not keep_work:
			shutil.rmtree(path.join(workflow.base_dir,workdir_name))
		if not keep_crashdump:
			try:
				shutil.rmtree(crashdump_dir)
			except (FileNotFoundError, OSError):
				pass

	if structural_scan_types:
		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_scan, input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type','task']))
		get_s_scan.inputs.ignore_exception = True
		get_s_scan.inputs.data_selection = data_selection
		get_s_scan.inputs.measurements_base = measurements_base
		get_s_scan.iterables = ("scan_type", structural_scan_types)

		s_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="s_bru2nii")
		s_bru2nii.inputs.force_conversion=True
		s_bru2nii.inputs.actual_size = not inflated_size

		s_filename = pe.Node(name='s_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		s_filename.inputs.metadata = data_selection
		s_filename.inputs.extension=''

		s_metadata_filename = pe.Node(name='s_metadata_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
		s_metadata_filename.inputs.extension = ".json"
		s_metadata_filename.inputs.metadata = data_selection

		s_metadata_file = pe.Node(name='s_metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getargspec(write_bids_metadata_file)[0], output_names=['out_file']))
		s_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

		workflow_connections = [
			(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
			(infosource, get_s_scan, [('subject_session', 'selector')]),
			(infosource, s_filename, [('subject_session', 'subject_session')]),
			(infosource, s_metadata_filename, [('subject_session', 'subject_session')]),
			(get_s_scan, s_bru2nii, [('scan_path','input_dir')]),
			(get_s_scan, s_filename, [('scan_type', 'scan_type')]),
			(get_s_scan, s_metadata_filename, [('scan_type', 'scan_type')]),
			(get_s_scan, s_metadata_file, [('scan_path', 'scan_dir')]),
			(s_filename, s_bru2nii, [('filename','output_filename')]),
			(s_metadata_filename, s_metadata_file, [('filename', 'out_file')]),
			(s_bru2nii, datasink, [('nii_file', 'anat')]),
			(s_metadata_file, datasink, [('out_file', 'anat.@metadata')]),
			]
		crashdump_dir = path.join(out_base,'bids_crashdump')
		workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
		if debug:
			workflow_config['logging'] = {
				'workflow_level':'DEBUG',
				'utils_level':'DEBUG',
				'interface_level':'DEBUG',
				'filemanip_level':'DEBUG',
				'log_to_file':'true',
				}

		workdir_name = 'bids_work'
		workflow = pe.Workflow(name=workdir_name)
		workflow.connect(workflow_connections)
		workflow.base_dir = path.join(out_base)
		workflow.config = workflow_config
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph_structural.dot"), graph2use="hierarchical", format="png")

		#Execute the workflow
		if not keep_work or not keep_crashdump:
			try:
				workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
			except RuntimeError:
				pass
		else:
			workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
		if not keep_work:
			shutil.rmtree(path.join(workflow.base_dir,workdir_name))
		if not keep_crashdump:
			try:
				shutil.rmtree(crashdump_dir)
			except (FileNotFoundError, OSError):
				pass

	# This is needed because BIDS does not yet support CBV
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)
	with open(path.join(out_dir,".bidsignore"), "w+") as f:
		f.write('*_cbv.*')

	# BIDS needs a descriptor file
	if not dataset_name:
		dataset_name = measurements_base
	description = {
		'Name':dataset_name,
		'BIDSVersion':'1.0.2',
		}
	with open(path.join(out_dir,'dataset_description.json'), 'w') as f:
		json.dump(description, f)

