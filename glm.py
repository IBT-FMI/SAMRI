import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.base import Bunch
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, Level1Design, FEATModel
from nipype.interfaces.afni import Bandpass
from nipype.algorithms.modelgen import SpecifyModel
import nipype.interfaces.io as nio
from os import path
from preprocessing import bru2_preproc
from nipype.interfaces.nipy import SpaceTimeRealigner
import nipype.interfaces.ants as ants

def level1(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, resize=True, omit_ID=[], tr=1, inclusion_filter="", pipeline_denominator="FSL_GLM", template="ds_QBI_atlas100RD.nii"):
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

	pipeline = pe.Workflow(name=pipeline_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([
		(preprocessing, first_level, [(('timing_metadata.total_delay_s',subjectinfo),'specify_model.subject_info')]),
		(preprocessing, first_level, [('structural_bandpass.out_file','specify_model.functional_runs')]),
		(preprocessing, first_level, [('structural_bandpass.out_file','glm.in_file')]),
		])

	# pipeline.write_graph(graph2use="flat")
	pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})

def level2(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, resize=True, omit_ID=[], tr=1, inclusion_filter="", pipeline_denominator="FSL_GLM", template="ds_QBI_atlas100RD.nii"):


if __name__ == "__main__":
	level1(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", structural_scan_type="T2_TurboRARE>", experiment_type="<ofM_aF>", omit_ID=["20151027_121613_4013_1_1"])
	level2(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", structural_scan_type="T2_TurboRARE>", experiment_type="<ofM_aF>", omit_ID=["20151027_121613_4013_1_1"])
