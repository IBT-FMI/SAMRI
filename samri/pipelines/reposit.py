from os import path, remove
from samri.pipelines.extra_functions import flip_if_needed, get_data_selection, get_bids_scan, write_bids_metadata_file, write_bids_events_file, write_bids_physio_file, BIDS_METADATA_EXTRACTION_DICTS
import os

import argh
import re
import inspect
import json
import os
import shutil
import time

import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import pandas as pd
#from nipype.interfaces.bru2nii import Bru2

from samri.pipelines.utils import sessions_file, ss_to_path
from samri.pipelines.extra_interfaces import Bru2
from samri.utilities import N_PROCS

try:
	    FileNotFoundError
except NameError:
	    FileNotFoundError = IOError

N_PROCS=max(N_PROCS-4, 2)

@argh.arg('-e','--exclude', type=json.loads)
@argh.arg('-d','--diffusion-match', type=json.loads)
@argh.arg('-f','--functional-match', type=json.loads)
@argh.arg('-s','--structural-match', type=json.loads)
@argh.arg('-m','--measurements', nargs='*', type=str)
def bru2bids(measurements_base,
	bids_extra=['acq','run'],
	dataset_authors=[],
	dataset_funding=[],
	dataset_license='',
	dataset_name=False,
	debug=False,
	diffusion_match={},
	exclude={},
	functional_match={},
	inflated_size=False,
	keep_crashdump=False,
	keep_work=False,
	measurements=[],
	n_procs=N_PROCS,
	out_base=None,
	structural_match={},
	workflow_name='bids',
	):
	"""
	Convert and reorganize Bruker "raw" directories (2dseq and ParaVision-formatted metadata files) into a BIDS-organized file hierarchy containing NIfTI files and associated metadata.
	If any exist, this workflow also reposits COSplay event files (already written according to BIDS) in the correct place in the output hierarchy.

	Parameters
	----------

	measurements_base : str
		Path of the top level directory containing all the Bruker ParaVision scan directories to be converted and reformatted.
	bids_extra : list, optional
		List of strings denoting optional BIDS fields to include in the resulting file names.
		Accepted items are 'acq' and 'run'.
	dataset_authors : list of string, optional
		A list of dataset author names, which will be written into the BIDS metadata file.
		Generally not needed, unless this is important for you.
	dataset_funding : list, optional
		List of strings specifying funding sources, corresponds to the BIDS "Funding" field.
	dataset_license : string, optional
		A dataset license name that will be written into the BIDS metadata file.
		Generally not needed, unless this is important for you.
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
	inflated_size : bool, optional
		Whether to inflate the voxel size reported by the scanner when converting the data to NIfTI.
		Setting this to `True` multiplies the voxel edge lengths by 10 (i.e. the volume by 1000); this is occasionally done in some small animal pipelines, which use routines designed exclusively for human data.
		Unless you are looking to reproduce such a workflow, this should be set to `True`.
	keep_crashdump : bool, optional
		Whether to keep the crashdump directory (containing all the crash reports for intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	measurements : list, optional
		Whitelist of Bruker ParaVision scan directories to consider.
	n_procs : int, optional
		Maximum number of processes which to simultaneously spawn for the workflow.
		If not explicitly defined, this is automatically calculated from the number of available cores and under the assumption that the workflow will be the main process running for the duration that it is running.
	out_base : str, optional
		Base directory in which to place the BIDS reposited data.
		If not present the BIDS records will be created in the `measurements_base` directory.
	structural_match : dict, optional
		A dictionary with any combination of "session", "subject", "task", and "acquisition" as keys and corresponding lists of identifiers as values.
		Only structural scans matching all identifiers will be included - i.e. this is a whitelist.
	workflow_name : str, optional
		Top level name for the output directory.
	"""

	measurements_base = path.abspath(path.expanduser(measurements_base))
	if out_base:
		out_base = path.abspath(path.expanduser(out_base))
	else:
		out_base = measurements_base
	out_dir = path.join(out_base,workflow_name)
	workdir_name = workflow_name+'_work'
	workdir = path.join(out_base,workdir_name)

	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	# BIDS needs a descriptor file
	if not dataset_name:
		dataset_name = measurements_base
	description = {
		'Name':dataset_name,
		'BIDSVersion':'1.4.1',
		}
	if dataset_authors:
		description['Authors'] = dataset_authors
	if dataset_funding:
		description['Funding'] = dataset_funding
	if dataset_license:
		description['License'] = dataset_license
	with open(path.join(out_dir,'dataset_description.json'), 'w') as f:
		json.dump(description, f, indent=1)
		f.write("\n")

	# define measurement directories to be processed, and populate the list either with the given include_measurements, or with an intelligent selection
	functional_scan_types = diffusion_scan_types = structural_scan_types = []
	data_selection = pd.DataFrame([])
	if structural_match:
		s_data_selection = get_data_selection(measurements_base,
			match=structural_match,
			exclude=exclude,
			measurements=measurements,
			)
		print(s_data_selection.columns)
		structural_scan_types = list(s_data_selection['scan_type'].unique())
		struct_ind = s_data_selection.index.tolist()
		data_selection = pd.concat([data_selection,s_data_selection], sort=True)
	if functional_match:
		f_data_selection = get_data_selection(measurements_base,
			match=functional_match,
			exclude=exclude,
			measurements=measurements,
			)
		print(f_data_selection)
		functional_scan_types = list(f_data_selection['scan_type'].unique())
		func_ind = f_data_selection.index.tolist()
		data_selection = pd.concat([data_selection,f_data_selection], sort=True)
	if diffusion_match:
		d_data_selection = get_data_selection(measurements_base,
			match=diffusion_match,
			exclude=exclude,
			measurements=measurements,
			)
		diffusion_scan_types = list(d_data_selection['scan_type'].unique())
		dwi_ind = d_data_selection.index.tolist()
		data_selection = pd.concat([data_selection,d_data_selection], sort=True)

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
		if not os.path.exists(workdir):
			os.makedirs(workdir)
		f_data_selection.to_csv(path.join(workdir,'f_data_selection.csv'))
		get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getfullargspec(get_bids_scan)[0], output_names=[
			'scan_path', 'typ', 'task', 'nii_path', 'nii_name', 'eventfile_name', 'subject_session', 'metadata_filename', 'dict_slice', 'ind_type',
			]))
		get_f_scan.inputs.ignore_exception = True
		get_f_scan.inputs.data_selection = f_data_selection
		get_f_scan.inputs.bids_base = measurements_base
		get_f_scan.iterables = ("ind_type", func_ind)

		f_bru2nii = pe.Node(interface=Bru2(), name="f_bru2nii")
		f_bru2nii.inputs.actual_size = not inflated_size
		f_bru2nii.inputs.compress = True

		f_metadata_file = pe.Node(name='metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getfullargspec(write_bids_metadata_file)[0], output_names=['out_file']))
		f_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

		f_flip = pe.Node(name='f_flip', interface=util.Function(function=flip_if_needed,input_names=inspect.getfullargspec(flip_if_needed)[0], output_names=['out_file']))
		f_flip.inputs.data_selection = f_data_selection

		events_file = pe.Node(name='events_file', interface=util.Function(function=write_bids_events_file,input_names=inspect.getfullargspec(write_bids_events_file)[0], output_names=['out_file']))
		events_file.ignore_exception = True

		physio_file = pe.Node(name='physio_file', interface=util.Function(function=write_bids_physio_file,input_names=inspect.getfullargspec(write_bids_physio_file)[0], output_names=['out_file','out_metadata_file']))

		workflow_connections = [
			(get_f_scan, datasink, [(('subject_session',ss_to_path), 'container')]),
			(get_f_scan, f_bru2nii, [('scan_path', 'input_dir')]),
			(get_f_scan, f_bru2nii, [('nii_name', 'output_filename')]),
			(get_f_scan, f_flip, [('ind_type', 'ind')]),
			(get_f_scan, f_flip, [('nii_name', 'output_filename')]),
			(f_bru2nii, f_flip, [('nii_file', 'nii_path')]),
			(f_flip, datasink, [('out_file', 'func')]),
			(f_metadata_file, events_file, [('out_file', 'metadata_file')]),
			(f_bru2nii, events_file, [('nii_file', 'timecourse_file')]),
			(get_f_scan, f_metadata_file, [
				('metadata_filename', 'out_file'),
				('task', 'task'),
				('scan_path', 'scan_dir')
				]),
			(get_f_scan, events_file, [
				('eventfile_name', 'out_file'),
				('task', 'task'),
				('scan_path', 'scan_dir')
				]),
			(get_f_scan, physio_file, [
				('nii_name', 'nii_name'),
				('scan_path', 'scan_dir')
				]),
			(events_file, datasink, [('out_file', 'func.@events')]),
			(physio_file, datasink, [('out_file', 'func.@physio')]),
			(physio_file, datasink, [('out_metadata_file', 'func.@meta_physio')]),
			(f_metadata_file, datasink, [('out_file', 'func.@metadata')]),
			]
		crashdump_dir = path.join(out_base,workflow_name+'_crashdump')
		workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
		if debug:
			workflow_config['logging'] = {
				'workflow_level':'DEBUG',
				'utils_level':'DEBUG',
				'interface_level':'DEBUG',
				'filemanip_level':'DEBUG',
				'log_to_file':'true',
				}

		workflow = pe.Workflow(name=workdir_name)
		workflow.connect(workflow_connections)
		workflow.base_dir = path.join(out_base)
		workflow.config = workflow_config
		try:
			workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph_functional.dot"), graph2use="hierarchical", format="png")
		except OSError:
			print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

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
		# We check for the directory, since it gets deleted after a successful execution.
		if not os.path.exists(workdir):
			os.makedirs(workdir)
		d_data_selection.to_csv(path.join(workdir,'d_data_selection.csv'))
		get_d_scan = pe.Node(name='get_d_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getfullargspec(get_bids_scan)[0], output_names=[
			'scan_path', 'typ', 'task', 'nii_path', 'nii_name', 'eventfile_name', 'subject_session', 'metadata_filename', 'dict_slice', 'ind_type',
			]))
		get_d_scan.inputs.ignore_exception = True
		get_d_scan.inputs.data_selection = d_data_selection
		get_d_scan.inputs.extra = ['acq']
		get_d_scan.inputs.bids_base = measurements_base
		get_d_scan.iterables = ("ind_type", dwi_ind)

		d_bru2nii = pe.Node(interface=Bru2(), name="d_bru2nii")
		d_bru2nii.inputs.force_conversion=True
		d_bru2nii.inputs.actual_size = not inflated_size
		d_bru2nii.inputs.compress = True

		d_metadata_file = pe.Node(name='metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getfullargspec(write_bids_metadata_file)[0], output_names=['out_file']))
		d_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

		workflow_connections = [
			(get_d_scan, datasink, [(('subject_session',ss_to_path), 'container')]),
			(get_d_scan, d_bru2nii, [('scan_path', 'input_dir')]),
			(get_d_scan, d_bru2nii, [('nii_name', 'output_filename')]),
			(d_bru2nii, datasink, [('nii_file', 'dwi')]),
			(get_d_scan, d_metadata_file, [
				('metadata_filename', 'out_file'),
				('task', 'task'),
				('scan_path', 'scan_dir')
				]),
			(d_metadata_file, datasink, [('out_file', 'dwi.@metadata')]),
			]

		crashdump_dir = path.join(out_base,workflow_name+'_crashdump')
		workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
		if debug:
			workflow_config['logging'] = {
				'workflow_level':'DEBUG',
				'utils_level':'DEBUG',
				'interface_level':'DEBUG',
				'filemanip_level':'DEBUG',
				'log_to_file':'true',
				}

		workflow = pe.Workflow(name=workdir_name)
		workflow.connect(workflow_connections)
		workflow.base_dir = path.join(out_base)
		workflow.config = workflow_config
		try:
			workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph_diffusion.dot"), graph2use="hierarchical", format="png")
		except OSError:
			print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

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
		# We check for the directory, since it gets deleted after a successful execution.
		if not os.path.exists(workdir):
			os.makedirs(workdir)
		s_data_selection.to_csv(path.join(workdir,'s_data_selection.csv'))
		get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getfullargspec(get_bids_scan)[0], output_names=[
			'scan_path', 'typ', 'task', 'nii_path', 'nii_name', 'eventfile_name', 'subject_session', 'metadata_filename', 'dict_slice', 'ind_type',
			]))
		get_s_scan.inputs.ignore_exception = True
		get_s_scan.inputs.data_selection = s_data_selection
		get_s_scan.inputs.extra = ['acq']
		get_s_scan.inputs.bids_base = measurements_base
		get_s_scan.iterables = ("ind_type", struct_ind)

		s_bru2nii = pe.Node(interface=Bru2(), name="s_bru2nii")
		s_bru2nii.inputs.force_conversion=True
		s_bru2nii.inputs.actual_size = not inflated_size
		s_bru2nii.inputs.compress = True

		s_metadata_file = pe.Node(name='metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getfullargspec(write_bids_metadata_file)[0], output_names=['out_file']))
		s_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

		s_flip = pe.Node(name='s_flip', interface=util.Function(function=flip_if_needed,input_names=inspect.getfullargspec(flip_if_needed)[0], output_names=['out_file']))
		s_flip.inputs.data_selection = s_data_selection

		workflow_connections = [
			(get_s_scan, datasink, [(('subject_session',ss_to_path), 'container')]),
			(get_s_scan, s_bru2nii, [('scan_path', 'input_dir')]),
			(get_s_scan, s_bru2nii, [('nii_name', 'output_filename')]),
			(get_s_scan, s_flip, [('ind_type', 'ind')]),
			(get_s_scan, s_flip, [('nii_name', 'output_filename')]),
			(s_bru2nii, s_flip, [('nii_file', 'nii_path')]),
			(s_flip, datasink, [('out_file', 'anat')]),
			(get_s_scan, s_metadata_file, [
				('metadata_filename', 'out_file'),
				('task', 'task'),
				('scan_path', 'scan_dir')
				]),
			(s_metadata_file, datasink, [('out_file', 'anat.@metadata')]),
			]
		crashdump_dir = path.join(out_base,workflow_name+'_crashdump')
		workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
		if debug:
			workflow_config['logging'] = {
				'workflow_level':'DEBUG',
				'utils_level':'DEBUG',
				'interface_level':'DEBUG',
				'filemanip_level':'DEBUG',
				'log_to_file':'true',
				}

		workflow = pe.Workflow(name=workdir_name)
		workflow.connect(workflow_connections)
		workflow.base_dir = path.join(out_base)
		workflow.config = workflow_config
		try:
			workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph_structural.dot"), graph2use="hierarchical", format="png")
		except OSError:
			print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

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

	# Copy participants/subjects file
	for ext in ['.tsv','.json']:
		participants_file = path.join(measurements_base,'participants')+ext
		participants_file_copy = path.join(out_dir,'participants')+ext
		try:
			shutil.copyfile(participants_file,participants_file_copy)
		except FileNotFoundError:
			pass

	# Create sessions files
	sessions_file(out_dir, data_selection)

	if len(os.listdir(out_dir) ) == 0:
		shutil.rmtree(out_dir)
		print("Empty BIDS directory was produced, removing.")

	# Introduce the notion of validation:
	print('\n'
		'USER NOTICE:\n'
		'To ensure conformity with the most recent release of the BIDS standard, you may want to submit the dataset to the online\n'
		'validator (this will *not* require you to actually upload any of the data):\n'
		'https://bids-standard.github.io/bids-validator/'
		)
