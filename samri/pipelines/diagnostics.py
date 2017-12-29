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
from nipype.interfaces import afni, fsl, nipy, bru2nii

from samri.pipelines.extra_functions import get_data_selection, get_scan, write_events_file, force_dummy_scans
from samri.pipelines.nodes import functional_registration, structural_registration, composite_registration
from samri.pipelines.utils import out_path, container

from samri.utilities import N_PROCS

#set all outputs to compressed NIfTI
afni.base.AFNICommand.set_default_output_type('NIFTI_GZ')
fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

#relative paths
thisscriptspath = path.dirname(path.realpath(__file__))
scan_classification_file_path = path.join(thisscriptspath,"scan_type_classification.csv")

@argh.arg('-f', '--functional_scan_types', nargs='+', type=str)
@argh.arg('-s', '--structural_scan_types', nargs='+', type=str)
@argh.arg('--sessions', nargs='+', type=str)
@argh.arg('--subjects', nargs='+', type=str)
@argh.arg('--exclude_subjects', nargs='+', type=str)
@argh.arg('--measurements', nargs='+', type=str)
@argh.arg('--exclude_measurements', nargs='+', type=str)
def diagnose(bids_base,
	functional_scan_types=[],
	structural_scan_types=[],
	sessions=[],
	subjects=[],
	measurements=[],
	exclude_subjects=[],
	exclude_measurements=[],
	actual_size=False,
	components=None,
	loud=False,
	n_procs=N_PROCS,
	realign="time",
	tr=1,
	workflow_name="diagnostic",
	exclude={},
	include={},
	match_regex='.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_trial-(?P<trial>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+).(?:nii|nii\.gz)',
	keep_work=True,
	keep_crashdump=True,
	debug=False,
	):
	'''

	realign: {"space","time","spacetime",""}
		Parameter that dictates slictiming correction and realignment of slices. "time" (FSL.SliceTimer) is default, since it works safely. Use others only with caution!

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

	melodic = pe.Node(interface=fsl.model.MELODIC(), name="melodic")
	melodic.inputs.tr_sec = tr
	melodic.inputs.report = True
	if components:
		melodic.inputs.dim = int(components)

	workflow_connections = [
		(infosource, dummy_scans, [('path', 'in_file')]),
		(infosource, bids_filename, [('path', 'in_path')]),
		(bids_filename, bids_container, [('filename', 'out_path')]),
		(bids_filename, melodic, [('filename', 'out_dir')]),
		(bids_container, datasink, [('container', 'container')]),
		(melodic, datasink, [('out_dir', 'func')]),
		]

	if realign == "space":
		realigner = pe.Node(interface=spm.Realign(), name="realigner")
		realigner.inputs.register_to_mean = True
		workflow_connections.extend([
			(dummy_scans, realigner, [('out_file', 'in_file')]),
			(realigner, melodic, [('out_file', 'in_files')]),
			])
	elif realign == "spacetime":
		realigner = pe.Node(interface=nipy.SpaceTimeRealigner(), name="realigner")
		realigner.inputs.slice_times = "asc_alt_2"
		realigner.inputs.tr = tr
		realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
		workflow_connections.extend([
			(dummy_scans, realigner, [('out_file', 'in_file')]),
			(realigner, melodic, [('out_file', 'in_files')]),
			])
	elif realign == "time":
		realigner = pe.Node(interface=fsl.SliceTimer(), name="slicetimer")
		realigner.inputs.time_repetition = tr
		workflow_connections.extend([
			(dummy_scans, realigner, [('out_file', 'in_file')]),
			(realigner, melodic, [('slice_time_corrected_file', 'in_files')]),
			])
	else:
		workflow_connections.extend([
			(dummy_scans, melodic, [('out_file', 'in_files')]),
			])

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

