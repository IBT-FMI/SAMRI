from os import path, listdir, getcwd, remove

import inspect
import pandas as pd
import re
import shutil
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
from copy import deepcopy
from itertools import product
from nipype.interfaces import fsl
from nipype.interfaces.fsl.model import Level1Design
#from nipype.algorithms.modelgen import SpecifyModel

from samri.pipelines.extra_interfaces import SpecifyModel
from samri.pipelines.extra_functions import select_from_datafind_df
from samri.pipelines.utils import bids_dict_to_source, ss_to_path, iterfield_selector, datasource_exclude, bids_dict_to_dir
from samri.utilities import N_PROCS

N_PROCS=max(N_PROCS-2, 1)

def l1(preprocessing_dir,
	bf_path = '~/ni_data/irfs/chr_beta1.txt',
	exclude={},
	habituation='confound',
	highpass_sigma=225,
	lowpass_sigma=False,
	include={},
	keep_work=False,
	out_dir="",
	mask="",
	match_regex='sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/func/.*?_task-(?P<task>[a-zA-Z0-9]+)_acq-(?P<acq>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)\.(?:tsv|nii|nii\.gz)',
	nprocs=N_PROCS,
	tr=1,
	workflow_name="generic",
	modality="cbv",
	):
	"""Calculate subject level GLM statistic scores.

	Parameters
	----------

	bf_path : str, optional
		Basis set path. It should point to a text file in the so-called FEAT/FSL "#2" format (1 entry per volume).
	exclude : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified matching entries will be excluded in the analysis.
	habituation : {"", "confound", "separate_contrast", "in_main_contrast"}, optional
		How the habituation regressor should be handled.
		Anything which evaluates as False (though we recommend "") means no habituation regressor will be introduced.
	highpass_sigma : int, optional
		Highpass threshold (in seconds).
	include : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified only matching entries will be included in the analysis.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	out_dir : str, optional
		Path to the directory inside which both the working directory and the output directory will be created.
	mask : str, optional
		Path to the brain mask which shall be used to define the brain volume in the analysis.
		This has to point to an existing NIfTI file containing zero and one values only.
	match_regex : str, optional
		Regex matching pattern by which to select input files. Has to contain groups named "sub", "ses", "acq", "task", and "mod".
	n_procs : int, optional
		Maximum number of processes which to simultaneously spawn for the workflow.
		If not explicitly defined, this is automatically calculated from the number of available cores and under the assumption that the workflow will be the main process running for the duration that it is running.
	tr : int, optional
		Repetition time, in seconds.
	workflow_name : str, optional
		Name of the workflow; this will also be the name of the final output directory produced under `out_dir`.
	"""

	preprocessing_dir = path.abspath(path.expanduser(preprocessing_dir))
	if not out_dir:
		out_dir = path.join(bids_base,'l1')
	else:
		out_dir = path.abspath(path.expanduser(out_dir))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = preprocessing_dir
	datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()
	out_paths = [path.abspath(path.expanduser(i)) for i in datafind_res.outputs.out_paths]
	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.task, datafind_res.outputs.mod, out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','task','modality','path'))
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	if include:
		for key in include:
			data_selection = data_selection[data_selection[key].isin(include[key])]
	bids_dictionary = data_selection[data_selection['modality']==modality].drop_duplicates().T.to_dict().values()

	infosource = pe.Node(interface=util.IdentityInterface(fields=['bids_dictionary']), name="infosource")
	infosource.iterables = [('bids_dictionary', bids_dictionary)]

	datafile_source = pe.Node(name='datafile_source', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['out_file']))
	datafile_source.inputs.bids_dictionary_override = {'modality':modality}
	datafile_source.inputs.df = data_selection

	eventfile_source = pe.Node(name='eventfile_source', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['out_file']))
	eventfile_source.inputs.bids_dictionary_override = {'modality':'events'}
	eventfile_source.inputs.df = data_selection

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = highpass_sigma
	specify_model.inputs.habituation_regressor = bool(habituation)

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	if bf_path:
		bf_path = path.abspath(path.expanduser(bf_path))
		level1design.inputs.bases = {"custom": {"bfcustompath":bf_path}}
	# level1design.inputs.bases = {'gamma': {'derivs':False, 'gammasigma':10, 'gammadelay':5}}
	level1design.inputs.orthogonalization = {1: {0:0,1:0,2:0}, 2: {0:1,1:1,2:0}}
	level1design.inputs.model_serial_correlations = True
	if habituation=="separate_contrast":
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1]),('allStim','T', ["e1"],[1])] #condition names as defined in specify_model
	elif habituation=="in_main_contrast":
		level1design.inputs.contrasts = [('allStim','T', ["e0", "e1"],[1,1])] #condition names as defined in specify_model
	elif habituation=="confound" or not habituation:
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1])] #condition names as defined in specify_model
	else:
		raise ValueError('The value you have provided for the `habituation` parameter, namely "{}", is invalid. Please choose one of: {"confound","in_main_contrast","separate_contrast"}'.format(habituation))

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')
	modelgen.inputs.ignore_exception = True

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')
	glm.inputs.out_cope = "cope.nii.gz"
	glm.inputs.out_varcb_name = "varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	glm.inputs.out_file = "betas.nii.gz"
	glm.inputs.out_t_name = "t_stat.nii.gz"
	glm.inputs.out_p_name = "p_stat.nii.gz"
	if mask:
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	glm.interface.mem_gb = 6
	glm.inputs.ignore_exception = True

	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_cope.nii.gz"
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_varcb.nii.gz"
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_tstat.nii.gz"
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_zstat.nii.gz"
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_pstat.nii.gz"
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_pfstat.nii.gz"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(out_dir,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, datafile_source, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, eventfile_source, [('bids_dictionary', 'bids_dictionary')]),
		(eventfile_source, specify_model, [('out_file', 'event_files')]),
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		(modelgen, glm, [('con_file', 'contrasts')]),
		(infosource, datasink, [(('bids_dictionary',bids_dict_to_dir), 'container')]),
		(infosource, cope_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, varcb_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, tstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, zstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, pstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, pfstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(cope_filename, glm, [('filename', 'out_cope')]),
		(varcb_filename, glm, [('filename', 'out_varcb_name')]),
		(tstat_filename, glm, [('filename', 'out_t_name')]),
		(zstat_filename, glm, [('filename', 'out_z_name')]),
		(pstat_filename, glm, [('filename', 'out_p_name')]),
		(pfstat_filename, glm, [('filename', 'out_pf_name')]),
		(glm, datasink, [('out_pf', '@pfstat')]),
		(glm, datasink, [('out_p', '@pstat')]),
		(glm, datasink, [('out_z', '@zstat')]),
		(glm, datasink, [('out_t', '@tstat')]),
		(glm, datasink, [('out_cope', '@cope')]),
		(glm, datasink, [('out_varcb', '@varcb')]),
		]

	if highpass_sigma or lowpass_sigma:
		bandpass = pe.Node(interface=fsl.maths.TemporalFilter(), name="bandpass")
		bandpass.inputs.highpass_sigma = highpass_sigma
		bandpass.interface.mem_gb = 6
		if lowpass_sigma:
			bandpass.inputs.lowpass_sigma = lowpass_sigma
		else:
			bandpass.inputs.lowpass_sigma = tr
		workflow_connections.extend([
			(datafile_source, bandpass, [('out_file', 'in_file')]),
			(bandpass, specify_model, [('out_file', 'functional_runs')]),
			(bandpass, glm, [('out_file', 'in_file')]),
			])
	else:
		workflow_connections.extend([
			(datafile_source, specify_model, [('out_file', 'functional_runs')]),
			(datafile_source, glm, [('out_file', 'in_file')]),
			])


	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_dir
	workflow.config = {"execution": {"crashdump_dir": path.join(out_dir,"crashdump")}}
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})
	if not keep_work:
		shutil.rmtree(path.join(out_dir,workdir_name))

def seed_fc(preprocessing_dir,
	exclude={},
	habituation='confound',
	highpass_sigma=225,
	lowpass_sigma=False,
	include={},
	keep_work=False,
	out_dir="",
	mask="",
	match_regex='sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/func/.*?_task-(?P<task>[a-zA-Z0-9]+)_acq-(?P<acq>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)\.(?:tsv|nii|nii\.gz)',
	nprocs=N_PROCS,
	tr=1,
	workflow_name="generic",
	modality="cbv",
	):
	"""Calculate subject level seed-based functional connectivity via the `fsl_glm` command.

	Parameters
	----------

	exclude : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified matching entries will be excluded in the analysis.
	habituation : {"", "confound", "separate_contrast", "in_main_contrast"}, optional
		How the habituation regressor should be handled.
		Anything which evaluates as False (though we recommend "") means no habituation regressor will be introduced.
	highpass_sigma : int, optional
		Highpass threshold (in seconds).
	include : dict
		A dictionary with any combination of "sessions", "subjects", "tasks" as keys and corresponding identifiers as values.
		If this is specified only matching entries will be included in the analysis.
	keep_work : bool, optional
		Whether to keep the work directory (containing all the intermediary workflow steps, as managed by nipypye).
		This is useful for debugging and quality control.
	out_dir : str, optional
		Path to the directory inside which both the working directory and the output directory will be created.
	mask : str, optional
		Path to the brain mask which shall be used to define the brain volume in the analysis.
		This has to point to an existing NIfTI file containing zero and one values only.
	match_regex : str, optional
		Regex matching pattern by which to select input files. Has to contain groups named "sub", "ses", "acq", "task", and "mod".
	n_procs : int, optional
		Maximum number of processes which to simultaneously spawn for the workflow.
		If not explicitly defined, this is automatically calculated from the number of available cores and under the assumption that the workflow will be the main process running for the duration that it is running.
	tr : int, optional
		Repetition time, in seconds.
	workflow_name : str, optional
		Name of the workflow; this will also be the name of the final output directory produced under `out_dir`.
	"""

	preprocessing_dir = path.abspath(path.expanduser(preprocessing_dir))
	if not out_dir:
		out_dir = path.join(bids_base,'l1')
	else:
		out_dir = path.abspath(path.expanduser(out_dir))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = preprocessing_dir
	datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()
	out_paths = [path.abspath(path.expanduser(i)) for i in datafind_res.outputs.out_paths]
	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.task, datafind_res.outputs.mod, out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','task','modality','path'))
	if exclude:
		for key in exclude:
			data_selection = data_selection[~data_selection[key].isin(exclude[key])]
	if include:
		for key in include:
			data_selection = data_selection[data_selection[key].isin(include[key])]
	bids_dictionary = data_selection[data_selection['modality']==modality].drop_duplicates().T.to_dict().values()

	infosource = pe.Node(interface=util.IdentityInterface(fields=['bids_dictionary']), name="infosource")
	infosource.iterables = [('bids_dictionary', bids_dictionary)]

	datafile_source = pe.Node(name='datafile_source', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['out_file']))
	datafile_source.inputs.bids_dictionary_override = {'modality':modality}
	datafile_source.inputs.df = data_selection

	seed_timecourse = pe.Node(name='seed_timecourse', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['out_file']))

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = highpass_sigma
	specify_model.inputs.habituation_regressor = bool(habituation)

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	if bf_path:
		bf_path = path.abspath(path.expanduser(bf_path))
		level1design.inputs.bases = {"custom": {"bfcustompath":bf_path}}
	# level1design.inputs.bases = {'gamma': {'derivs':False, 'gammasigma':10, 'gammadelay':5}}
	level1design.inputs.orthogonalization = {1: {0:0,1:0,2:0}, 2: {0:1,1:1,2:0}}
	level1design.inputs.model_serial_correlations = True
	if habituation=="separate_contrast":
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1]),('allStim','T', ["e1"],[1])] #condition names as defined in specify_model
	elif habituation=="in_main_contrast":
		level1design.inputs.contrasts = [('allStim','T', ["e0", "e1"],[1,1])] #condition names as defined in specify_model
	elif habituation=="confound" or not habituation:
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1])] #condition names as defined in specify_model
	else:
		raise ValueError('The value you have provided for the `habituation` parameter, namely "{}", is invalid. Please choose one of: {"confound","in_main_contrast","separate_contrast"}'.format(habituation))

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')
	modelgen.inputs.ignore_exception = True

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')
	glm.inputs.out_cope = "cope.nii.gz"
	glm.inputs.out_varcb_name = "varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	glm.inputs.out_file = "betas.nii.gz"
	glm.inputs.out_t_name = "t_stat.nii.gz"
	glm.inputs.out_p_name = "p_stat.nii.gz"
	if mask:
		glm.inputs.mask = path.abspath(path.expanduser(mask))
	glm.inputs.ignore_exception = True

	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_cope.nii.gz"
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_varcb.nii.gz"
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_tstat.nii.gz"
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_zstat.nii.gz"
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_pstat.nii.gz"
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_{modality}_pfstat.nii.gz"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(out_dir,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, datafile_source, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, eventfile_source, [('bids_dictionary', 'bids_dictionary')]),
		(eventfile_source, specify_model, [('out_file', 'event_files')]),
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		(modelgen, glm, [('con_file', 'contrasts')]),
		(infosource, datasink, [(('bids_dictionary',bids_dict_to_dir), 'container')]),
		(infosource, cope_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, varcb_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, tstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, zstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, pstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, pfstat_filename, [('bids_dictionary', 'bids_dictionary')]),
		(cope_filename, glm, [('filename', 'out_cope')]),
		(varcb_filename, glm, [('filename', 'out_varcb_name')]),
		(tstat_filename, glm, [('filename', 'out_t_name')]),
		(zstat_filename, glm, [('filename', 'out_z_name')]),
		(pstat_filename, glm, [('filename', 'out_p_name')]),
		(pfstat_filename, glm, [('filename', 'out_pf_name')]),
		(glm, datasink, [('out_pf', '@pfstat')]),
		(glm, datasink, [('out_p', '@pstat')]),
		(glm, datasink, [('out_z', '@zstat')]),
		(glm, datasink, [('out_t', '@tstat')]),
		(glm, datasink, [('out_cope', '@cope')]),
		(glm, datasink, [('out_varcb', '@varcb')]),
		]

	if highpass_sigma or lowpass_sigma:
		bandpass = pe.Node(interface=fsl.maths.TemporalFilter(), name="bandpass")
		bandpass.inputs.highpass_sigma = highpass_sigma
		if lowpass_sigma:
			bandpass.inputs.lowpass_sigma = lowpass_sigma
		else:
			bandpass.inputs.lowpass_sigma = tr
		workflow_connections.extend([
			(datafile_source, bandpass, [('out_file', 'in_file')]),
			(bandpass, specify_model, [('out_file', 'functional_runs')]),
			(bandpass, glm, [('out_file', 'in_file')]),
			])
	else:
		workflow_connections.extend([
			(datafile_source, specify_model, [('out_file', 'functional_runs')]),
			(datafile_source, glm, [('out_file', 'in_file')]),
			])


	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = out_dir
	workflow.config = {"execution": {"crashdump_dir": path.join(out_dir,"crashdump")}}
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})
	if not keep_work:
		shutil.rmtree(path.join(out_dir,workdir_name))

def getlen(a):
	return len(a)
def add_suffix(name, suffix):
	"""A function that adds suffix to a variable.

	Returns converted to string-type  input variable 'name', and string-type converted variable
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
	groupby="session",
	keep_work=False,
	l2_dir="",
	loud=False,
	tr=1,
	nprocs=6,
	workflow_name="generic",
	mask="~/ni_data/templates/ds_QBI_chr_bin.nii.gz",
	subjects=[],
	sessions=[],
	tasks=[],
	exclude={},
	include={},
	):

	l1_dir = path.expanduser(l1_dir)
	if not l2_dir:
		l2_dir = path.abspath(path.join(l1_dir,"..","..","l2"))

	mask=path.abspath(path.expanduser(mask))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = l1_dir
	datafind.inputs.match_regex = '.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_task-(?P<task>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)_(?P<stat>[a-zA-Z0-9]+)\.(?:tsv|nii|nii\.gz)'
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

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")

	level2model = pe.Node(interface=fsl.L2Model(),name='level2model')

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file = mask
	flameo.inputs.run_mode = "ols"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(l2_dir,workflow_name)
	datasink.inputs.substitutions = [('_iterable_', ''),]

	if groupby == "subject":
		subjects = data_selection[['subject']].drop_duplicates().values.tolist()

		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', subjects)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["group",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[['group','group']],
			varcbs=[['group','group']]
			)
		datasource.inputs.field_template = dict(
			copes="sub-%s/ses-*/sub-%s_ses-*_task-*_cope.nii.gz",
			varcbs="sub-%s/ses-*/sub-%s_ses-*_task-*_varcb.nii.gz",
			)
		workflow_connections = [
			(infosource, datasource, [('iterable', 'group')]),
			(infosource, copemerge, [(('iterable',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
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
		sessions = data_selection[['session']].drop_duplicates()
		sessions = sessions.T.to_dict().values()

		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', sessions)]

		copes = pe.Node(name='copes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		copes.inputs.bids_dictionary_override = {'statistic':'cope'}
		copes.inputs.df = data_selection
		copes.inputs.list_output = True

		varcopes = pe.Node(name='varcopes', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['selection']))
		varcopes.inputs.bids_dictionary_override = {'statistic':'varcb'}
		varcopes.inputs.df = data_selection
		varcopes.inputs.list_output = True

		workflow_connections = [
			(infosource, copemerge, [(('iterable',dict_and_suffix,"session","_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',dict_and_suffix,"session","_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "task":
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

	workflow_connections.extend([
		(copes, copemerge, [('selection', 'in_files')]),
		(varcopes, varcopemerge, [('selection', 'in_files')]),
		(varcopes, level2model, [(('selection',mylen), 'num_copes')]),
		(copemerge,flameo,[('merged_file','cope_file')]),
		(varcopemerge,flameo,[('merged_file','var_cope_file')]),
		(level2model,flameo, [('design_mat','design_file')]),
		(level2model,flameo, [('design_grp','cov_split_file')]),
		(level2model,flameo, [('design_con','t_con_file')]),
		(flameo, datasink, [('copes', '@copes')]),
		(flameo, datasink, [('fstats', '@fstats')]),
		(flameo, datasink, [('tstats', '@tstats')]),
		(flameo, datasink, [('zstats', '@zstats')]),
		])

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.config = {"execution": {"crashdump_dir": path.join(l2_dir,"crashdump")}}
	workflow.base_dir = l2_dir
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")


	if not loud:
		try:
			workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})
		except RuntimeError:
			print("WARNING: Some expected tasks have not been found (or another RuntimeError has occured).")
		for f in listdir(getcwd()):
			if re.search("crash.*?-varcopemerge|-copemerge.*", f):
				remove(path.join(getcwd(), f))
	else:
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})


	if not keep_work:
		shutil.rmtree(path.join(l2_dir,workdir_name))

def mylen(foo):
	return len(foo)

def dict_and_suffix(my_dictionary,key,suffix):
	filename = my_dictionary[key]
	filename = str(filename)+suffix
	return filename

def l2_anova(l1_dir,
	keep_work=False,
	l2_dir="",
	loud=False,
	tr=1,
	nprocs=6,
	workflow_name="generic",
	mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
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

	copes = data_selection[data_selection['statistic']=='cope']['path'].tolist()
	varcopes = data_selection[data_selection['statistic']=='varcb']['path'].tolist()

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	copemerge.inputs.in_files = copes
	copemerge.inputs.merged_file = 'copes.nii.gz'

	varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")
	varcopemerge.inputs.in_files = varcopes
	varcopemerge.inputs.merged_file = 'varcopes.nii.gz'

	copeonly = data_selection[data_selection['statistic']=='cope']
	regressors = {}
	for sub in copeonly['subject'].unique():
		#print(sub)
		regressor = [copeonly['subject'] == sub][0]
		regressor = [int(i) for i in regressor]
		key = "sub-"+str(sub)
		regressors[key] = regressor
	reference = str(copeonly['session'].unique()[0])
	for ses in copeonly['session'].unique()[1:]:
		#print(ses)
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
	#print(regressors)
	#print(contrasts)
	#return

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
	workflow.config = {"execution": {"crashdump_dir": path.join(l2_dir,"crashdump")}}
	workflow.base_dir = l2_dir
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	if not loud:
		try:
			workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})
		except RuntimeError:
			print("WARNING: Some expected tasks have not been found (or another RuntimeError has occured).")
		for f in listdir(getcwd()):
			if re.search("crash.*?-varcopemerge|-copemerge.*", f):
				remove(path.join(getcwd(), f))
	else:
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})


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
