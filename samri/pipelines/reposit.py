from os import path, remove
from samri.pipelines.extra_functions import get_data_selection, get_scan, write_bids_metadata_file, write_events_file, BIDS_METADATA_EXTRACTION_DICTS

import re
import inspect
import shutil
import time

import nipype.interfaces.io as nio
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
import pandas as pd
from nipype.interfaces import bru2nii

from samri.pipelines.utils import bids_naming, ss_to_path
from samri.utilities import N_PROCS

N_PROCS=max(N_PROCS-4, 2)

def bru2bids(measurements_base,
	actual_size=True,
	debug=False,
	exclude={},
	functional_match={},
	keep_crashdump=False,
	keep_work=False,
	n_procs=N_PROCS,
	structural_match={},
	):
	"""
	Convert and reorganize Bruker "raw" directories (2dseq and ParaVision-formatted metadata files) into a BIDS-organized file hierarchy containing NIfTI files and associated metadata.
	If any exist, this workflow also reposits COSplay event files (already written according to BIDS) in the correct place in the output hierarchy.

	Parameters
	----------

	measurements_base : str
		Path of the top level directory containing all the Bruker scan directories to be converted and reformatted.
	actual_size : bool, optional
		Whether to conserve the voxel size reported by the scanner when converting the data to NIfTI.
		Setting this to `False` multiplies the voxel edge lengths by 10 (i.e. the volume by 1000); this is occasionally done in hackish small animal pipelines, which use routines designed exclusively for human data.
		Unless you are looking to reproduce such a workflow, this should be set to `True`.
	debug : bool, optional
		Whether to enable debug support.
		This prints the data selection before passing it to the nipype workflow management system, and turns on debug support in nipype (leading to more verbose logging).
	exclude : dict, optional
		A dictionary with any combination of "session", "subject", "trial" , and "acquisition" as keys and corresponding identifiers as values.
		Only scans not matching any of the listed criteria will be included in the workfolow - i.e. this is a blacklist (for functional and structural scans).
	functional_match : dict, optional
		A dictionary with any combination of "session", "subject", "trial", and "acquisition" as keys and corresponding lists of identifiers as values.
		Functional scans matching all identifiers will be included - i.e. this is a whitelist.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	keep_crashdump : bool, optional
		Whether to keep the crashdump directory (containing all the crash reports for intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	n_procs : int, optional
		Maximum number of processes which to simultaneously spawn for the workflow.
		If not explicitly defined, this is automatically calculated from the number of available cores and under the assumption that the workflow will be the main process running for the duration that it is running.
	structural_match : dict, optional
		A dictionary with any combination of "session", "subject", "trial", and "acquisition" as keys and corresponding lists of identifiers as values.
		Functional scans matching all identifiers will be included - i.e. this is a whitelist.
	"""

	measurements_base = path.abspath(path.expanduser(measurements_base))

	# define measurement directories to be processed, and populate the list either with the given include_measurements, or with an intelligent selection
	data_selection = pd.DataFrame([])
	if structural_match:
		s_data_selection = get_data_selection(measurements_base,
			match=structural_match,
			exclude=exclude,
			)
		structural_scan_types = s_data_selection['scan_type'].unique()
		data_selection = pd.concat([data_selection,s_data_selection])
	if functional_match:
		f_data_selection = get_data_selection(measurements_base,
			match=functional_match,
			exclude=exclude,
			)
		functional_scan_types = f_data_selection['scan_type'].unique()
		data_selection = pd.concat([data_selection,f_data_selection])

	# we start to define nipype workflow elements (nodes, connections, meta)
	subjects_sessions = data_selection[["subject","session"]].drop_duplicates().values.tolist()
	if debug:
		print('Data selection:')
		print(data_selection)
		print('Iterating over:')
		print(subjects_sessions)
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_session'], mandatory_inputs=False), name="infosource")
	infosource.iterables = [('subject_session', subjects_sessions)]

	get_f_scan = pe.Node(name='get_f_scan', interface=util.Function(function=get_scan,input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type','trial']))
	get_f_scan.inputs.ignore_exception = True
	get_f_scan.inputs.data_selection = data_selection
	get_f_scan.inputs.measurements_base = measurements_base
	get_f_scan.iterables = ("scan_type", functional_scan_types)

	f_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="f_bru2nii")
	f_bru2nii.inputs.actual_size=actual_size

	f_filename = pe.Node(name='bids_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
	f_filename.inputs.metadata = data_selection
	f_filename.inputs.extension=''

	f_metadata_filename = pe.Node(name='metadata_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
	f_metadata_filename.inputs.extension = ".json"
	f_metadata_filename.inputs.metadata = data_selection

	events_filename = pe.Node(name='bids_stim_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
	events_filename.inputs.suffix = "events"
	events_filename.inputs.extension = ".tsv"
	events_filename.inputs.metadata = data_selection
	events_filename.ignore_exception = True

	f_metadata_file = pe.Node(name='metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getargspec(write_bids_metadata_file)[0], output_names=['out_file']))
	f_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

	events_file = pe.Node(name='events_file', interface=util.Function(function=write_events_file,input_names=inspect.getargspec(write_events_file)[0], output_names=['out_file']))
	events_file.inputs.unchanged = True
	events_file.ignore_exception = True

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(measurements_base,"bids")
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, get_f_scan, [('subject_session', 'selector')]),
		(infosource, f_metadata_filename, [('subject_session', 'subject_session')]),
		(infosource, f_filename, [('subject_session', 'subject_session')]),
		(infosource, events_filename, [('subject_session', 'subject_session')]),
		(infosource, datasink, [(('subject_session',ss_to_path), 'container')]),
		(get_f_scan, f_metadata_filename, [('scan_type', 'scan_type')]),
		(get_f_scan, f_filename, [('scan_type', 'scan_type')]),
		(get_f_scan, f_bru2nii, [('scan_path', 'input_dir')]),
		(get_f_scan, f_metadata_file, [('scan_path', 'scan_dir')]),
		(f_metadata_filename, f_metadata_file, [('filename', 'out_file')]),
		(f_filename, f_bru2nii, [('filename', 'output_filename')]),
		(events_filename, events_file, [('filename', 'out_file')]),
		(get_f_scan, events_filename, [('scan_type', 'scan_type')]),
		(f_bru2nii, datasink, [('nii_file', 'func')]),
		(get_f_scan, events_file, [
			('trial', 'trial'),
			('scan_path', 'scan_dir')
			]),
		(events_file, datasink, [('out_file', 'func.@events')]),
		(f_metadata_file, datasink, [('out_file', 'func.@metadata')]),
		]

	try:
		if structural_scan_types.any():
			get_s_scan = pe.Node(name='get_s_scan', interface=util.Function(function=get_scan, input_names=inspect.getargspec(get_scan)[0], output_names=['scan_path','scan_type','trial']))
			get_s_scan.inputs.ignore_exception = True
			get_s_scan.inputs.data_selection = data_selection
			get_s_scan.inputs.measurements_base = measurements_base
			get_s_scan.iterables = ("scan_type", structural_scan_types)

			s_bru2nii = pe.Node(interface=bru2nii.Bru2(), name="s_bru2nii")
			s_bru2nii.inputs.force_conversion=True
			s_bru2nii.inputs.actual_size=actual_size

			s_filename = pe.Node(name='s_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
			s_filename.inputs.metadata = data_selection
			s_filename.inputs.extension=''

			s_metadata_filename = pe.Node(name='s_metadata_filename', interface=util.Function(function=bids_naming,input_names=inspect.getargspec(bids_naming)[0], output_names=['filename']))
			s_metadata_filename.inputs.extension = ".json"
			s_metadata_filename.inputs.metadata = data_selection

			s_metadata_file = pe.Node(name='s_metadata_file', interface=util.Function(function=write_bids_metadata_file,input_names=inspect.getargspec(write_bids_metadata_file)[0], output_names=['out_file']))
			s_metadata_file.inputs.extraction_dicts = BIDS_METADATA_EXTRACTION_DICTS

			workflow_connections.extend([
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
				])
	except UnboundLocalError:
		pass

	crashdump_dir = path.join(measurements_base,'bids_crashdump')
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
	workflow.base_dir = path.join(measurements_base)
	workflow.config = workflow_config
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_procs})
	if not keep_work:
		shutil.rmtree(path.join(workflow.base_dir,workdir_name))
	if not keep_crashdump:
		try:
			shutil.rmtree(crashdump_dir)
		except FileNotFoundError:
			pass
