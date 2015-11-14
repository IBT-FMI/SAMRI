import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask
# from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET
import nipype.interfaces.io as nio
from os import path
from preprocessing import bru2_preproc
from nipype.interfaces.nipy import SpaceTimeRealigner

def fsl_glm(workflow_base, functional_scan_type, structural_scan_type=None, experiment_type=None, workflow_denominator="FSL_GLM", omit_ID=[]):
	workflow_base = path.expanduser(workflow_base)
	bru2_preproc_workflow = bru2_preproc(workflow_base, functional_scan_type, structural_scan_type=structural_scan_type, experiment_type=experiment_type, omit_ID=omit_ID)

	meaner = pe.Node(interface=MeanImage(), name="temporal_mean")
	masker = pe.Node(interface=ApplyMask(), name="mask_application")

	spatial_filtering = pe.Node(interface=FAST(), name="FAST")
	spatial_filtering.inputs.output_biascorrected = True
	spatial_filtering.inputs.bias_iters = 8

	skullstripping = pe.Node(interface=BET(), name="BET")
	skullstripping.inputs.functional = True
	skullstripping.inputs.mask = True
	# skullstripping_structural = pe.Node(interface=BET(), name="BET_structural")

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realign")
	realigner.inputs.tr = 1
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for saggital)
	realigner.inputs.slice_times = "asc_alt_2"

	coregistration_designer = pe.Node(interface=FLIRT(), name="FLIRT_design")
	coregistration_designer.inputs.reference = "/home/chymera/data/reference/QBI_atlas100.nii"

	coregistration_implementer = pe.Node(interface=FLIRT(), name="FLIRT_implement")
	coregistration_implementer.inputs.reference = "/home/chymera/data/reference/QBI_atlas100.nii"

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	datasink = pe.Node(nio.DataSink(), name='sinker')
	datasink.inputs.base_directory = workflow_base+"/"+workflow_denominator+"_results"

	#SET UP ANALYSIS WORKFLOW:
	analysis_workflow = pe.Workflow(name="GLM")

	analysis_workflow.connect([
		(realigner, meaner, [('out_file', 'in_file')]),
		(realigner, masker, [('out_file', 'in_file')]),
		(meaner, skullstripping, [('out_file', 'in_file')]),
		(skullstripping, spatial_filtering, [('out_file', 'in_files')]),
		(skullstripping, masker, [('mask_file', 'mask_file')]),
		(spatial_filtering, coregistration_designer, [('restored_image', 'in_file')]),
		(coregistration_designer, coregistration_implementer, [('out_matrix_file', 'in_matrix_file')]),
		(masker, coregistration_implementer, [('out_file', 'in_file')]),
		(coregistration_implementer, melodic, [('out_file', 'in_files')]),
		(melodic, datasink, [('report_dir', 'MELODIC_reports')])
		])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([(bru2_preproc_workflow, analysis_workflow, [('bru2nii.nii_file','realign.in_file')])
		])

	pipeline.write_graph(graph2use="flat")
	pipeline.run(plugin="MultiProc")

if __name__ == "__main__":
	fsl_glm(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", experiment_type="<ofM>", omit_ID=["20151026_135856_4006_1_1", "20151027_121613_4013_ofM_1_1"])
