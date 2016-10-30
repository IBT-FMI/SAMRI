from os import path, listdir, getcwd, remove
if not __package__:
	import sys
	pkg_root = path.abspath(path.join(path.dirname(path.realpath(__file__)),"../../.."))
	sys.path.insert(0, pkg_root)
from samri.pipelines.extra_functions import get_level2_inputs, get_subjectinfo, write_function_call, bids_inputs

import inspect
import re
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
from itertools import product
from nipype.interfaces import fsl

from extra_interfaces import GenL2Model, SpecifyModel, Level1Design
from preprocessing import bruker
from utils import sss_to_source, ss_to_path, iterfield_selector

def l1(preprocessing_dir,
	highpass_sigma=290,
	include={},
	exclude={},
	l1_dir="",
	nprocs=10,
	mask="/home/chymera/NIdata/templates/ds_QBI_chr_bin.nii.gz",
	per_event_contrasts=False,
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

	print(iterfields)
	return

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
	specify_model.inputs.one_condition_file = True
	specify_model.inputs.habituation_regressor = True

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'gamma': {'derivs':False, 'gammasigma':10, 'gammadelay':5}}
	level1design.inputs.orthogonalization = {1: {0:0,1:0,2:0}, 2: {0:1,1:1,2:0}}
	level1design.inputs.model_serial_correlations = True
	if per_event_contrasts:
		level1design.inputs.contrasts = [('allStim','T', ["e0","e1","e2","e3","e4","e5"],[1,1,1,1,1,1])] #condition names as defined in specify_model
	else:
		level1design.inputs.contrasts = [('allStim','T', ["e0"],[1])] #condition names as defined in specify_model

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')

	glm = pe.Node(interface=fsl.GLM(), name='glm', iterfield='design')
	glm.inputs.out_cope="cope.nii.gz"
	glm.inputs.out_varcb_name="varcb.nii.gz"
	glm.inputs.mask=mask
	#not setting a betas output file might lead to beta export in lieu of COPEs
	glm.inputs.out_file="betas.nii.gz"
	glm.inputs.out_t_name="t_stat.nii.gz"
	glm.inputs.out_p_name="p_stat.nii.gz"

	cope_filename = pe.Node(name='cope_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	cope_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_cope.nii.gz"
	varcb_filename = pe.Node(name='varcb_filename', interface=util.Function(function=sss_to_source,input_names=inspect.getargspec(sss_to_source)[0], output_names=['filename']))
	varcb_filename.inputs.source_format = "sub-{0}_ses-{1}_trial-{2}_varcb.nii.gz"

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
		(cope_filename, glm, [('filename', 'out_cope')]),
		(varcb_filename, glm, [('filename', 'out_varcb_name')]),
		(glm, datasink, [('out_cope', '@cope')]),
		(glm, datasink, [('out_varcb', '@varcb')]),
		]

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = l1_dir
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})

def level1(measurements_base, functional_scan_types, structural_scan_types=[], tr=1, conditions=[], subjects=[], exclude_subjects=[], measurements=[], exclude_measurements=[], actual_size=False, pipeline_denominator="level1", template="/home/chymera/NIdata/templates/ds_QBI_chr.nii.gz", standalone_execute=True, compare_experiment_types=[], quiet=True, blur_xy=False):
	"""First-level analysis pipeiline which calls the bru_preproc workflow for preprocessing

	Mandatory Arguments:
	measurements_base -- path in which to look for data to be processed
	functional_scan_types -- a list of identifiers for the functional scan types to be selected OR a dictionary with keys whch are identifiers for the functional scan types to be selected and values which are corresponding codes of the stimulation protocols (as seen in ~/syncdata/meta.db) in use on each functional scan type

	Keyword Arguments:
	"""

	if isinstance(functional_scan_types, dict):
		functional_scan_types_list = functional_scan_types.keys()
	else:
		functional_scan_types_list = functional_scan_types

	measurements_base = path.expanduser(measurements_base)
	preprocessing = bru_preproc(measurements_base, functional_scan_types_list, structural_scan_types=structural_scan_types, tr=tr, conditions=conditions, subjects=subjects, exclude_subjects=exclude_subjects, measurements=measurements, exclude_measurements=exclude_measurements, actual_size=actual_size, template=template, blur_xy=blur_xy)

	get_subject_info = pe.Node(name='get_subject_info', interface=util.Function(function=get_subjectinfo,input_names=["subject_delay","scan_type","scan_types"], output_names=['output']))
	get_subject_info.inputs.scan_types = functional_scan_types

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = 180

	level1design = pe.Node(interface=fsl.model.Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'dgamma': {'derivs':False}}
	level1design.inputs.model_serial_correlations = True
	level1design.inputs.contrasts = [('allStim','T', ["s1","s2","s3","s4","s5","s6"],[1,1,1,1,1,1])]

	modelgen = pe.Node(interface=fsl.FEATModel(), name='modelgen')

	func_glm = pe.Node(interface=fsl.GLM(), name='func_glm', iterfield='design')
	func_glm.inputs.out_cope="cope.nii.gz"
	func_glm.inputs.out_varcb_name="varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	func_glm.inputs.out_file="betas.nii.gz"
	func_glm.inputs.out_t_name="t_stat.nii.gz"
	func_glm.inputs.out_p_name="p_stat.nii.gz"

	struc_glm = pe.Node(interface=fsl.GLM(), name='struc_glm', iterfield='design')
	struc_glm.inputs.out_cope="cope.nii.gz"
	struc_glm.inputs.out_varcb_name="varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	struc_glm.inputs.out_file="betas.nii.gz"
	struc_glm.inputs.out_t_name="t_stat.nii.gz"
	struc_glm.inputs.out_p_name="p_stat.nii.gz"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(measurements_base,"GLM",pipeline_denominator,"results")
	#remove iterfield names
	datasink.inputs.substitutions = [('_condition_', ''),('_subject_', '.')]

	first_level = pe.Workflow(name="first_level")

	first_level.connect([
		(get_subject_info, specify_model, [('output', 'subject_info')]),
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, func_glm, [('design_file', 'design')]),
		(modelgen, func_glm, [('con_file', 'contrasts')]),
		(func_glm, datasink, [('out_cope', 'func_cope')]),
		(func_glm, datasink, [('out_varcb', 'func_varcb')]),
		])

	pipeline = pe.Workflow(name=pipeline_denominator)

	pipeline.connect([
		(preprocessing, first_level, [('timing_metadata.total_delay_s','get_subject_info.subject_delay')]),
		(preprocessing, first_level, [('get_functional_scan.scan_type','get_subject_info.scan_type')]),
		(preprocessing, first_level, [('functional_bandpass.out_file','specify_model.functional_runs')]),
		(preprocessing, first_level, [('functional_bandpass.out_file','func_glm.in_file')]),
		])

	pipeline.write_graph(dotfilename=path.join(measurements_base,"GLM",pipeline_denominator,"graph.dot"), graph2use="flat", format="png")
	if standalone_execute:
		pipeline.base_dir = path.join(measurements_base,"GLM")

		frame = inspect.currentframe()
		write_function_call(frame,path.join(measurements_base,"GLM",pipeline_denominator,"function_call.txt"))

		if quiet:
			try:
				pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
			except RuntimeError:
				print("WARNING: Some expected scans have not been found (or another RuntimeError has occured).")
			for f in listdir(getcwd()):
				if re.search("crash.*?get_structural_scan|get_functional_scan.*", f):
					remove(path.join(getcwd(), f))
		else:
			pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	else:
		return pipeline

if __name__ == "__main__":
	# level1("~/NIdata/ofM.dr/", {"7_EPI_CBV":"6_20_jb"}, structural_scan_types=-1, conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], exclude_measurements=["20151027_121613_4013_1_1"], pipeline_denominator="level1_dgamma_blurxy56n", blur_xy=5.6)

	# level1("~/NIdata/ofM.erc/", {"EPI_CBV_jin6":"jin6","EPI_CBV_jin10":"jin10","EPI_CBV_jin20":"jin20","EPI_CBV_jin40":"jin40","EPI_CBV_jin60":"jin60","EPI_CBV_alej":"alej",}, structural_scan_types=-1, actual_size=False, pipeline_denominator="level1_dgamma")
	# level2_common_effect("~/NIdata/ofM.erc/GLM/level1_dgamma", categories=[], scan_types=[["EPI_CBV_jin6"],["EPI_CBV_jin10"],["EPI_CBV_jin20"],["EPI_CBV_jin40"],["EPI_CBV_jin60"],["EPI_CBV_alej"]], participants=["5502","5503"], denominator="level2_dgamma")
	# for i in range(4,8):
	# 	level1("~/NIdata/ofM.erc/", {"EPI_CBV_jin6":"jin6","EPI_CBV_jin10":"jin10","EPI_CBV_jin20":"jin20","EPI_CBV_jin40":"jin40","EPI_CBV_jin60":"jin60","EPI_CBV_alej":"alej",}, structural_scan_types=-1, actual_size=False, pipeline_denominator="level1_dgamma_blurxy"+str(i), blur_xy=i)
	# 	level2_common_effect("~/NIdata/ofM.erc/GLM/level1_dgamma_blurxy"+str(i), categories=[], scan_types=[["EPI_CBV_jin6"],["EPI_CBV_jin10"],["EPI_CBV_jin20"],["EPI_CBV_jin40"],["EPI_CBV_jin60"],["EPI_CBV_alej"]], participants=["5502","5503"], denominator="level2_dgamma_blurxy"+str(i))

	l1("~/NIdata/ofM.dr/preprocessing/generic", workflow_name="generic", include={"subjects":[i for i in range(4001,4010)]+[4011,4012],"sessions":[]}, mask=None)
	l1("~/NIdata/ofM.dr/preprocessing/generic", workflow_name="masked", include={"subjects":[i for i in range(4001,4010)]+[4011,4012],"sessions":[]})
	# l1("~/NIdata/ofM.dr/preprocessing/generic")
