import inspect
import re
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
from itertools import product
from nipype.algorithms.modelgen import SpecifyModel
from os import path, listdir, remove, getcwd

from extra_interfaces import GenL2Model
from preprocessing import bruker
from utils import datasource_exclude
try:
	from ..extra_functions import get_level2_inputs, get_subjectinfo, write_function_call
except ValueError:
	import os
	import sys
	sys.path.append(os.path.expanduser('~/src/SAMRI/samri/pipelines'))
	from extra_functions import get_level2_inputs, get_subjectinfo, write_function_call

def getlen(a):
	return len(a)
def add_suffix(name, suffix):
	return str(name)+str(suffix)

def l2_common_effect(l1_dir,
	exclude={},
	groupby="session",
	keep_work=False,
	l2_dir="",
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

	datasource = pe.Node(interface=nio.DataGrabber(infields=["group",], outfields=["copes", "varcbs"]), name="datasource")
	datasource.inputs.base_directory = l1_dir
	datasource.inputs.sort_filelist = True
	datasource.inputs.template = "*"
	datasource.inputs.template_args = dict(
		copes=[['group','group']],
		varcbs=[['group','group']]
		)

	infosource = pe.Node(interface=util.IdentityInterface(fields=['iterable']), name="infosource")

	copemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="copemerge")
	varcopemerge = pe.Node(interface=fsl.Merge(dimension='t'),name="varcopemerge")

	level2model = pe.Node(interface=fsl.L2Model(),name='level2model')

	flameo = pe.Node(interface=fsl.FLAMEO(), name="flameo")
	flameo.inputs.mask_file="/home/chymera/NIdata/templates/ds_QBI_chr_bin.nii.gz"
	flameo.inputs.run_mode="ols"

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(l2_dir,workflow_name)
	datasink.inputs.substitutions = [('_iterable_', ''),]

	if groupby == "subject":
		infosource.iterables = [('iterable', subjects)]
		datasource.inputs.field_template = dict(
			copes="sub-%s/ses-*/sub-%s_ses-*_trial-*_cope.nii.gz",
			varcbs="sub-%s/ses-*/sub-%s_ses-*_trial-*_varcb.nii.gz",
			)
	elif groupby == "session":
		infosource.iterables = [('iterable', sessions)]
		datasource.inputs.field_template = dict(
			copes="sub-*/ses-%s/sub-*_ses-%s_trial-*_cope.nii.gz",
			varcbs="sub-*/ses-%s/sub-*_ses-%s_trial-*_varcb.nii.gz",
			)
	elif groupby == "scan":
		infosource.iterables = [('iterable', scans)]
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
		]

	workdir_name = workflow_name+"_work"
	workflow = pe.Workflow(name=workdir_name)
	workflow.connect(workflow_connections)
	workflow.base_dir = l2_dir
	workflow.write_graph(dotfilename=path.join(workflow.base_dir,workdir_name,"graph.dot"), graph2use="hierarchical", format="png")

	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : nprocs})
	if not keep_work:
		shutil.rmtree(path.join(workdir_name))

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

if __name__ == "__main__":
	# level1("~/NIdata/ofM.dr/", {"7_EPI_CBV":"6_20_jb"}, structural_scan_types=-1, conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], exclude_measurements=["20151027_121613_4013_1_1"], pipeline_denominator="level1_dgamma_blurxy56n", blur_xy=5.6)
	# level1("~/NIdata/ofM.erc/", {"EPI_CBV_jin6":"jin6","EPI_CBV_jin10":"jin10","EPI_CBV_jin20":"jin20","EPI_CBV_jin40":"jin40","EPI_CBV_jin60":"jin60","EPI_CBV_alej":"alej",}, structural_scan_types=-1, actual_size=False, pipeline_denominator="level1_dgamma")
	# level2_common_effect("~/NIdata/ofM.erc/GLM/level1_dgamma", categories=[], scan_types=[["EPI_CBV_jin6"],["EPI_CBV_jin10"],["EPI_CBV_jin20"],["EPI_CBV_jin40"],["EPI_CBV_jin60"],["EPI_CBV_alej"]], participants=["5502","5503"], denominator="level2_dgamma")
	# for i in range(4,8):
	# 	level1("~/NIdata/ofM.erc/", {"EPI_CBV_jin6":"jin6","EPI_CBV_jin10":"jin10","EPI_CBV_jin20":"jin20","EPI_CBV_jin40":"jin40","EPI_CBV_jin60":"jin60","EPI_CBV_alej":"alej",}, structural_scan_types=-1, actual_size=False, pipeline_denominator="level1_dgamma_blurxy"+str(i), blur_xy=i)

	# l2_common_effect("~/NIdata/ofM.dr/l1/generic", workflow_name="subjectwise", groupby="subject")
	# l2_common_effect("~/NIdata/ofM.dr/l1/generic", workflow_name="sessionwise_responders", groupby="session", exclude={"subjects":["4001","4008"]})
	# l2_common_effect("~/NIdata/ofM.dr/l1/generic", workflow_name="sessionwise_all", groupby="session")

	# l2_common_effect("~/NIdata/ofM.dr/l1/generic_funcreg", workflow_name="subjectwise_funcreg", groupby="subject")
	# l2_common_effect("~/NIdata/ofM.dr/l1/norealign", workflow_name="subjectwise_norealign", groupby="subject")
	# l2_common_effect("~/NIdata/ofM.dr/l1/generic", workflow_name="sessionwise_generic", groupby="session", exclude={"subjects":["4001","4002","4003","4004","4005","4006","4009"]})
	# l2_common_effect("~/NIdata/ofM.dr/l1/withhabituation", workflow_name="subjectwise_withhabituation", groupby="subject")
	# l2_common_effect("~/NIdata/ofM.dr/l1/generic", workflow_name="subjectwise_generic", groupby="subject")
	# l2_common_effect("~/NIdata/ofM.dr/l1/withhabituation", workflow_name="subjectwise_withhabituation", groupby="subject")

	# l2_common_effect("~/NIdata/ofM.dr/l1/dr_mask", workflow_name="subjectwise_dr_mask", groupby="subject")
	l2_common_effect("~/NIdata/ofM.dr/l1/dr_mask", workflow_name="sessionwise_dr_mask", groupby="session", exclude={"subjects":["4001","4002","4003","4004","4005","4006","4009","4013"]})
