import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, FEATModel, Merge, L2Model, FLAMEO, Cluster
from gamma_fix import Level1Design
from nipype.algorithms.modelgen import SpecifyModel
import nipype.interfaces.io as nio
from os import path, listdir, remove, getcwd
from extra_interfaces import GenL2Model
from extra_functions import get_level2_inputs, get_subjectinfo, write_function_call
from preprocessing import bru_preproc
from nipype.interfaces.nipy import SpaceTimeRealigner
import nipype.interfaces.ants as ants
from itertools import product
import inspect
import re

def getlen(a):
	the_len = len(a)
	return the_len

def level2_common_effect(level1_directory, categories=[], participants=[], scan_types=[], denominator="level2"):
	level1_directory = path.expanduser(level1_directory)
	#edit the following lines to choose different outputs (e.g. from functional coregistration)
	copemergeroot = level1_directory+"/results/func_cope/"
	varcbmergeroot = level1_directory+"/results/func_varcb/"

	copemerge = pe.Node(interface=Merge(dimension='t'),name="copemerge")
	varcopemerge = pe.Node(interface=Merge(dimension='t'),name="varcopemerge")

	level2model = pe.Node(interface=L2Model(),name='level2model')

	flameo = pe.MapNode(interface=FLAMEO(), name="flameo", iterfield=['cope_file','var_cope_file'])
	flameo.inputs.mask_file="/home/chymera/NIdata/templates/ds_QBI_chr_bin.nii.gz"
	flameo.inputs.run_mode="ols"

	workflow_connections = [
		(copemerge,flameo,[('merged_file','cope_file')]),
		(varcopemerge,flameo,[('merged_file','var_cope_file')]),
		(level2model,flameo, [('design_mat','design_file')]),
		(level2model,flameo, [('design_grp','cov_split_file')]),
		(level2model,flameo, [('design_con','t_con_file')]),
		]

	multi_scan_type = False
	multi_category = False
	try:
		if isinstance(scan_types[0],list):
			multi_scan_type = True
	except IndexError:
		pass
	try:
		if isinstance(categories[0],list):
			multi_category = True
	except IndexError:
		pass

	if multi_category or multi_scan_type:
		get_copes = pe.Node(name='get_copes', interface=util.Function(function=get_level2_inputs,input_names=["input_root","categories","participants","scan_types"], output_names=['scan_paths']))
		get_copes.inputs.input_root=copemergeroot
		get_copes.inputs.participants=participants
		get_varcbs = pe.Node(name='get_varcbs', interface=util.Function(function=get_level2_inputs,input_names=["input_root","categories","participants","scan_types"], output_names=['scan_paths']))
		get_varcbs.inputs.input_root=varcbmergeroot
		get_varcbs.inputs.participants=participants

		if not multi_category:
			infosource = pe.Node(interface=util.IdentityInterface(fields=['scan_type_multi']), name="infosource")
			infosource.iterables = [('scan_type_multi',scan_types)]
			get_copes.inputs.categories=categories
			get_varcbs.inputs.categories=categories
			workflow_connections.extend([
				(infosource, get_copes, [('scan_type_multi', 'scan_types')]),
				(infosource, get_varcbs, [('scan_type_multi', 'scan_types')]),
				])

		if not multi_scan_type:
			infosource = pe.Node(interface=util.IdentityInterface(fields=['category_multi']), name="infosource")
			infosource.iterables = [('category_multi',categories)]
			get_copes.inputs.scan_types=scan_types
			get_varcbs.inputs.scan_types=scan_types
			workflow_connections.extend([
				(infosource, get_copes, [('category_multi', 'categories')]),
				(infosource, get_varcbs, [('category_multi', 'categories')]),
				])

		workflow_connections.extend([
			(get_copes, copemerge, [('scan_paths', 'in_files')]),
			(get_varcbs, varcopemerge, [('scan_paths', 'in_files')]),
			(get_copes, level2model, [(('scan_paths',getlen), 'num_copes')]),
			])
	else:
		copes = get_level2_inputs(copemergeroot, categories=categories, participants=participants, scan_types=scan_types)
		varcbs = get_level2_inputs(varcbmergeroot, categories=categories, participants=participants, scan_types=scan_types)

		copemerge.inputs.in_files=copes
		varcopemerge.inputs.in_files=varcbs

		level2model.inputs.num_copes=len(copes)

	second_level = pe.Workflow(name=denominator)
	second_level.connect(workflow_connections)

	second_level.base_dir = level1_directory+"/.."
	second_level.write_graph(dotfilename=path.join(second_level.base_dir,denominator,"graph.dot"),graph2use="flat")
	second_level.run(plugin="MultiProc",  plugin_args={'n_procs' : 6})

def level2(level1_directory, categories=["ofM","ofM_aF"], participants=["4008","4007","4011","4012"], denominator="level2"):
	level1_directory = path.expanduser(level1_directory)
	copemergeroot = level1_directory+"/results/cope/"
	varcbmergeroot = level1_directory+"/results/varcb/"

	subirs_list = [category+"."+participant for category, participant in product(categories,participants)]

	copes = [copemergeroot+sub_dir+"/cope.nii.gz" for sub_dir in subirs_list]

	copemerge = pe.Node(interface=Merge(dimension='t'),name="copemerge")
	copemerge.inputs.in_files=copes

	varcopemerge = pe.Node(interface=Merge(dimension='t'),name="varcopemerge")
	varcopemerge.inputs.in_files=[varcbmergeroot+sub_dir+"/varcb.nii.gz" for sub_dir in subirs_list]

	level2model = pe.Node(interface=GenL2Model(),name='level2model')
	level2model.inputs.num_copes=len(copes)
	level2model.inputs.conditions=categories
	level2model.inputs.subjects=participants

	flameo = pe.MapNode(interface=FLAMEO(), name="flameo", iterfield=['cope_file','var_cope_file'])
	flameo.inputs.mask_file="/home/chymera/NIdata/templates/ds_QBI_chr_bin.nii.gz"
	flameo.inputs.run_mode="ols"

	second_level = pe.Workflow(name=denominator)

	second_level.connect([
		(copemerge,flameo,[('merged_file','cope_file')]),
		(varcopemerge,flameo,[('merged_file','var_cope_file')]),
		(level2model,flameo, [('design_mat','design_file')]),
		(level2model,flameo, [('design_grp','cov_split_file')]),
		(level2model,flameo, [('design_con','t_con_file')]),
		])

	second_level.write_graph(graph2use="flat")
	second_level.base_dir = level1_directory+"/.."
	second_level.run(plugin="MultiProc",  plugin_args={'n_procs' : 6})

def level1(measurements_base, functional_scan_types, structural_scan_types=[], tr=1, conditions=[], subjects=[], exclude_subjects=[], measurements=[], exclude_measurements=[], actual_size=False, pipeline_denominator="level1", template="/home/chymera/NIdata/templates/ds_QBI_chr.nii.gz", standalone_execute=True, compare_experiment_types=[], quiet=True):
	"""Runs a first-level analysis while calling the bru_preproc workflow for preprocessing

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
	preprocessing = bru_preproc(measurements_base, functional_scan_types_list, structural_scan_types=structural_scan_types, tr=tr, conditions=conditions, subjects=subjects, exclude_subjects=exclude_subjects, measurements=measurements, exclude_measurements=exclude_measurements, actual_size=actual_size, template=template)

	get_subject_info = pe.Node(name='get_subject_info', interface=util.Function(function=get_subjectinfo,input_names=["subject_delay","scan_type","scan_types"], output_names=['output']))
	get_subject_info.inputs.scan_types = functional_scan_types

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = 180

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'gamma': {'derivs':False}}
	level1design.inputs.model_serial_correlations = True
	level1design.inputs.contrasts = [('allStim','T', ["s1","s2","s3","s4","s5","s6"],[1,1,1,1,1,1])]

	modelgen = pe.Node(interface=FEATModel(), name='modelgen')

	func_glm = pe.Node(interface=GLM(), name='func_glm', iterfield='design')
	func_glm.inputs.out_cope="cope.nii.gz"
	func_glm.inputs.out_varcb_name="varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	func_glm.inputs.out_file="betas.nii.gz"
	func_glm.inputs.out_t_name="t_stat.nii.gz"
	func_glm.inputs.out_p_name="p_stat.nii.gz"

	struc_glm = pe.Node(interface=GLM(), name='struc_glm', iterfield='design')
	struc_glm.inputs.out_cope="cope.nii.gz"
	struc_glm.inputs.out_varcb_name="varcb.nii.gz"
	#not setting a betas output file might lead to beta export in lieu of COPEs
	struc_glm.inputs.out_file="betas.nii.gz"
	struc_glm.inputs.out_t_name="t_stat.nii.gz"
	struc_glm.inputs.out_p_name="p_stat.nii.gz"

	# Cluster._cmd = "fsl_cluster" #on NeuroGentoo this file is renamed to avoid a collision with one of FSL's deps
	# cluster = pe.Node(interface=Cluster(), name="cluster")
	# cluster.inputs.threshold = 0.95
	# cluster.inputs.out_max_file = "out_max_file"
	# cluster.inputs.out_mean_file = "out_mean_file"
	# cluster.inputs.out_size_file = "out_size_file"

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
		# (cluster, datasink, [('localmax_vol_file', 'localmax_vol_file')]),
		# (cluster, datasink, [('max_file', 'max_file')]),
		# (cluster, datasink, [('mean_file', 'mean_file')]),
		# (cluster, datasink, [('pval_file', 'pval_file')]),
		# (cluster, datasink, [('size_file', 'size_file')]),
		# (cluster, datasink, [('threshold_file', 'threshold_file')]),
		# (glm, cluster, [('out_t', 'in_file')]),
		# (glm, cluster, [('out_cope', 'cope_file')]),

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
				print "WARNING: Some expected scans have not been found (or another RuntimeError has occured)."
			for f in listdir(getcwd()):
				if re.search("crash.*?get_structural_scan|get_functional_scan.*", f):
					remove(path.join(getcwd(), f))
		else:
			pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	else:
		return pipeline

if __name__ == "__main__":
	# level1("~/NIdata/ofM.dr/", {"7_EPI_CBV":"6_20_jb"}, structural_scan_types=-1, conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], exclude_measurements=["20151027_121613_4013_1_1"])
	# level1("~/NIdata/ofM.erc/", {"EPI_CBV_jin6":"jin6","EPI_CBV_jin10":"jin10","EPI_CBV_jin20":"jin20","EPI_CBV_jin40":"jin40","EPI_CBV_jin60":"jin60","EPI_CBV_alej":"alej",}, structural_scan_types=-1, actual_size=False, pipeline_denominator="level1_ext_gamma")
	# level1("~/NIdata/ofM.erc/", {"EPI_CBV_jin6":"jin6","EPI_CBV_jin10":"jin10"}, structural_scan_types=["T2_TurboRARE"])
	# level2_common_effect("~/NIdata/ofM.dr/level1_CBV", categories=["ofM_cF2"], participants=["4008","4007","4011","4012"], scan_types=["7_EPI_CBV"])
	# level2_common_effect("~/NIdata/ofM.dr/level1", categories=[["ofM"],["ofM_aF"],["ofM_cF1"],["ofM_cF2"],["ofM_pF"]], participants=["4008","4007","4012","4009"], scan_types=["7_EPI_CBV"])
	# level2("~/NIdata/ofM.dr/level1")
	level2_common_effect("~/NIdata/ofM.erc/GLM/level1", categories=[], scan_types=[["EPI_CBV_jin6"],["EPI_CBV_jin10"],["EPI_CBV_jin20"],["EPI_CBV_jin40"],["EPI_CBV_jin60"],["EPI_CBV_alej"]], participants=["5502","5503"])
