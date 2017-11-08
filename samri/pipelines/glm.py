from os import path, listdir, getcwd, remove
from samri.pipelines.extra_functions import get_level2_inputs, get_subjectinfo, write_function_call, bids_inputs

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

from samri.pipelines.extra_interfaces import SpecifyModel
from samri.pipelines.extra_functions import select_from_datafind_df
from samri.pipelines.utils import bids_dict_to_source, ss_to_path, iterfield_selector, datasource_exclude, bids_dict_to_dir


def l1(preprocessing_dir,
	highpass_sigma=225,
	include={},
	exclude={},
	keep_work=False,
	l1_dir="",
	nprocs=10,
	mask="~/ni_data/templates/ds_QBI_chr_bin.nii.gz",
	per_stimulus_contrast=False,
	habituation="",
	tr=1,
	workflow_name="generic",
	bf_path = '~/ni_data/irfs/chr_beta1.txt',
	):
	"""Calculate subject level GLM statistics.

	Parameters
	----------

	include : dict
	A dictionary with any combination of "sessions", "subjects", "trials" as keys and corresponding identifiers as values.
	If this is specified ony matching entries will be included in the analysis.

	exclude : dict
	A dictionary with any combination of "sessions", "subjects", "trials" as keys and corresponding identifiers as values.
	If this is specified ony non-matching entries will be included in the analysis.

	habituation : string
	One value of "confound", "in_main_contrast", "separate_contrast", "" indicating how the habituation regressor should be handled.
	"" or any other value which evaluates to False will mean no habituation regressor is used int he model
	"""

	preprocessing_dir = path.expanduser(preprocessing_dir)
	if not l1_dir:
		l1_dir = path.abspath(path.join(preprocessing_dir,"..","..","l1"))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = preprocessing_dir
	datafind.inputs.match_regex = '.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/func/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_trial-(?P<trial>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)\.(?:tsv|nii|nii\.gz)'
	datafind_res = datafind.run()
	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.trial, datafind_res.outputs.mod, datafind_res.outputs.out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','trial','modality','path'))

	bids_dictionary = data_selection[data_selection['modality']=='cbv'].drop_duplicates().T.to_dict().values()

	infosource = pe.Node(interface=util.IdentityInterface(fields=['bids_dictionary']), name="infosource")
	infosource.iterables = [('bids_dictionary', bids_dictionary)]

	datafile_source = pe.Node(name='datafile_source', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['out_file']))
	datafile_source.inputs.bids_dictionary_override = {'modality':'cbv'}
	datafile_source.inputs.df = data_selection

	eventfile_source = pe.Node(name='eventfile_source', interface=util.Function(function=select_from_datafind_df, input_names=inspect.getargspec(select_from_datafind_df)[0], output_names=['out_file']))
	eventfile_source.inputs.bids_dictionary_override = {'modality':'events'}
	eventfile_source.inputs.df = data_selection

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = highpass_sigma
	specify_model.inputs.one_condition_file = not per_stimulus_contrast
	specify_model.inputs.habituation_regressor = bool(habituation)

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	if bf_path:
		bf_path = path.abspath(path.expanduser(bf_path))
		level1design.inputs.bases = {"custom": {"bfcustompath":bf_path}}
	# level1design.inputs.bases = {'gamma': {'derivs':False, 'gammasigma':10, 'gammadelay':5}}
	level1design.inputs.orthogonalization = {1: {0:0,1:0,2:0}, 2: {0:1,1:1,2:0}}
	level1design.inputs.model_serial_correlations = True
	if per_stimulus_contrast:
		level1design.inputs.contrasts = [('allStim','T', ["e0","e1","e2","e3","e4","e5"],[1,1,1,1,1,1])] #condition names as defined in specify_model
	elif habituation=="separate_contrast":
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1]),('allStim','T', ["e1"],[1])] #condition names as defined in specify_model
	elif habituation=="in_main_contrast":
		level1design.inputs.contrasts = [('allStim','T', ["e0", "e1"],[1,1])] #condition names as defined in specify_model
	elif habituation=="confound":
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1])] #condition names as defined in specify_model
	else:
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1])] #condition names as defined in specify_model

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')
	glm.inputs.out_cope = "cope.nii.gz"
	glm.inputs.out_varcb_name = "varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	glm.inputs.out_file = "betas.nii.gz"
	glm.inputs.out_t_name = "t_stat.nii.gz"
	glm.inputs.out_p_name = "p_stat.nii.gz"
	if mask:
		glm.inputs.mask = path.abspath(path.expanduser(mask))

	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = "sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_{modality}_cope.nii.gz"
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = "sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_{modality}_varcb.nii.gz"
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_{modality}_tstat.nii.gz"
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_{modality}_zstat.nii.gz"
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_{modality}_pstat.nii.gz"
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=bids_dict_to_source,input_names=inspect.getargspec(bids_dict_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = "sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_{modality}_pfstat.nii.gz"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(l1_dir,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, datafile_source, [('bids_dictionary', 'bids_dictionary')]),
		(infosource, eventfile_source, [('bids_dictionary', 'bids_dictionary')]),
		(eventfile_source, specify_model, [('out_file', 'event_files')]),
		(datafile_source, specify_model, [('out_file', 'functional_runs')]),
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(datafile_source, glm, [('out_file', 'in_file')]),
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

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = l1_dir
	workflow.config = {"execution": {"crashdump_dir": path.join(l1_dir,"crashdump")}}
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})
	if not keep_work:
		shutil.rmtree(path.join(l1_dir,workdir_name))

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
	exclude={},
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
	trials=[],
	):

	l1_dir = path.expanduser(l1_dir)
	if not l2_dir:
		l2_dir = path.abspath(path.join(l1_dir,"..","..","l2"))

	mask=path.abspath(path.expanduser(mask))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = l1_dir
	datafind.inputs.match_regex = '.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_trial-(?P<trial>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)_(?P<stat>[a-zA-Z0-9]+)\.(?:tsv|nii|nii\.gz)'
	datafind_res = datafind.run()
	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.trial, datafind_res.outputs.mod, datafind_res.outputs.out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','trial','modality','path'))

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
			copes="sub-%s/ses-*/sub-%s_ses-*_trial-*_cope.nii.gz",
			varcbs="sub-%s/ses-*/sub-%s_ses-*_trial-*_varcb.nii.gz",
			)
		workflow_connections = [
			(infosource, datasource, [('iterable', 'group')]),
			(infosource, copemerge, [(('iterable',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "subject_trial":
		#does not currently work, due to missing iterator combinations (same issue as preprocessing)
		merge = pe.Node(interface=util.Merge(2), name="merge")
		infosource = pe.Node(interface=util.IdentityInterface(fields=['subject','trial']), name="infosource")
		infosource.iterables = [('subject', subjects),('trial', trials)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["subject","trial",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[["subject","subject","trial",]],
			varcbs=[["subject","subject","trial",]]
			)
		datasource.inputs.field_template = dict(
			copes="sub-%s/ses-*/sub-%s_ses-*_trial-%s_cope.nii.gz",
			varcbs="sub-%s/ses-*/sub-%s_ses-*_trial-%s_varcb.nii.gz",
			)
		workflow_connections = [
			(infosource, datasource, [('subject', 'subject'),('trial','trial')]),
			(infosource, merge, [('subject', 'in1'),('trial','in2')]),
			(merge, copemerge, [(('out',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(merge, varcopemerge, [(('out',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "session":
		sessions = data_selection[['sessions']].drop_duplicates().values.tolist()

		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', sessions)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["group",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[['group','group']],
			varcbs=[['group','group']]
			)
		datasource.inputs.field_template = dict(
			copes="sub-*/ses-%s/sub-*_ses-%s_trial-*_cope.nii.gz",
			varcbs="sub-*/ses-%s/sub-*_ses-%s_trial-*_varcb.nii.gz",
			)
		workflow_connections = [
			(infosource, datasource, [('iterable', 'group')]),
			(infosource, copemerge, [(('iterable',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "trial":
		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', trials)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["group",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[['group']],
			varcbs=[['group']]
			)
		datasource.inputs.field_template = dict(
			copes="sub-*/ses-*/sub-*_ses-*_trial-%s_cope.nii.gz ",
			varcbs="sub-*/ses-*/sub-*_ses-*_trial-%s_varcb.nii.gz ",
			)
		workflow_connections = [
			(infosource, datasource, [('iterable', 'group')]),
			(infosource, copemerge, [(('iterable',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(infosource, varcopemerge, [(('iterable',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]
	datasource.inputs.base_directory = l1_dir
	datasource.inputs.sort_filelist = True
	datasource.inputs.template = "*"

	workflow_connections.extend([
		(datasource, copemerge, [(('copes',datasource_exclude,exclude), 'in_files')]),
		(datasource, varcopemerge, [(('varcbs',datasource_exclude,exclude), 'in_files')]),
		(datasource, level2model, [(('copes',datasource_exclude,exclude,"len"), 'num_copes')]),
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
			print("WARNING: Some expected trials have not been found (or another RuntimeError has occured).")
		for f in listdir(getcwd()):
			if re.search("crash.*?-varcopemerge|-copemerge.*", f):
				remove(path.join(getcwd(), f))
	else:
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})


	if not keep_work:
		shutil.rmtree(path.join(l2_dir,workdir_name))

def l2_anova(l1_dir,
	keep_work=False,
	l2_dir="",
	loud=False,
	tr=1,
	nprocs=6,
	workflow_name="generic",
	mask="~/ni_data/templates/ds_QBI_chr_bin.nii.gz",
	exclude={},
	include={},
	):

	l1_dir = path.expanduser(l1_dir)
	if not l2_dir:
		l2_dir = path.abspath(path.join(l1_dir,"..","..","l2"))

	mask=path.abspath(path.expanduser(mask))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = l1_dir
	datafind.inputs.match_regex = '.+/sub-(?P<sub>[a-zA-Z0-9]+)/ses-(?P<ses>[a-zA-Z0-9]+)/.*?_acq-(?P<acq>[a-zA-Z0-9]+)_trial-(?P<trial>[a-zA-Z0-9]+)_(?P<mod>[a-zA-Z0-9]+)_(?P<stat>(cope|varcb)+)\.(?:tsv|nii|nii\.gz)'
	datafind_res = datafind.run()

	data_selection = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.acq, datafind_res.outputs.trial, datafind_res.outputs.mod, datafind_res.outputs.stat, datafind_res.outputs.out_paths])
	data_selection = [list(i) for i in data_selection]
	data_selection = pd.DataFrame(data_selection,columns=('subject','session','acquisition','trial','modality','statistic','path'))

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
	varcopemerge.inputs.in_files = copes
	varcopemerge.inputs.merged_file = 'varcopes.nii.gz'

	copeonly = data_selection[data_selection['statistic']=='cope']
	regressors = {}
	for sub in copeonly['subject'].unique():
		regressor = [copeonly['subject'] == sub][0]
		regressor = [int(i) for i in regressor]
		key = "sub-"+str(sub)
		regressors[key] = regressor
	for ses in copeonly['session'].unique()[1:]:
		regressor = [copeonly['session'] == ses][0]
		regressor = [int(i) for i in regressor]
		key = "ses-"+str(ses)
		regressors[key] = regressor

	sessions = [[i,'T',[i], [1]] for i in regressors.keys() if "ses-" in i]
	contrasts = deepcopy(sessions)
	contrasts.append(['anova', 'F', sessions])

	level2model = pe.Node(interface=fsl.MultipleRegressDesign(),name='level2model')
	level2model.inputs.regressors = regressors
	level2model.inputs.contrasts = contrasts

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file = mask
	flameo.inputs.run_mode = "ols"
	#flameo.inputs.run_mode = "fe"

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
			print("WARNING: Some expected trials have not been found (or another RuntimeError has occured).")
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
