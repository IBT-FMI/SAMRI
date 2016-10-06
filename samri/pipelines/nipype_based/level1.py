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
from nipype.algorithms.modelgen import SpecifyModel
from nipype.interfaces.fsl import GLM, FEATModel, Merge, L2Model, FLAMEO, model

from extra_interfaces import GenL2Model
from preprocessing import bru_preproc

def l1(preprocessing_dir):
	preprocessing_dir = path.expanduser(preprocessing_dir)
	# inputs = bids_inputs(preprocessing_dir)
	# print(inputs)
	# dg = nio.DataGrabber(infields=["sub"])
	# dg = nio.DataGrabber(infields=['sub','ses','sub','ses','scan'])
	# dg.inputs.base_directory = preprocessing_dir
	# dg.inputs.sort_filelist = True
	# dg.inputs.template = "%s"
	# dg.inputs.sub = "*"
	# dg.inputs.template = "sub-{}/ses-{}/func/sub-{}_ses-{}_trial-{}.nii.gz"
	# dg.run()

	df = nio.DataFinder()
	df.inputs.root_paths = preprocessing_dir
	df.inputs.match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/func/.*?_trial-(?P<scan>.+)\.nii.gz'
	# df.inputs.match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/func/sub-(?P<sub>.+)_ses-(?P<ses>.+)_trial-(?P<scan>.+)\.nii.gz'
	result = df.run()
	iterfields = zip(*[result.outputs.sub, result.outputs.ses, result.outputs.scan])
	# print(iterfields)

	df1 = nio.DataFinder()
	df1.inputs.root_paths = preprocessing_dir
	df1.inputs.match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/func/.*?_trial-(?P<scan>.+)\.nii.gz'
	# df.inputs.match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/func/sub-(?P<sub>.+)_ses-(?P<ses>.+)_trial-(?P<scan>.+)\.nii.gz'
	result = df1.run()
	iterfields = zip(*[result.outputs.sub, result.outputs.ses, result.outputs.scan])
	# print(iterfields)



	# infosource = util.IdentityInterface(fields=['sub_ses_scan'], mandatory_inputs=False)
	# infosource.iterables = [('sub_ses_scan',iterfields)]
	# print(infosource.inputs.sub_ses_scan)
	# out = infosource.run()
	# # result = infosource.run()
	# # print(infosource.sub_ses_scan)
	# print(out.outputs.sub_ses_scan)

	# workflow_connections = [
	# 	(infosource, get_functional_scan, [('subject_condition', 'selector')]),
	# 	(infosource, bids_stim_filename, [('subject_condition', 'subject_condition')]),
	# 	]
	#
	# workflow = pe.Workflow(name=workdir_name)
	# workflow.connect(workflow_connections)
	# workflow.run()

	# print("sub-4011/ses-ofM_aF/func/sub-4011_ses-ofM_aF_trial-7_EPI_CBV_cbv.nii.gz")

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

	level1design = pe.Node(interface=model.Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'dgamma': {'derivs':False}}
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
				print "WARNING: Some expected scans have not been found (or another RuntimeError has occured)."
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

	l1("~/NIdata/ofM.dr/preprocessing/generic")

	# level2_common_effect("~/NIdata/ofM.dr/GLM/level1_gamma", categories=["ofM_cF2"], participants=["4008","4007","4011","4012"], scan_types=["7_EPI_CBV"])
	# level2_common_effect("~/NIdata/ofM.dr/GLM/level1_dgamma_blurxy56", categories=[["ofM"],["ofM_aF"],["ofM_cF1"],["ofM_cF2"],["ofM_pF"]], participants=["4008","4007","4011","4012"], scan_types=["7_EPI_CBV"],denominator="level2_dgamma_blurxy56")
	# level2_common_effect("~/NIdata/ofM.dr/GLM/level1_dgamma_blurxy56n", categories=[["ofM"],["ofM_aF"],["ofM_cF1"],["ofM_cF2"],["ofM_pF"]], participants=["4008","4007","4011","4012"], scan_types=["7_EPI_CBV"],denominator="level2_dgamma_blurxy56n")
	# level2_common_effect("~/NIdata/ofM.erc/GLM/level1_ext_dgamma_blur56", categories=[], scan_types=[["EPI_CBV_jin6"],["EPI_CBV_jin10"],["EPI_CBV_jin20"],["EPI_CBV_jin40"],["EPI_CBV_jin60"],["EPI_CBV_alej"]], participants=["5502","5503"], denominator="level2_ext_dgamma_level1_ext_dgamma_blur56")
