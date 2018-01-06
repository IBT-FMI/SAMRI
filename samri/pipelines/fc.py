from os import path, listdir, getcwd, remove

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
from nipype.interfaces import fsl, nipy, bru2nii

from samri.pipelines.extra_functions import force_dummy_scans, get_tr
from samri.pipelines.nodes import functional_registration, structural_registration, composite_registration
from samri.pipelines.utils import out_path, container
from samri.utilities import N_PROCS

#set all outputs to compressed NIfTI
afni.base.AFNICommand.set_default_output_type('NIFTI_GZ')
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

def seed_based(bids_base,
	seed_mask=None,
	debug=False,
	exclude={},
	include={},
	keep_crashdump=False,
	keep_work=False,
	match_regex='.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_trial-(?P<trial>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+).(?:nii|nii\.gz)',
	n_procs=N_PROCS,
	workflow_name="diagnostic",
	):
	'''Create seed-based functional connectivity maps based on a GLM timecourse analysis (with FSL's FLAMEO) for a given seed mask and a given BIDS-formatted directory tree.

	Parameters
	----------

	bids_base : string, optional
		Path to the top level of a BIDS directory tree for which to perform the diagnostic.
	debug : bool, optional
		Enable full nipype debugging support for the workflow construction and execution.
	exclude : dict, optional
		A dictionary with any subset of 'subject', 'session', 'acquisition', 'trial', 'modality', and 'path' as keys and corresponding identifiers as values.
		This is a blacklist: if this is specified only non-matching entries will be included in the analysis.
	include : dict, optional
		A dictionary with any subset of 'subject', 'session', 'acquisition', 'trial', 'modality', and 'path' as keys and corresponding identifiers as values.
		This is a whitelist: if this is specified only matching entries will be included in the analysis.
	keep_crashdump : bool, optional
		Whether to keep the crashdump directory (containing all the crash reports for intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	match_regex : str, optional
		Regex matching pattern by which to select input files. Has to contain groups named "sub", "ses", "acq", "trial", and "mod".
	n_procs : int, optional
		Maximum number of processes which to simultaneously spawn for the workflow.
		If not explicitly defined, this is automatically calculated from the number of available cores and under the assumption that the workflow will be the main process running for the duration that it is running.
	workflow_name : string, optional
		Name of the workflow execution. The output will be saved one level above the bids_base, under a directory bearing the name given here.
	'''

	bids_base = path.abspath(path.expanduser(bids_base))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = bids_base
	datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()

	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.trial, datafind_res.outputs.mod, datafind_res.outputs.out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','trial','modality','path'))

	data_selection = data_selection.sort_values(['session', 'subject'], ascending=[1, 1])
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	if include:
		for key in include:
			data_selection = data_selection[data_selection[key].isin(include[key])]

	data_selection['out_path'] = ''
	if data_selection['path'].str.contains('.nii.gz').any():
		data_selection['out_path'] = data_selection['path'].apply(lambda x: path.basename(path.splitext(path.splitext(x)[0])[0]+'_MELODIC'))
	else:
		data_selection['out_path'] = data_selection['path'].apply(lambda x: path.basename(path.splitext(x)[0]+'_MELODIC'))

	paths = data_selection['path']

	infosource = pe.Node(interface=util.IdentityInterface(fields=['path'], mandatory_inputs=False), name="infosource")
	infosource.iterables = [('path', paths)]

	dummy_scans = pe.Node(name='dummy_scans', interface=util.Function(function=force_dummy_scans,input_names=inspect.getargspec(force_dummy_scans)[0], output_names=['out_file']))
	dummy_scans.inputs.desired_dummy_scans = 10

	bids_filename = pe.Node(name='bids_filename', interface=util.Function(function=out_path,input_names=inspect.getargspec(out_path)[0], output_names=['filename']))
	bids_filename.inputs.selection_df = data_selection

	bids_container = pe.Node(name='path_container', interface=util.Function(function=container,input_names=inspect.getargspec(container)[0], output_names=['container']))
	bids_container.inputs.selection_df = data_selection

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.abspath(path.join(bids_base,'..','diagnostic'))
	datasink.inputs.parameterization = False

	report_tr = pe.Node(name='report_tr', interface=util.Function(function=get_tr,input_names=inspect.getargspec(get_tr)[0], output_names=['tr']))
	report_tr.inputs.ndim = 4

	workflow_connections = [
		(infosource, dummy_scans, [('path', 'in_file')]),
		(infosource, bids_filename, [('path', 'in_path')]),
		(bids_filename, bids_container, [('filename', 'out_path')]),
		(bids_container, datasink, [('container', 'container')]),
		(infosource, report_tr, [('path', 'in_file')]),
		(report_tr, melodic, [('tr', 'tr_sec')]),
		]


	crashdump_dir = path.abspath(path.join(bids_base,'..','diagnostic_crashdump'))
	workflow_config = {'execution': {'crashdump_dir': crashdump_dir}}
	if debug:
		workflow_config['logging'] = {
			'workflow_level':'DEBUG',
			'utils_level':'DEBUG',
			'interface_level':'DEBUG',
			'filemanip_level':'DEBUG',
			'log_to_file':'true',
			}

	workdir_name = 'diagnostic_work'
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = path.abspath(path.join(bids_base,'..'))
	workflow.config = workflow_config
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

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
		except FileNotFoundError:
			pass

	return

