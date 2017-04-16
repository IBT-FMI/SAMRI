from os import path, listdir, getcwd, remove
from samri.pipelines.extra_functions import get_level2_inputs, get_subjectinfo, write_function_call, bids_inputs

import inspect
import re
import shutil
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
from itertools import product
from nipype.interfaces import fsl
from nipype.interfaces.fsl.model import Level1Design

from extra_interfaces import SpecifyModel
from preprocessing import bruker
from utils import sss_to_source, ss_to_path, iterfield_selector, datasource_exclude

def l1(preprocessing_dir,
	highpass_sigma=290,
	include={},
	exclude={},
	keep_work=False,
	l1_dir="",
	nprocs=10,
	mask="/home/chymera/ni_data/templates/ds_QBI_chr_bin.nii.gz",
	per_stimulus_contrast=False,
	habituation="",
	tr=1,
	workflow_name="generic",
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
	datafind.inputs.match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/func/.*?_trial-(?P<scan>.+)\.nii.gz'
	datafind_res = datafind.run()
	iterfields = zip(*[datafind_res.outputs.sub, datafind_res.outputs.ses, datafind_res.outputs.scan])

	if include:
		iterfields = iterfield_selector(iterfields, include, "include")
	if exclude:
		iterfields = iterfield_selector(iterfields, exclude, "exclude")

	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_session_scan']), name="infosource")
	infosource.iterables = [('subject_session_scan', iterfields)]

	datafile_source = pe.Node(name='datafile_source', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['out_file']))
	datafile_source.inputs.base_directory = preprocessing_dir
	datafile_source.inputs.source_format = "sub-{0}/ses-{1}/func/sub-{0}_ses-{1}_trial-{2}.nii.gz"

	eventfile_source = pe.Node(name='eventfile_source', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['out_file']))
	eventfile_source.inputs.base_directory = preprocessing_dir
	eventfile_source.inputs.source_format = "sub-{0}/ses-{1}/func/sub-{0}_ses-{1}_trial-{2}_events.tsv"

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = highpass_sigma
	specify_model.inputs.one_condition_file = not per_stimulus_contrast
	specify_model.inputs.habituation_regressor = bool(habituation)

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {"custom": {"bfcustompath":"/mnt/data/ni_data/irfs/chr_beta1.txt"}}
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
		glm.inputs.mask = mask

	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_cope.nii.gz"
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_varcb.nii.gz"
	tstat_filename = pe.Node(name='tstat_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	tstat_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_tstat.nii.gz"
	zstat_filename = pe.Node(name='zstat_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	zstat_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_zstat.nii.gz"
	pstat_filename = pe.Node(name='pstat_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	pstat_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_pstat.nii.gz"
	pfstat_filename = pe.Node(name='pfstat_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	pfstat_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_pfstat.nii.gz"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(l1_dir,workflow_name)
	datasink.inputs.parameterization = False

	workflow_connections = [
		(infosource, datafile_source, [('subject_session_scan', 'subject_session_scan')]),
		(infosource, eventfile_source, [('subject_session_scan', 'subject_session_scan')]),
		(eventfile_source, specify_model, [('out_file', 'event_files')]),
		(datafile_source, specify_model, [('out_file', 'functional_runs')]),
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(datafile_source, glm, [('out_file', 'in_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		(modelgen, glm, [('con_file', 'contrasts')]),
		(infosource, datasink, [(('subject_session_scan',ss_to_path), 'container')]),
		(infosource, cope_filename, [('subject_session_scan', 'subject_session_scan')]),
		(infosource, varcb_filename, [('subject_session_scan', 'subject_session_scan')]),
		(infosource, tstat_filename, [('subject_session_scan', 'subject_session_scan')]),
		(infosource, zstat_filename, [('subject_session_scan', 'subject_session_scan')]),
		(infosource, pstat_filename, [('subject_session_scan', 'subject_session_scan')]),
		(infosource, pfstat_filename, [('subject_session_scan', 'subject_session_scan')]),
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
	):

	l1_dir = path.expanduser(l1_dir)
	if not l2_dir:
		l2_dir = path.abspath(path.join(l1_dir,"..","..","l2"))

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = l1_dir
	datafind.inputs.match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_trial-(?P<scan>.+)_cope\.nii.gz'
	datafind_res = datafind.run()
	subjects = set(datafind_res.outputs.sub)
	sessions = set(datafind_res.outputs.ses)
	scans = set(datafind_res.outputs.scan)

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")

	level2model = pe.Node(interface=fsl.L2Model(),name='level2model')

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file="/home/chymera/ni_data/templates/ds_QBI_chr_bin.nii.gz"
	flameo.inputs.run_mode="ols"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(l2_dir,workflow_name)
	datasink.inputs.substitutions = [('_iterable_', ''),]

	if groupby == "subject":
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
	elif groupby == "subject_scan":
		#does not currently work, due to missing iterator combinations (same issue as preprocessing)
		merge = pe.Node(interface=util.Merge(2), name="merge")
		infosource = pe.Node(interface=util.IdentityInterface(fields=['subject','scan']), name="infosource")
		infosource.iterables = [('subject', subjects),('scan', scans)]
		datasource = pe.Node(interface=nio.DataGrabber(infields=["subject","scan",], outfields=["copes", "varcbs"]), name="datasource")
		datasource.inputs.template_args = dict(
			copes=[["subject","subject","scan",]],
			varcbs=[["subject","subject","scan",]]
			)
		datasource.inputs.field_template = dict(
			copes="sub-%s/ses-*/sub-%s_ses-*_trial-%s_cope.nii.gz",
			varcbs="sub-%s/ses-*/sub-%s_ses-*_trial-%s_varcb.nii.gz",
			)
		workflow_connections = [
			(infosource, datasource, [('subject', 'subject'),('scan','scan')]),
			(infosource, merge, [('subject', 'in1'),('scan','in2')]),
			(merge, copemerge, [(('out',add_suffix,"_cope.nii.gz"), 'merged_file')]),
			(merge, varcopemerge, [(('out',add_suffix,"_varcb.nii.gz"), 'merged_file')]),
			]
	elif groupby == "session":
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
	elif groupby == "scan":
		infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")
		infosource.iterables = [('iterable', scans)]
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
			print("WARNING: Some expected scans have not been found (or another RuntimeError has occured).")
		for f in listdir(getcwd()):
			if re.search("crash.*?-varcopemerge|-copemerge.*", f):
				remove(path.join(getcwd(), f))
	else:
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})


	if not keep_work:
		shutil.rmtree(path.join(l2_dir,workdir_name))
