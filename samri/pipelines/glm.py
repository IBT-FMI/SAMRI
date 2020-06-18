from os import path, listdir, getcwd, remove

import inspect
import pandas as pd
import re
import shutil
import multiprocessing as mp
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import os
from copy import deepcopy
from itertools import product
from nipype.interfaces import fsl
from nipype.interfaces.fsl.model import Level1Design
#from nipype.algorithms.modelgen import SpecifyModel

from samri.pipelines.extra_interfaces import SpecifyModel
from samri.pipelines.extra_functions import select_from_datafind_df, corresponding_eventfile, get_bids_scan, physiofile_ts, eventfile_add_habituation, regressor
from samri.pipelines.utils import bids_dict_to_source, ss_to_path, iterfield_selector, datasource_exclude, bids_dict_to_dir
from samri.report.roi import ts
from samri.utilities import N_PROCS

N_PROCS=max(N_PROCS-2, 1)

def l1(preprocessing_dir,
	bf_path='',
	convolution='gamma',
	debug=False,
	exclude={},
	habituation='confound',
	highpass_sigma=225,
	lowpass_sigma=False,
	include={},
	keep_work=False,
	out_base="",
	mask="",
	match={},
	temporal_derivatives=True,
	tr=1,
	workflow_name="generic",
	modality="cbv",
	n_jobs_percentage=1,
	invert=False,
	user_defined_contrasts=False,
	):
	"""Calculate subject level GLM statistic scores.

	Parameters
	----------

	bf_path : str, optional
		Basis set path. It should point to a text file in the so-called FEAT/FSL "#2" format (1 entry per volume).
		If selected, this overrides the `convolution` option and sets it to "custom".
	convolution : str or dict, optional
		Select convolution method.
	exclude : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified matching entries will be excluded in the analysis.
	debug : bool, optional
		Whether to enable nipype debug mode.
		This increases logging.
	habituation : {"", "confound", "separate_contrast", "in_main_contrast"}, optional
		How the habituation regressor should be handled.
		Anything which evaluates as False (though we recommend "") means no habituation regressor will be introduced.
	highpass_sigma : int, optional
		Highpass threshold (in seconds).
	include : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified only matching entries will be included in the analysis.
	invert : bool
		If true the values will be inverted with respect to zero.
		This is commonly used for iron nano-particle Cerebral Blood Volume (CBV) measurements.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	out_base : str, optional
		Path to the directory inside which both the working directory and the output directory will be created.
	mask : str, optional
		Path to the brain mask which shall be used to define the brain volume in the analysis.
		This has to point to an existing NIfTI file containing zero and one values only.
	n_jobs_percentage : float, optional
		Percentage of the cores present on the machine which to maximally use for deploying jobs in parallel.
	temporal_derivatives : int, optional
		Whether to add temporal derivatives of the main regressors in the model. This only applies if the convolution parameter is set to 'dgamma' or 'gamma'.
	tr : int, optional
		Repetition time, in seconds.
	workflow_name : str, optional
		Name of the workflow; this will also be the name of the final output directory produced under `out_dir`.
	"""

	from samri.pipelines.utils import bids_data_selection

	preprocessing_dir = path.abspath(path.expanduser(preprocessing_dir))
	out_base = path.abspath(path.expanduser(out_base))

	data_selection = bids_data_selection(preprocessing_dir, structural_match=False, functional_match=match, subjects=False, sessions=False)
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	ind = data_selection.index.tolist()

	out_dir = path.join(out_base,workflow_name)
	workdir_name = workflow_name+'_work'
	workdir = path.join(out_base,workdir_name)
	if not os.path.exists(workdir):
		os.makedirs(workdir)
	data_selection.to_csv(path.join(workdir,'data_selection.csv'))

	get_scan = pe.Node(name='get_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'events_name', 'subject_session', 'metadata_filename', 'dict_slice', 'ind_type']))
	get_scan.inputs.ignore_exception = True
	get_scan.inputs.data_selection = data_selection
	get_scan.inputs.bids_base = preprocessing_dir
	get_scan.iterables = ("ind_type", ind)

	eventfile = pe.Node(name='eventfile', interface=util.Function(function=corresponding_eventfile,input_names=inspect.getargspec(corresponding_eventfile)[0], output_names=['eventfile']))

	if invert:
		invert = pe.Node(interface=fsl.ImageMaths(), name="invert")
		invert.inputs.op_string = '-mul -1'

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = highpass_sigma

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	if bf_path:
		convolution = 'custom'
	if convolution == 'custom':
		bf_path = path.abspath(path.expanduser(bf_path))
		level1design.inputs.bases = {"custom": {"bfcustompath":bf_path}}
	elif convolution == 'gamma':
		# We are not adding derivatives here, as these conflict with the habituation option.
		# !!! This is not difficult to solve, and would only require the addition of an elif condition to the habituator definition, which would add multiple column copies for each of the derivs.
		level1design.inputs.bases = {'gamma': {'derivs':temporal_derivatives, 'gammasigma':30, 'gammadelay':10}}
	elif convolution == 'dgamma':
		# We are not adding derivatives here, as these conflict with the habituation option.
		# !!! This is not difficult to solve, and would only require the addition of an elif condition to the habituator definition, which would add multiple column copies for each of the derivs.
		level1design.inputs.bases = {'dgamma': {'derivs':temporal_derivatives,}}
	elif isinstance(convolution, dict):
		level1design.inputs.bases = convolution
	else:
		raise ValueError('You have specified an invalid value for the "convoltion" parameter of.')
	level1design.inputs.model_serial_correlations = True

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')
	if mask == 'mouse':
		mask = '/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii'
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	else:
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	glm.interface.mem_gb = 6

	out_file_name_base = 'sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_run-{{run}}_{{modality}}_{}.{}'

	betas_filename = pe.Node(name='betas_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	betas_filename.inputs.source_format = out_file_name_base.format('betas','nii.gz')
	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = out_file_name_base.format('cope','nii.gz')
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = out_file_name_base.format('varcb','nii.gz')
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = out_file_name_base.format('tstat','nii.gz')
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = out_file_name_base.format('zstat','nii.gz')
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = out_file_name_base.format('pstat','nii.gz')
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = out_file_name_base.format('pfstat','nii.gz')
	design_filename = pe.Node(name='design_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	design_filename.inputs.source_format = out_file_name_base.format('design','mat')
	designimage_filename = pe.Node(name='designimage_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	designimage_filename.inputs.source_format = out_file_name_base.format('design','png')

	design_rename = pe.Node(interface=util.Rename(), name='design_rename')
	designimage_rename = pe.Node(interface=util.Rename(), name='designimage_rename')

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(out_base,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(get_scan, eventfile, [('nii_path', 'timecourse_file')]),
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		(modelgen, glm, [('con_file', 'contrasts')]),
		(get_scan, datasink, [(('dict_slice',bids_dict_to_dir), 'container')]),
		(get_scan, betas_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, cope_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, varcb_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, tstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, zstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, pstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, pfstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, design_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, designimage_filename, [('dict_slice', 'bids_dictionary')]),
		(betas_filename, glm, [('filename', 'out_file')]),
		(cope_filename, glm, [('filename', 'out_cope')]),
		(varcb_filename, glm, [('filename', 'out_varcb_name')]),
		(tstat_filename, glm, [('filename', 'out_t_name')]),
		(zstat_filename, glm, [('filename', 'out_z_name')]),
		(pstat_filename, glm, [('filename', 'out_p_name')]),
		(pfstat_filename, glm, [('filename', 'out_pf_name')]),
		(modelgen, design_rename, [('design_file', 'in_file')]),
		(modelgen, designimage_rename, [('design_image', 'in_file')]),
		(design_filename, design_rename, [('filename', 'format_string')]),
		(designimage_filename, designimage_rename, [('filename', 'format_string')]),
		(glm, datasink, [('out_pf', '@pfstat')]),
		(glm, datasink, [('out_p', '@pstat')]),
		(glm, datasink, [('out_z', '@zstat')]),
		(glm, datasink, [('out_t', '@tstat')]),
		(glm, datasink, [('out_cope', '@cope')]),
		(glm, datasink, [('out_varcb', '@varcb')]),
		(glm, datasink, [('out_file', '@betas')]),
		(design_rename, datasink, [('out_file', '@design')]),
		(designimage_rename, datasink, [('out_file', '@designimage')]),
		]

	if habituation:
		level1design.inputs.orthogonalization = {1: {0:0,1:0,2:0}, 2: {0:1,1:1,2:0}}
		specify_model.inputs.bids_condition_column = 'samri_l1_regressors'
		specify_model.inputs.bids_amplitude_column = 'samri_l1_amplitude'
		add_habituation = pe.Node(name='add_habituation', interface=util.Function(function=eventfile_add_habituation,input_names=inspect.getargspec(eventfile_add_habituation)[0], output_names=['out_file']))
		# Regressor names need to be prefixed with "e" plus a numerator so that Level1Design will be certain to conserve the order.
		add_habituation.inputs.original_stimulation_value='1stim'
		add_habituation.inputs.habituation_value='2habituation'
		workflow_connections.extend([
			(eventfile, add_habituation, [('eventfile', 'in_file')]),
			(add_habituation, specify_model, [('out_file', 'bids_event_file')]),
			])
	if user_defined_contrasts:
		level1design.inputs.contrasts = user_defined_contrasts
		workflow_connections.extend([
			(eventfile, specify_model, [('eventfile', 'bids_event_file')]),
			])
	elif not habituation:
		specify_model.inputs.bids_condition_column = ''
		if convolution == 'custom':
			level1design.inputs.contrasts = [('allStim','T', ['ev0'],[1])]
		elif convolution in ['gamma','dgamma']:
			level1design.inputs.contrasts = [('allStim','T', ['ev0','ev1'],[1,1])]
		workflow_connections.extend([
			(eventfile, specify_model, [('eventfile', 'bids_event_file')]),
			])
	#condition names as defined in eventfile_add_habituation:
	elif habituation=="separate_contrast":
		level1design.inputs.contrasts = [('stim','T', ['1stim','2habituation'],[1,0]),('hab','T', ['1stim','2habituation'],[0,1])]
	elif habituation=="in_main_contrast":
		level1design.inputs.contrasts = [('all','T', ['1stim','2habituation'],[1,1])]
	elif habituation=="confound":
		level1design.inputs.contrasts = [('stim','T', ["1stim", "2habituation"],[1,0])]
	else:
		raise ValueError('The value you have provided for the `habituation` parameter, namely "{}", is invalid. Please choose one of: {{None, False,"","confound","in_main_contrast","separate_contrast"}}'.format(habituation))

	if highpass_sigma or lowpass_sigma:
		bandpass = pe.Node(interface=fsl.maths.TemporalFilter(), name="bandpass")
		bandpass.inputs.highpass_sigma = highpass_sigma
		bandpass.interface.mem_gb = 16
		if lowpass_sigma:
			bandpass.inputs.lowpass_sigma = lowpass_sigma
		else:
			bandpass.inputs.lowpass_sigma = tr
		if invert:
			workflow_connections.extend([
				(get_scan, invert, [('nii_path', 'in_file')]),
				(invert, bandpass, [('out_file', 'in_file')]),
				(bandpass, specify_model, [('out_file', 'functional_runs')]),
				(bandpass, glm, [('out_file', 'in_file')]),
				(bandpass, datasink, [('out_file', '@ts_file')]),
				(get_scan, bandpass, [('nii_name', 'out_file')]),
				])
		else:
			workflow_connections.extend([
				(get_scan, bandpass, [('nii_path', 'in_file')]),
				(bandpass, specify_model, [('out_file', 'functional_runs')]),
				(bandpass, glm, [('out_file', 'in_file')]),
				(bandpass, datasink, [('out_file', '@ts_file')]),
				(get_scan, bandpass, [('nii_name', 'out_file')]),
				])
	else:
		if invert:
			workflow_connections.extend([
				(get_scan, invert, [('nii_path', 'in_file')]),
				(invert, specify_model, [('out_file', 'functional_runs')]),
				(invert, glm, [('out_file', 'in_file')]),
				(invert, datasink, [('out_file', '@ts_file')]),
				(get_scan, invert, [('nii_name', 'out_file')]),
				])
		else:
			workflow_connections.extend([
				(get_scan, specify_model, [('nii_path', 'functional_runs')]),
				(get_scan, glm, [('nii_path', 'in_file')]),
				(get_scan, datasink, [('nii_path', '@ts_file')]),
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

	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_base
	workflow.config = workflow_config
	try:
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	except OSError:
		print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

	n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_work:
		shutil.rmtree(path.join(out_base,workdir_name))

def l1_physio(preprocessing_dir, physiology_identifier,
	bf_path='',
	convolution='gamma',
	debug=False,
	exclude={},
	highpass_sigma=225,
	lowpass_sigma=False,
	include={},
	keep_work=False,
	out_base="",
	mask="",
	match={},
	temporal_derivatives=True,
	tr=1,
	workflow_name="generic",
	modality="cbv",
	n_jobs_percentage=1,
	invert=False,
	):
	"""Calculate subject level GLM statistic scores.

	Parameters
	----------

	bf_path : str, optional
		Basis set path. It should point to a text file in the so-called FEAT/FSL "#2" format (1 entry per volume).
		If selected, this overrides the `convolution` option and sets it to "custom".
	convolution : str or dict, optional
		Select convolution method.
	exclude : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified matching entries will be excluded in the analysis.
	debug : bool, optional
		Whether to enable nipype debug mode.
		This increases logging.
	highpass_sigma : int, optional
		Highpass threshold (in seconds).
	include : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified only matching entries will be included in the analysis.
	invert : bool
		If true the values will be inverted with respect to zero.
		This is commonly used for iron nano-particle Cerebral Blood Volume (CBV) measurements.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	out_base : str, optional
		Path to the directory inside which both the working directory and the output directory will be created.
	mask : str, optional
		Path to the brain mask which shall be used to define the brain volume in the analysis.
		This has to point to an existing NIfTI file containing zero and one values only.
	n_jobs_percentage : float, optional
		Percentage of the cores present on the machine which to maximally use for deploying jobs in parallel.
	temporal_derivatives : int, optional
		Whether to add temporal derivatives of the main regressors in the model. This only applies if the convolution parameter is set to 'dgamma' or 'gamma'.
	tr : int, optional
		Repetition time, in seconds.
	workflow_name : str, optional
		Name of the workflow; this will also be the name of the final output directory produced under `out_dir`.
	"""

	from samri.pipelines.utils import bids_data_selection

	preprocessing_dir = path.abspath(path.expanduser(preprocessing_dir))
	out_base = path.abspath(path.expanduser(out_base))

	data_selection = bids_data_selection(preprocessing_dir, structural_match=False, functional_match=match, subjects=False, sessions=False)
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	ind = data_selection.index.tolist()

	out_dir = path.join(out_base,workflow_name)
	workdir_name = workflow_name+'_work'
	workdir = path.join(out_base,workdir_name)
	if not os.path.exists(workdir):
		os.makedirs(workdir)
	data_selection.to_csv(path.join(workdir,'data_selection.csv'))

	get_scan = pe.Node(name='get_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'events_name', 'subject_session', 'metadata_filename', 'dict_slice', 'ind_type']))
	get_scan.inputs.ignore_exception = True
	get_scan.inputs.data_selection = data_selection
	get_scan.inputs.bids_base = preprocessing_dir
	get_scan.iterables = ("ind_type", ind)

	physiofile = pe.Node(name='physiofile', interface=util.Function(function=physiofile_ts,input_names=inspect.getargspec(physiofile_ts)[0], output_names=['nii_file','ts']))
	physiofile.inputs.column_name = physiology_identifier
	physiofile.inputs.ignore_exception = True

	make_regressor = pe.Node(name='make_regressor', interface=util.Function(function=regressor,input_names=inspect.getargspec(regressor)[0], output_names=['output']))
	make_regressor.inputs.hpf = highpass_sigma
	make_regressor.inputs.name = physiology_identifier

	if invert:
		invert = pe.Node(interface=fsl.ImageMaths(), name="invert")
		invert.inputs.op_string = '-mul -1'

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	if bf_path:
		convolution = 'custom'
	if convolution == 'custom':
		bf_path = path.abspath(path.expanduser(bf_path))
		level1design.inputs.bases = {"custom": {"bfcustompath":bf_path}}
		level1design.inputs.contrasts = [('allStim','T', ['ev0'],[1])]
	elif convolution == 'gamma':
		level1design.inputs.bases = {'gamma': {'derivs':temporal_derivatives, 'gammasigma':30, 'gammadelay':10}}
		#level1design.inputs.contrasts = [('allStim','T', ['ev0','ev1'],[1,1])]
		level1design.inputs.contrasts = [('allStim','T', [physiology_identifier],[1])]
	elif convolution == 'dgamma':
		level1design.inputs.bases = {'dgamma': {'derivs':temporal_derivatives,}}
		level1design.inputs.contrasts = [('allStim','T', ['ev0','ev1'],[1,1])]
	elif isinstance(convolution, dict):
		level1design.inputs.bases = convolution
	elif not convolution:
		level1design.inputs.bases = {'none': {}}
		level1design.inputs.contrasts = [('stim','T', [physiology_identifier],[1])]
	else:
		raise ValueError('You have specified an invalid value for the "convoltion" parameter of.')
	level1design.inputs.model_serial_correlations = True

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')
	if mask == 'mouse':
		mask = '/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii'
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	else:
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	glm.interface.mem_gb = 6

	out_file_name_base = 'sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_run-{{run}}_{{modality}}_{}.{}'

	betas_filename = pe.Node(name='betas_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	betas_filename.inputs.source_format = out_file_name_base.format('betas','nii.gz')
	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = out_file_name_base.format('cope','nii.gz')
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = out_file_name_base.format('varcb','nii.gz')
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = out_file_name_base.format('tstat','nii.gz')
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = out_file_name_base.format('zstat','nii.gz')
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = out_file_name_base.format('pstat','nii.gz')
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = out_file_name_base.format('pfstat','nii.gz')
	design_filename = pe.Node(name='design_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	design_filename.inputs.source_format = out_file_name_base.format('design','mat')
	designimage_filename = pe.Node(name='designimage_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	designimage_filename.inputs.source_format = out_file_name_base.format('design','png')

	design_rename = pe.Node(interface=util.Rename(), name='design_rename')
	designimage_rename = pe.Node(interface=util.Rename(), name='designimage_rename')

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(out_base,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(get_scan, physiofile, [('nii_path', 'in_file')]),
		(physiofile, make_regressor, [('ts', 'timecourse')]),
		(physiofile, make_regressor, [('nii_file', 'scan_path')]),
		(make_regressor, level1design, [('output', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		(modelgen, glm, [('con_file', 'contrasts')]),
		(get_scan, datasink, [(('dict_slice',bids_dict_to_dir), 'container')]),
		(get_scan, betas_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, cope_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, varcb_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, tstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, zstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, pstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, pfstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, design_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, designimage_filename, [('dict_slice', 'bids_dictionary')]),
		(betas_filename, glm, [('filename', 'out_file')]),
		(cope_filename, glm, [('filename', 'out_cope')]),
		(varcb_filename, glm, [('filename', 'out_varcb_name')]),
		(tstat_filename, glm, [('filename', 'out_t_name')]),
		(zstat_filename, glm, [('filename', 'out_z_name')]),
		(pstat_filename, glm, [('filename', 'out_p_name')]),
		(pfstat_filename, glm, [('filename', 'out_pf_name')]),
		(modelgen, design_rename, [('design_file', 'in_file')]),
		(modelgen, designimage_rename, [('design_image', 'in_file')]),
		(design_filename, design_rename, [('filename', 'format_string')]),
		(designimage_filename, designimage_rename, [('filename', 'format_string')]),
		(glm, datasink, [('out_pf', '@pfstat')]),
		(glm, datasink, [('out_p', '@pstat')]),
		(glm, datasink, [('out_z', '@zstat')]),
		(glm, datasink, [('out_t', '@tstat')]),
		(glm, datasink, [('out_cope', '@cope')]),
		(glm, datasink, [('out_varcb', '@varcb')]),
		(glm, datasink, [('out_file', '@betas')]),
		(design_rename, datasink, [('out_file', '@design')]),
		(designimage_rename, datasink, [('out_file', '@designimage')]),
		]

	if highpass_sigma or lowpass_sigma:
		bandpass = pe.Node(interface=fsl.maths.TemporalFilter(), name="bandpass")
		bandpass.inputs.highpass_sigma = highpass_sigma
		bandpass.interface.mem_gb = 16
		if lowpass_sigma:
			bandpass.inputs.lowpass_sigma = lowpass_sigma
		else:
			bandpass.inputs.lowpass_sigma = tr
		if invert:
			workflow_connections.extend([
				(physiofile, invert, [('nii_file', 'in_file')]),
				(invert, bandpass, [('out_file', 'in_file')]),
				(bandpass, glm, [('out_file', 'in_file')]),
				(bandpass, datasink, [('out_file', '@ts_file')]),
				(get_scan, bandpass, [('nii_name', 'out_file')]),
				])
		else:
			workflow_connections.extend([
				(physiofile, bandpass, [('nii_file', 'in_file')]),
				(bandpass, glm, [('out_file', 'in_file')]),
				(bandpass, datasink, [('out_file', '@ts_file')]),
				(get_scan, bandpass, [('nii_name', 'out_file')]),
				])
	else:
		if invert:
			workflow_connections.extend([
				(physiofile, invert, [('nii_file', 'in_file')]),
				(invert, glm, [('out_file', 'in_file')]),
				(invert, datasink, [('out_file', '@ts_file')]),
				(get_scan, invert, [('nii_name', 'out_file')]),
				])
		else:
			workflow_connections.extend([
				(physiofile, glm, [('nii_file', 'in_file')]),
				(get_scan, datasink, [('nii_path', '@ts_file')]),
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

	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_base
	workflow.config = workflow_config
	try:
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	except OSError:
		print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

	n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_work:
		shutil.rmtree(path.join(out_base,workdir_name))

def seed(preprocessing_dir, seed_mask,
	debug=False,
	erode_iterations=False,
	exclude={},
	highpass_sigma=225,
	lowpass_sigma=False,
	include={},
	keep_work=False,
	out_base="",
	mask='mouse',
	match={},
	tr=1,
	workflow_name="generic",
	modality="cbv",
	n_jobs_percentage=1,
	invert=False,
	metric='mean',
	top_voxel='',
	):
	"""Calculate subject level seed-based functional connectivity via the `fsl_glm` command.

	Parameters
	----------

	exclude : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified matching entries will be excluded in the analysis.
	debug : bool, optional
		Whether to enable nipype debug mode.
		This increases logging.
	highpass_sigma : int, optional
		Highpass threshold (in seconds).
	include : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified only matching entries will be included in the analysis.
	invert : bool
		If true the values will be inverted with respect to zero.
		This is commonly used for iron nano-particle Cerebral Blood Volume (CBV) measurements.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	out_base : str, optional
		Path to the directory inside which both the working directory and the output directory will be created.
	mask : str, optional
		Path to the brain mask which shall be used to define the brain volume in the analysis.
		This has to point to an existing NIfTI file containing zero and one values only.
	n_jobs_percentage : float, optional
		Percentage of the cores present on the machine which to maximally use for deploying jobs in parallel.
	tr : int, optional
		Repetition time, in seconds.
	workflow_name : str, optional
		Name of the workflow; this will also be the name of the final output directory produced under `out_dir`.
	metric : {'mean' or 'median'}, optional
		Whether to use the volume-wise region of interest mean of median to compute the time course.
	top_voxel : str or list, optional
		Path to NIfTI file or files based on the within-mask top-value voxel of which to create a sub-mask for time course extraction.
		Note that this file *needs* to be in the exact same affine space as the `seed_mask` file.
	"""

	from samri.pipelines.utils import bids_data_selection

	preprocessing_dir = path.abspath(path.expanduser(preprocessing_dir))
	out_base = path.abspath(path.expanduser(out_base))

	data_selection = bids_data_selection(preprocessing_dir, structural_match=False, functional_match=match, subjects=False, sessions=False)
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	ind = data_selection.index.tolist()

	out_dir = path.join(out_base,workflow_name)
	workdir_name = workflow_name+'_work'
	workdir = path.join(out_base,workdir_name)
	if not os.path.exists(workdir):
		os.makedirs(workdir)
	data_selection.to_csv(path.join(workdir,'data_selection.csv'))

	get_scan = pe.Node(name='get_scan', interface=util.Function(function=get_bids_scan,input_names=inspect.getargspec(get_bids_scan)[0], output_names=['scan_path','scan_type','task', 'nii_path', 'nii_name', 'events_name', 'subject_session', 'metadata_filename', 'dict_slice', 'ind_type']))
	get_scan.inputs.ignore_exception = True
	get_scan.inputs.data_selection = data_selection
	get_scan.inputs.bids_base = preprocessing_dir
	get_scan.iterables = ("ind_type", ind)

	compute_seed = pe.Node(name='compute_seed', interface=util.Function(function=ts,input_names=inspect.getargspec(ts)[0], output_names=['means','medians']))
	if erode_iterations:
		from samri.report.roi import erode
		eroded_seed = '/var/tmp/samri_seed_eroded_{}.nii.gz'.format(erode_iterations)
		erode(path.abspath(path.expanduser(seed_mask)), iterations=erode_iterations, save_as=eroded_seed)
		compute_seed.inputs.mask = eroded_seed
	else:
		compute_seed.inputs.mask = path.abspath(path.expanduser(seed_mask))

	make_regressor = pe.Node(name='make_regressor', interface=util.Function(function=regressor,input_names=inspect.getargspec(regressor)[0], output_names=['output']))
	make_regressor.inputs.hpf = highpass_sigma
	make_regressor.inputs.name = 'seed'

	if invert:
		invert = pe.Node(interface=fsl.ImageMaths(), name="invert")
		invert.inputs.op_string = '-mul -1'

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'none': {}}
	level1design.inputs.model_serial_correlations = True
	level1design.inputs.contrasts = [('stim','T', ['seed'],[1])]

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')

	if mask == 'mouse':
		mask = '/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii'
		(make_regressor, level1design, [('output', 'session_info')]),
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	else:
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	glm.interface.mem_gb = 6

	out_file_name_base = 'sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_run-{{run}}_{{modality}}_{}.{}'

	betas_filename = pe.Node(name='betas_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	betas_filename.inputs.source_format = out_file_name_base.format('betas','nii.gz')
	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = out_file_name_base.format('cope','nii.gz')
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = out_file_name_base.format('varcb','nii.gz')
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = out_file_name_base.format('tstat','nii.gz')
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = out_file_name_base.format('zstat','nii.gz')
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = out_file_name_base.format('pstat','nii.gz')
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = out_file_name_base.format('pfstat','nii.gz')
	design_filename = pe.Node(name='design', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	design_filename.inputs.source_format = out_file_name_base.format('design','mat')

	design_rename = pe.Node(interface=util.Rename(), name='design_rename')

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(out_base,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(make_regressor, level1design, [('output', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		(modelgen, glm, [('con_file', 'contrasts')]),
		(get_scan, datasink, [(('dict_slice',bids_dict_to_dir), 'container')]),
		(get_scan, betas_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, cope_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, varcb_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, tstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, zstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, pstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, pfstat_filename, [('dict_slice', 'bids_dictionary')]),
		(get_scan, design_filename, [('dict_slice', 'bids_dictionary')]),
		(betas_filename, glm, [('filename', 'out_file')]),
		(cope_filename, glm, [('filename', 'out_cope')]),
		(varcb_filename, glm, [('filename', 'out_varcb_name')]),
		(tstat_filename, glm, [('filename', 'out_t_name')]),
		(zstat_filename, glm, [('filename', 'out_z_name')]),
		(pstat_filename, glm, [('filename', 'out_p_name')]),
		(pfstat_filename, glm, [('filename', 'out_pf_name')]),
		(modelgen, design_rename, [('design_file', 'in_file')]),
		(design_filename, design_rename, [('filename', 'format_string')]),
		(glm, datasink, [('out_pf', '@pfstat')]),
		(glm, datasink, [('out_p', '@pstat')]),
		(glm, datasink, [('out_z', '@zstat')]),
		(glm, datasink, [('out_t', '@tstat')]),
		(glm, datasink, [('out_cope', '@cope')]),
		(glm, datasink, [('out_varcb', '@varcb')]),
		(glm, datasink, [('out_file', '@betas')]),
		(design_rename, datasink, [('out_file', '@design')]),
		]

	if top_voxel:
		voxel_filename = pe.Node(name='voxel_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
		voxel_filename.inputs.source_format = top_voxel
		workflow_connections.extend([
			(get_scan, voxel_filename, [('dict_slice', 'bids_dictionary')]),
			(voxel_filename, compute_seed, [('filename', 'top_voxel')]),
			])

	if metric == 'mean':
		workflow_connections.extend([
			(compute_seed, make_regressor, [('means', 'timecourse')]),
			])
	elif metric == 'median':
		workflow_connections.extend([
			(compute_seed, make_regressor, [('medians', 'timecourse')]),
			])
	else:
		raise ValueError('Accepted values for the `metric` parameter are "mean" and "median". You specified {}'.format(metric))

	if highpass_sigma or lowpass_sigma:
		bandpass = pe.Node(interface=fsl.maths.TemporalFilter(), name="bandpass")
		bandpass.inputs.highpass_sigma = highpass_sigma
		bandpass.interface.mem_gb = 16
		if lowpass_sigma:
			bandpass.inputs.lowpass_sigma = lowpass_sigma
		else:
			bandpass.inputs.lowpass_sigma = tr
		workflow_connections.extend([
			(get_scan, bandpass, [('nii_path', 'in_file')]),
			(bandpass, compute_seed, [('out_file', 'img_path')]),
			(bandpass, make_regressor, [('out_file', 'scan_path')]),
			(bandpass, glm, [('out_file', 'in_file')]),
			(bandpass, datasink, [('out_file', '@ts_file')]),
			(get_scan, bandpass, [('nii_name', 'out_file')]),
			])
	else:
		workflow_connections.extend([
			(get_scan, compute_seed, [('nii_path', 'img_path')]),
			(get_scan, make_regressor, [('nii_path', 'scan_path')]),
			(get_scan, glm, [('nii_path', 'in_file')]),
			(get_scan, datasink, [('nii_path', '@ts_file')]),
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

	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_base
	workflow.config = workflow_config
	try:
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	except OSError:
		print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

	n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_work:
		shutil.rmtree(path.join(out_base,workdir_name))


def getlen(a):
	return len(a)
def add_suffix(name, suffix):
	"""A function that adds suffix to a variable.

	Returns converted to string-type input variable 'name', and string-type converted variable
	'suffix' added at the end of 'name'.
	If variable 'name' is type list, all the elements are being converted to strings and
	they are being joined.

	Parameters
	----------
	name : list or str
		Will be converted to string and return with suffix
	suffix : str
		Will be converted to string and will be added at the end of 'name'.

	Returns
	-------
	str
		String type variable 'name' with suffix, the string variable 'suffix'.

	"""

	if type(name) is list:
		name = "".join([str(i) for i in name])
	return str(name)+str(suffix)

def l2_common_effect(l1_dir,
	groupby="none",
	keep_work=False,
	keep_crashdump=False,
	tr=1,
	mask='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
	match={},
	n_jobs_percentage=1,
	out_base="",
	subjects=[],
	sessions=[],
	tasks=[],
	exclude={},
	include={},
	workflow_name="generic",
	debug=False,
	target_set=[],
	run_mode='flame12',
	select_input_volume=None,
	):
	"""Determine the common effect in a sample of 3D feature maps.

	Parameters
	----------

	n_jobs_percentage : float, optional
		Percentage of the cores present on the machine which to maximally use for deploying jobs in parallel.
	run_mode : {'ols', 'fe', 'flame1', 'flame12'}, optional
		Estimation model.
	exclude : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to exclude from the matched selection (blacklist).
	include : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to include from the matched selection (whitelist).
	match : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to select.
	select_input_volume: int, optional
		Select one of multiple volumes in the fourth dimension of level-1 input files.
		This is useful for level-1 files producing multiple regressors.
	"""

	from samri.pipelines.utils import bids_data_selection

	l1_dir = path.abspath(path.expanduser(l1_dir))
	out_base = path.abspath(path.expanduser(out_base))
	mask=path.abspath(path.expanduser(mask))

	data_selection = bids_data_selection(l1_dir,
		structural_match=False,
		functional_match=match,
		subjects=False,
		sessions=False,
		verbose=True,
		)
	out_dir = path.join(out_base,workflow_name)
	workdir_name = workflow_name+'_work'
	workdir = path.join(out_base,workdir_name)
	if not os.path.exists(workdir):
		os.makedirs(workdir)

	data_selection = data_selection.sort_values(['session', 'subject'], ascending=[1, 1])
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	if include:
		for key in include:
			data_selection = data_selection[data_selection[key].isin(include[key])]
	data_selection.to_csv(path.join(workdir,'data_selection.csv'))

	varcopes_list = data_selection[data_selection['modality']=='varcb']['path'].tolist()
	copes_list = data_selection[data_selection['modality']=='cope']['path'].tolist()

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")

	level2model = pe.Node(interface=fsl.L2Model(),name='level2model')

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file = mask
	flameo.inputs.run_mode = "ols"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = out_dir
	datasink_substitutions = [('_iterable_', '')]

	if groupby == "subject_set":
		datasink_substitutions.extend([('alias', 'alias-')])
		for target in target_set:
			mylist = '.'.join(target['subject'])
			mymatch = 'subject{}.'.format(mylist)
			datasink_substitutions.extend([(mymatch, '')])
		common_fields = ''
		common_fields += 'acq-'+data_selection.acq.drop_duplicates().item()
		try:
			common_fields += '_run-'+data_selection.run.drop_duplicates().item()
		except ValueError:
			pass
		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', target_set)]

		copes = pe.Node(name='copes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		copes.inputs.bids_dictionary_override = {'modality':'cope', 'alias':''}
		copes.inputs.df = data_selection
		copes.inputs.list_output = True

		varcopes = pe.Node(name='varcopes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		varcopes.inputs.bids_dictionary_override = {'modality':'varcb', 'alias':''}
		varcopes.inputs.df = data_selection
		varcopes.inputs.list_output = True

		workflow_connections = [
			(infosource, copes, [('iterable', 'bids_dictionary')]),
			(infosource, varcopes, [('iterable', 'bids_dictionary')]),
			(infosource, copemerge, [(('iterable',dict_and_suffix,"subject","_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',dict_and_suffix,"subject","_varcb.nii.gz"), 'merged_file')]),
			]
	if groupby == "subject":
		datasink_substitutions.extend([('subject', 'sub-')])
		common_fields = ''
		common_fields += 'acq-'+data_selection.acq.drop_duplicates().item()
		try:
			common_fields += '_run-'+data_selection.run.drop_duplicates().item()
		except ValueError:
			pass

		subjects = data_selection[['subject']].drop_duplicates()
		# TODO: could not find a better way to convert pandas df column into list of dicts
		subjects_ = subjects.T.to_dict()
		subjects = [subjects_[i] for i in subjects_.keys()]

		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', subjects)]

		copes = pe.Node(name='copes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		copes.inputs.bids_dictionary_override = {'modality':'cope'}
		copes.inputs.df = data_selection
		copes.inputs.list_output = True

		varcopes = pe.Node(name='varcopes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		varcopes.inputs.bids_dictionary_override = {'modality':'varcb'}
		varcopes.inputs.df = data_selection
		varcopes.inputs.list_output = True

		workflow_connections = [
			(infosource, copes, [('iterable', 'bids_dictionary')]),
			(infosource, varcopes, [('iterable', 'bids_dictionary')]),
			(infosource, copemerge, [(('iterable',dict_and_suffix,"subject","_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',dict_and_suffix,"subject","_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "subject_task":
		#does not currently work, due to missing iterator combinations (same issue as preprocessing)
		merge = pe.Node(interface=util.Merge(2), name="merge")
		infosource = pe.Node(interface=util.IdentityInterface(fields=['subject','task']), name="infosource")
		infosource.iterables = [('subject', subjects),('task', tasks)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["subject","task",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[["subject","subject","task",]],
			varcbs=[["subject","subject","task",]]
			)
		datasource.inputs.field_template = dict(
			copes="sub-%s/ses-*/sub-%s_ses-*_task-%s_cope.nii.gz",
			varcbs="sub-%s/ses-*/sub-%s_ses-*_task-%s_varcb.nii.gz",
			)
		workflow_connections = [
			(infosource, datasource, [('subject', 'subject'),('task','task')]),
			(infosource, merge, [('subject', 'in1'),('task','in2')]),
			(merge, copemerge, [(('out',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(merge, varcopemerge, [(('out',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "session":
		datasink_substitutions.extend([('session', 'ses-')])
		common_fields = ''
		common_fields += 'acq-'+data_selection.acq.drop_duplicates().item()
		try:
			common_fields += '_run-'+data_selection.run.drop_duplicates().item()
		except ValueError:
			pass

		sessions = data_selection[['session']].drop_duplicates()
		# TODO: could not find a better way to convert pandas df column into list of dicts
		sessions_ = sessions.T.to_dict()
		sessions = [sessions_[i] for i in sessions_.keys()]

		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', sessions)]

		copes = pe.Node(name='copes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		copes.inputs.bids_dictionary_override = {'modality':'cope'}
		copes.inputs.df = data_selection
		copes.inputs.list_output = True

		varcopes = pe.Node(name='varcopes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		varcopes.inputs.bids_dictionary_override = {'modality':'varcb'}
		varcopes.inputs.df = data_selection
		varcopes.inputs.list_output = True

		workflow_connections = [
			(infosource, copes, [('iterable', 'bids_dictionary')]),
			(infosource, varcopes, [('iterable', 'bids_dictionary')]),
			(infosource, copemerge, [(('iterable',dict_and_suffix,"session","_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',dict_and_suffix,"session","_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "task":
		datasink_substitutions.extend([('task', 'task-')])
		common_fields = ''
		common_fields += 'acq-'+data_selection.acq.drop_duplicates().item()
		try:
			common_fields += '_run-'+data_selection.run.drop_duplicates().item()
		except ValueError:
			pass
		try:
			common_fields += '_ses-'+data_selection.session.drop_duplicates().item()
		except ValueError:
			pass

		iters = data_selection[['task']].drop_duplicates()
		# TODO: could not find a better way to convert pandas df column into list of dicts
		iters_ = iters.T.to_dict()
		iters = [iters_[i] for i in iters_.keys()]

		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', iters)]

		copes = pe.Node(name='copes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		copes.inputs.bids_dictionary_override = {'modality':'cope'}
		copes.inputs.df = data_selection
		copes.inputs.list_output = True

		varcopes = pe.Node(name='varcopes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		varcopes.inputs.bids_dictionary_override = {'modality':'varcb'}
		varcopes.inputs.df = data_selection
		varcopes.inputs.list_output = True

		workflow_connections = [
			(infosource, copes, [('iterable', 'bids_dictionary')]),
			(infosource, varcopes, [('iterable', 'bids_dictionary')]),
			(infosource, copemerge, [(('iterable',dict_and_suffix,"task","_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',dict_and_suffix,"task","_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "none":
		common_fields = ''
		try:
			if not data_selection.acq.drop_duplicates().isnull().values.any():
				common_fields += 'acq-'+data_selection.acq.drop_duplicates().item()
		except AttributeError:
			pass
		try:
			if not data_selection.run.drop_duplicates().isnull().values.any():
				try:
					common_fields += '_run-'+data_selection.run.drop_duplicates().item()
				except ValueError:
					pass
		except AttributeError:
			pass

		datasink_substitutions.extend([('cope1.nii.gz', common_fields+'_'+'cope.nii.gz')])
		datasink_substitutions.extend([('tstat1.nii.gz', common_fields+'_'+'tstat.nii.gz')])
		datasink_substitutions.extend([('zstat1.nii.gz', common_fields+'_'+'zstat.nii.gz')])
		datasink.inputs.substitutions = datasink_substitutions

		copes = pe.Node(name='copes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		copes.inputs.bids_dictionary_override = {'modality':'cope'}
		copes.inputs.df = data_selection
		copes.inputs.list_output = True

		varcopes = pe.Node(name='varcopes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		varcopes.inputs.bids_dictionary_override = {'modality':'varcb'}
		varcopes.inputs.df = data_selection
		varcopes.inputs.list_output = True

		copemerge.inputs.merged_file = 'cope.nii.gz'
		varcopemerge.inputs.merged_file = 'varcb.nii.gz'

		workflow_connections = []

	elif groupby == "mtask":
		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', tasks)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["group",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[['group']],
			varcbs=[['group']]
			)
		datasource.inputs.field_template = dict(
			copes="sub-*/ses-*/sub-*_ses-*_task-%s_cope.nii.gz ",
			varcbs="sub-*/ses-*/sub-*_ses-*_task-%s_varcb.nii.gz ",
			)
		workflow_connections = [
			(infosource, datasource, [('iterable', 'group')]),
			(infosource, copemerge, [(('iterable',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]

	datasink_substitutions.extend([('cope1.nii.gz', common_fields+'_'+'cope.nii.gz')])
	datasink_substitutions.extend([('tstat1.nii.gz', common_fields+'_'+'tstat.nii.gz')])
	datasink_substitutions.extend([('zstat1.nii.gz', common_fields+'_'+'zstat.nii.gz')])
	datasink.inputs.regexp_substitutions = datasink_substitutions

	if isinstance(select_input_volume,int):
		from samri.pipelines.extra_functions import extract_volumes

		copextract = pe.Node(name='copextract', interface=util.Function(function=extract_volumes, input_names=inspect.getargspec(extract_volumes)[0], output_names=['out_files']))
		copextract.inputs.axis=3
		copextract.inputs.volume=select_input_volume

		varcopextract = pe.Node(name='varcopextract', interface=util.Function(function=extract_volumes, input_names=inspect.getargspec(extract_volumes)[0], output_names=['out_files']))
		varcopextract.inputs.axis=3
		varcopextract.inputs.volume=select_input_volume

		workflow_connections.extend([
			(copes, copextract, [('selection', 'in_files')]),
			(copextract, copemerge, [('out_files', 'in_files')]),
			])
	else:
		workflow_connections.extend([
			(copes, copemerge, [('selection', 'in_files')]),
			])

	workflow_connections.extend([
		(copes, level2model, [(('selection',mylen), 'num_copes')]),
		(copemerge,flameo,[('merged_file','cope_file')]),
		(level2model,flameo, [('design_mat','design_file')]),
		(level2model,flameo, [('design_grp','cov_split_file')]),
		(level2model,flameo, [('design_con','t_con_file')]),
		(flameo, datasink, [('copes', '@copes')]),
		(flameo, datasink, [('fstats', '@fstats')]),
		(flameo, datasink, [('tstats', '@tstats')]),
		(flameo, datasink, [('zstats', '@zstats')]),
		])

	if len(varcopes_list) != 0:
		workflow_connections.extend([
			(varcopemerge,flameo,[('merged_file','var_cope_file')]),
			])
		if isinstance(select_input_volume,int):
			workflow_connections.extend([
				(varcopes, varcopextract, [('selection', 'in_files')]),
				(varcopextract, varcopemerge, [('out_files', 'in_files')]),
				])
		else:
			workflow_connections.extend([
				(varcopes, varcopemerge, [('selection', 'in_files')]),
				])

	crashdump_dir = path.join(out_base,'crashdump')
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
	workflow.base_dir = out_base
	workflow.config = workflow_config
	try:
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	except OSError:
		print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

	n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_crashdump:
		try:
			shutil.rmtree(crashdump_dir)
		except (FileNotFoundError, OSError):
			pass
	if not keep_work:
		shutil.rmtree(path.join(out_base,workdir_name))

def l2_controlled_effect(l1_dir,
	control_dir='',
	keep_work=False,
	tr=1,
	mask='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
	match={},
	control_match={},
	n_jobs_percentage=1,
	out_dir="",
	out_base="",
	subjects=[],
	sessions=[],
	tasks=[],
	exclude={},
	include={},
	workflow_name="l2_common_effect",
	debug=False,
	target_set=[],
	run_mode='flame12'
	):
	"""Determine the common effect in a sample of 3D feature maps, as established against a specified control group.

	Parameters
	----------

	control_dir : str, optional
		Directory where the BIDS hierarchy for the control data is located.
		If the value of this parameter evaluates as false, the control data will be assumed to aslo reside in `l1_dir`.
	n_jobs_percentage : float, optional
		Percentage of the cores present on the machine which to maximally use for deploying jobs in parallel.
	run_mode : {'ols', 'fe', 'flame1', 'flame12'}, optional
		Estimation model.
	exclude : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to exclude from the matched selection (blacklist).
	include : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to include from the matched selection (whitelist).
	match : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to select.
	control_match : dict, optional
		Dictionary containing keys which are BIDS field identifiers, and values which are lists of BIDS identifier values which the user wants to select the control group based on.
	"""

	from samri.pipelines.utils import bids_data_selection

	l1_dir = path.abspath(path.expanduser(l1_dir))
	out_base = path.abspath(path.expanduser(out_base))
	mask=path.abspath(path.expanduser(mask))
	if control_dir:
		control_dir = path.abspath(path.expanduser(control_dir))
	else:
		control_dir = l1_dir
	if not out_dir:
		out_dir = path.join(out_base,workflow_name)
	else:
		out_dir = path.abspath(path.expanduser(out_dir))

	data_selection = bids_data_selection(l1_dir,
		structural_match=False,
		functional_match=match,
		subjects=False,
		sessions=False,
		verbose=True,
		)
	control_data_selection = bids_data_selection(control_dir,
		structural_match=False,
		functional_match=control_match,
		subjects=False,
		sessions=False,
		verbose=True,
		)
	data_selection['control'] = False
	control_data_selection['control'] = True
	data_selection = pd.concat([control_data_selection, data_selection])
	if not out_dir:
		out_dir = path.join(out_base,workflow_name)
	workdir_name = workflow_name+'_work'
	workdir = path.join(out_base,workdir_name)
	if not os.path.exists(workdir):
		os.makedirs(workdir)

	data_selection = data_selection.sort_values(['session', 'subject'], ascending=[1, 1])
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	if include:
		for key in include:
			data_selection = data_selection[data_selection[key].isin(include[key])]
	data_selection.to_csv(path.join(workdir,'data_selection.csv'))

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file = mask
	flameo.inputs.run_mode = "ols"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = out_dir
	datasink_substitutions = [('_iterable_', '')]

	common_fields = ''
	try:
		common_fields += 'acq-'+data_selection.acq.drop_duplicates().item()
	except ValueError:
		pass
	try:
		common_fields += '_run-'+data_selection.run.drop_duplicates().item()
	except ValueError:
		pass

	copeonly = data_selection[data_selection['modality']=='cope']
	copes = copeonly['path'].tolist()
	varcopes = data_selection[data_selection['modality']=='varcb']['path'].tolist()

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	copemerge.inputs.in_files = copes
	copemerge.inputs.merged_file = 'copes.nii.gz'

	feature = [~copeonly['control']][0]
	control = [not i for i in feature]
	feature = [int(i) for i in feature]
	control = [int(i) for i in control]
	regressors = {
			'feature': feature,
			'control': control
			}

	t_contrasts = [['feature','T',['feature'], [1]]]
	contrasts = deepcopy(t_contrasts)
	contrasts.append(['controlled group', 'F', t_contrasts])

	level2model = pe.Node(interface=fsl.MultipleRegressDesign(),name='level2model')
	level2model.inputs.regressors = regressors
	level2model.inputs.contrasts = contrasts
	# create group for paired t-tests
	#level2model.inputs.groups = [i for i in range(len(feature))]

	datasink_substitutions.extend([('cope1.nii.gz', '{}_cope.nii.gz'.format(common_fields))])
	datasink_substitutions.extend([('tstat1.nii.gz','{}_tstat.nii.gz'.format(common_fields))])
	datasink_substitutions.extend([('zstat1.nii.gz','{}_zstat.nii.gz'.format(common_fields))])
	datasink_substitutions.extend([('fstat1.nii.gz','{}_fstat.nii.gz'.format(common_fields))])
	datasink_substitutions.extend([('zfstat1.nii.gz','{}_zfstat.nii.gz'.format(common_fields))])
	datasink.inputs.regexp_substitutions = datasink_substitutions

	workflow_connections = [
		(copemerge,flameo,[('merged_file','cope_file')]),
		(level2model,flameo, [('design_mat','design_file')]),
		(level2model,flameo, [('design_grp','cov_split_file')]),
		(level2model,flameo, [('design_fts','f_con_file')]),
		(level2model,flameo, [('design_con','t_con_file')]),
		(flameo, datasink, [('copes', '@copes')]),
		(flameo, datasink, [('tstats', '@tstats')]),
		(flameo, datasink, [('zstats', '@zstats')]),
		(flameo, datasink, [('fstats', '@fstats')]),
		(flameo, datasink, [('zfstats', '@zfstats')]),
		]

	if len(varcopes) != 0:
		varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")
		varcopemerge.inputs.in_files = varcopes
		varcopemerge.inputs.merged_file = 'varcopes.nii.gz'
		workflow_connections.extend([
			(varcopemerge,flameo,[('merged_file','var_cope_file')]),
			])

	workflow_config = {'execution': {'crashdump_dir': path.join(out_base,'crashdump'),}}

	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_base
	workflow.config = workflow_config
	try:
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	except RuntimeError:
		pass

	n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_work:
		shutil.rmtree(path.join(out_base,workdir_name))

def mylen(foo):
	return len(foo)

def dict_and_suffix(my_dictionary,key,suffix):
	filename = my_dictionary[key]
	if not isinstance(filename, (float, int, str)):
		filename = '+'.join([str(i) for i in filename])
	filename = str(filename)+suffix
	return filename

def l2_anova(l1_dir,
	keep_work=False,
	l2_dir="",
	loud=False,
	tr=1,
	keep_crashdump=False,
	workflow_name="generic",
	mask='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
	n_jobs_percentage=1,
	exclude={},
	include={},
	match_regex='.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_task-(?P<task>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)_(?P<stat>(cope|varcb)+)\.(?:nii|nii\.gz)'
	):

	l1_dir = path.expanduser(l1_dir)
	if not l2_dir:
		l2_dir = path.abspath(path.join(l1_dir,"..","..","l2"))

	mask=path.abspath(path.expanduser(mask))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = l1_dir
	datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()

	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.task, datafind_res.outputs.mod, datafind_res.outputs.stat, datafind_res.outputs.out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','task','modality','statistic','path'))

	data_selection = data_selection.sort_values(['session', 'subject'], ascending=[1, 1])
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	if include:
		for key in include:
			data_selection = data_selection[data_selection[key].isin(include[key])]

	copes = data_selection[data_selection['modality']=='cope']['path'].tolist()
	varcopes = data_selection[data_selection['modality']=='varcb']['path'].tolist()

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	copemerge.inputs.in_files = copes
	copemerge.inputs.merged_file = 'copes.nii.gz'

	varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")
	varcopemerge.inputs.in_files = varcopes
	varcopemerge.inputs.merged_file = 'varcopes.nii.gz'

	copeonly = data_selection[data_selection['modality']=='cope']
	regressors = {}
	for sub in copeonly['subject'].unique():
		regressor = [copeonly['subject'] == sub][0]
		regressor = [int(i) for i in regressor]
		key = "sub-"+str(sub)
		regressors[key] = regressor
	reference = str(copeonly['session'].unique()[0])
	for ses in copeonly['session'].unique()[1:]:
		regressor = [copeonly['session'] == ses][0]
		regressor = [int(i) for i in regressor]
		key = "ses-("+str(ses)+'-'+reference+')'
		regressors[key] = regressor

	sessions = [[i,'T',[i], [1]] for i in regressors.keys() if "ses-" in i]
	contrasts = deepcopy(sessions)
	contrasts.append(['anova', 'F', sessions])

	level2model = pe.Node(interface=fsl.MultipleRegressDesign(),name='level2model')
	level2model.inputs.regressors = regressors
	level2model.inputs.contrasts = contrasts

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file = mask
	# Using 'fe' instead of 'ols' is recommended (https://dpaniukov.github.io/2016/07/14/three-level-analysis-with-fsl-and-ants-2.html)
	# This has also been tested in SAMRI and shown to give better estimates.
	flameo.inputs.run_mode = "flame12"

	substitutions = []
	t_counter = 1
	f_counter = 1
	for contrast in contrasts:
		if contrast[1] == 'T':
			for i in ['cope', 'tstat', 'zstat']:
				substitutions.append((i+str(t_counter),contrast[0]+"_"+i))
			t_counter+=1
		if contrast[1] == 'F':
			for i in ['zfstat', 'fstat']:
				substitutions.append((i+str(f_counter),contrast[0]+"_"+i))
			f_counter+=1

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(l2_dir,workflow_name)
	datasink.inputs.substitutions = substitutions

	workflow_connections = [
		(copemerge,flameo,[('merged_file','cope_file')]),
		(varcopemerge,flameo,[('merged_file','var_cope_file')]),
		(level2model,flameo, [('design_mat','design_file')]),
		(level2model,flameo, [('design_grp','cov_split_file')]),
		(level2model,flameo, [('design_fts','f_con_file')]),
		(level2model,flameo, [('design_con','t_con_file')]),
		(flameo, datasink, [('copes', '@copes')]),
		(flameo, datasink, [('tstats', '@tstats')]),
		(flameo, datasink, [('zstats', '@zstats')]),
		(flameo, datasink, [('fstats', '@fstats')]),
		(flameo, datasink, [('zfstats', '@zfstats')]),
		]

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	crashdump_dir = path.join(l2_dir,"crashdump")
	workflow.config = {"execution": {"crashdump_dir": crashdump_dir}}
	workflow.base_dir = l2_dir
	try:
		workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")
	except OSError:
		print('We could not write the DOT file for visualization (`dot` function from the graphviz package). This is non-critical to the processing, but you should get this fixed.')

	n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	workflow.run(plugin="MultiProc", plugin_args={'n_procs' : n_jobs})
	if not keep_crashdump:
		try:
			shutil.rmtree(crashdump_dir)
		except (FileNotFoundError, OSError):
			pass
	if not keep_work:
		shutil.rmtree(path.join(l2_dir,workdir_name))

def sort_copes(files):
	numelements = len(files[0])
	outfiles = []
	for i in range(numelements):
		outfiles.insert(i,[])
		for j, elements in enumerate(files):
			outfiles[i].append(elements[i])
	return outfiles
