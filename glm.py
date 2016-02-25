import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.base import Bunch
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, Level1Design, FEATModel
from nipype.interfaces.afni import Bandpass
from nipype.algorithms.modelgen import SpecifyModel
import nipype.interfaces.io as nio
from os import path
from preprocessing import bru2_preproc, bru2_preproc2
from nipype.interfaces.nipy import SpaceTimeRealigner
import nipype.interfaces.ants as ants

def level1(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, resize=True, omit_ID=[], tr=1, inclusion_filter="", pipeline_denominator="FSL_GLM", template="ds_QBI_atlas100RD.nii", standalone_execute=False):
	workflow_base = path.expanduser(workflow_base)
	preprocessing = bru2_preproc(workflow_base, functional_scan_type, experiment_type=experiment_type, resize=resize, structural_scan_type=structural_scan_type, omit_ID=omit_ID, tr=tr, inclusion_filter=inclusion_filter, workflow_denominator="Preprocessing", template=template)


	def subjectinfo(subject_delay):
		from nipype.interfaces.base import Bunch
		from copy import deepcopy
		onsets=[]
		for i in range(6):
			onsets.append([range(222,222+180*6,180)[i]])
		output = []
		names = ['s1', 's2', 's3', 's4', 's5', 's6']
		for idx_a, a in enumerate(onsets):
			for idx_b, b in enumerate(a):
				onsets[idx_a][idx_b] = b-subject_delay
		output.append(Bunch(conditions=names,
						onsets=deepcopy(onsets),
						durations=[[20.0], [20.0], [20.0], [20.0], [20.0], [20.0]],
						))
		return output


	onsets=[]
	for i in range(6):
		onsets.append([range(222,222+180*6,180)[i]])

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = 128

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'dgamma': {'derivs':True}}
	level1design.inputs.model_serial_correlations = True
	level1design.inputs.contrasts = [['allStim','T', ["s1","s2","s3","s4","s5","s6"],[1,1,1,1,1,1]]]

	modelgen = pe.MapNode(interface=FEATModel(), name='modelgen', iterfield = 'fsf_file')

	glm = pe.MapNode(interface=GLM(), name='glm', iterfield='design')

	first_level = pe.Workflow(name="first_level")

	first_level.connect([
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		])

	pipeline = pe.Workflow(name=pipeline_denominator)

	pipeline.connect([
		(preprocessing, first_level, [(('timing_metadata.total_delay_s',subjectinfo),'specify_model.subject_info')]),
		(preprocessing, first_level, [('structural_bandpass.out_file','specify_model.functional_runs')]),
		(preprocessing, first_level, [('structural_bandpass.out_file','glm.in_file')]),
		])

	# pipeline.write_graph(graph2use="flat")
	if standalone_execute:
		pipeline.base_dir = workflow_base
		pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	else:
		return pipeline

def level2(measurements_base, functional_scan_type, structural_scan_type=None, tr=1, conditions=[], include_subjects=[], exclude_subjects=[], exclude_measurements=[], include_measurements=[], actual_size=False, pipeline_denominator="FSL_GLM2", template="ds_QBI_atlas100RD.nii", standalone_execute=True, compare_experiment_types=[]):
	measurements_base = path.expanduser(measurements_base)
	preprocessing = bru2_preproc2(measurements_base, functional_scan_type, structural_scan_type=structural_scan_type, tr=tr, conditions=conditions, include_subjects=include_subjects, exclude_subjects=exclude_subjects, exclude_measurements=exclude_measurements, include_measurements=include_measurements, actual_size=actual_size)


	def subjectinfo(subject_delay):
		from nipype.interfaces.base import Bunch
		from copy import deepcopy
		onsets=[]
		for i in range(6):
			onsets.append([range(222,222+180*6,180)[i]])
		output = []
		names = ['s1', 's2', 's3', 's4', 's5', 's6']
		for idx_a, a in enumerate(onsets):
			for idx_b, b in enumerate(a):
				onsets[idx_a][idx_b] = b-subject_delay
		output.append(Bunch(conditions=names,
						onsets=deepcopy(onsets),
						durations=[[20.0], [20.0], [20.0], [20.0], [20.0], [20.0]],
						))
		return output


	onsets=[]
	for i in range(6):
		onsets.append([range(222,222+180*6,180)[i]])

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.time_repetition = tr
	specify_model.inputs.high_pass_filter_cutoff = 128

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = tr
	level1design.inputs.bases = {'dgamma': {'derivs':True}}
	level1design.inputs.model_serial_correlations = True
	level1design.inputs.contrasts = [['allStim','T', ["s1","s2","s3","s4","s5","s6"],[1,1,1,1,1,1]]]

	modelgen = pe.MapNode(interface=FEATModel(), name='modelgen', iterfield = 'fsf_file')

	glm = pe.MapNode(interface=GLM(), name='glm', iterfield='design')

	first_level = pe.Workflow(name="first_level")

	first_level.connect([
		(specify_model, level1design, [('session_info', 'session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		(modelgen, glm, [('design_file', 'design')]),
		])

	pipeline = pe.Workflow(name=pipeline_denominator)

	pipeline.connect([
		(preprocessing, first_level, [(('timing_metadata.total_delay_s',subjectinfo),'specify_model.subject_info')]),
		(preprocessing, first_level, [('structural_bandpass.out_file','specify_model.functional_runs')]),
		(preprocessing, first_level, [('structural_bandpass.out_file','glm.in_file')]),
		])

	# pipeline.write_graph(graph2use="flat")
	if standalone_execute:
		pipeline.base_dir = measurements_base
		pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	else:
		return pipeline

# def level2(workflow_base, functional_scan_type, compare_experiment_types=None, structural_scan_type=None, resize=True, omit_ID=[], tr=1, inclusion_filter="", pipeline_denominator="GLM", template="ds_QBI_atlas100RD.nii"):
# 	workflow_base = path.expanduser(workflow_base)
# 	condition0 = level1(workflow_base=workflow_base, functional_scan_type=functional_scan_type, structural_scan_type=structural_scan_type, experiment_type=compare_experiment_types[0], omit_ID=omit_ID, pipeline_denominator="condition0")
# 	condition1 = level1(workflow_base=workflow_base, functional_scan_type=functional_scan_type, structural_scan_type=structural_scan_type, experiment_type=compare_experiment_types[1], omit_ID=omit_ID, pipeline_denominator="condition1")
#
# 	copemerge = pe.MapNode(interface=fsl.Merge(dimension='t'),iterfield=['in_files'], name="copemerge")
#
# 	varcopemerge = pe.MapNode(interface=fsl.Merge(dimension='t'), iterfield=['in_files'], name="varcopemerge")
#
# 	level2model = pe.Node(interface=fsl.L2Model(),name='l2model')
#
# 	flameo = pe.MapNode(interface=fsl.FLAMEO(run_mode='fe'), name="flameo", iterfield=['cope_file', 'var_cope_file'])
#
# 	second_level = pe.Workflow(name="second_level")
#
# 	pipeline = pe.Workflow(name=pipeline_denominator)
#
# 	pipeline.connect([
# 		(condition0, second_level, [('glm.out_cope','copemerge.in_files')]),
# 		(condition1, second_level, [('glm.out_cope','copemerge.in_files')]),
# 		(condition0, second_level, [('glm.out_varcb_name','varcopemerge.in_files')]),
# 		(condition1, second_level, [('glm.out_varcb_name','varcopemerge.in_files')]),
# 		(preprocessing, first_level, [('structural_bandpass.out_file','glm.in_file')]),
# 		])
#
# 	pipeline.write_graph(graph2use="flat")
# 	pipeline.base_dir = workflow_base
# 	pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})

if __name__ == "__main__":
	level2("~/NIdata/ofM.dr/", "7_EPI_CBV", structural_scan_type="T2_TurboRARE>", conditions=["ofM","ofM_aF"], exclude_measurements=["20151027_121613_4013_1_1"])
