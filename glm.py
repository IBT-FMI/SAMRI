import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask
# from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET
import nipype.interfaces.io as nio
from os import path
from preprocessing import bru2_preproc
from nipype.interfaces.nipy import SpaceTimeRealigner
import nipype.interfaces.ants as ants

def fsl_glm(workflow_base, functional_scan_type, structural_scan_type=None, experiment_type=None, workflow_denominator="FSL_GLM", omit_ID=[]):
	workflow_base = path.expanduser(workflow_base)
	bru2_preproc_workflow = bru2_preproc(workflow_base, functional_scan_type, structural_scan_type=structural_scan_type, experiment_type=experiment_type, omit_ID=omit_ID)

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realign")
	realigner.inputs.tr = 1
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for saggital)
	realigner.inputs.slice_times = "asc_alt_2"

	meaner = pe.Node(interface=MeanImage(), name="temporal_mean")
	masker = pe.Node(interface=ApplyMask(), name="mask_application")

	spatial_filtering = pe.Node(interface=FAST(), name="FAST")
	spatial_filtering.inputs.output_biascorrected = True
	spatial_filtering.inputs.bias_iters = 8

	spatial_filtering_structural = pe.Node(interface=FAST(), name="FAST_structural")
	spatial_filtering_structural.inputs.output_biascorrected = True
	spatial_filtering_structural.inputs.bias_iters = 8

	skullstripping = pe.Node(interface=BET(), name="BET")
	skullstripping.inputs.mask = True
	skullstripping.inputs.frac = 0.7

	skullstripping_structural = pe.Node(interface=BET(), name="BET_structural")
	skullstripping_structural.inputs.mask = True
	skullstripping_structural.inputs.frac = 0.7

	reg = pe.Node(ants.Registration(), name='antsRegister')
	reg.inputs.fixed_image = "/home/chymera/data/reference/QBI_atlas100.nii"
	reg.inputs.output_transform_prefix = "output_"
	reg.inputs.transforms = ['Rigid', 'Affine', 'SyN']
	reg.inputs.transform_parameters = [(0.1,), (0.1,), (0.2, 3.0, 0.0)]
	reg.inputs.number_of_iterations = [[10000, 11110, 11110]] * 2 + [[100, 30, 20]]
	reg.inputs.dimension = 3
	reg.inputs.write_composite_transform = True
	reg.inputs.collapse_output_transforms = True
	reg.inputs.initial_moving_transform_com = True
	reg.inputs.metric = ['Mattes'] * 2 + [['Mattes', 'CC']]
	reg.inputs.metric_weight = [1] * 2 + [[0.5, 0.5]]
	reg.inputs.radius_or_number_of_bins = [32] * 2 + [[32, 4]]
	reg.inputs.sampling_strategy = ['Regular'] * 2 + [[None, None]]
	reg.inputs.sampling_percentage = [0.3] * 2 + [[None, None]]
	reg.inputs.convergence_threshold = [1.e-8] * 2 + [-0.01]
	reg.inputs.convergence_window_size = [20] * 2 + [5]
	reg.inputs.smoothing_sigmas = [[4, 2, 1]] * 2 + [[1, 0.5, 0]]
	reg.inputs.sigma_units = ['vox'] * 3
	reg.inputs.shrink_factors = [[3, 2, 1]]*2 + [[4, 2, 1]]
	reg.inputs.use_estimate_learning_rate_once = [True] * 3
	reg.inputs.use_histogram_matching = [False] * 2 + [True]
	reg.inputs.winsorize_lower_quantile = 0.005
	reg.inputs.winsorize_upper_quantile = 0.995
	reg.inputs.args = '--float'
	reg.inputs.output_warped_image = 'output_warped_image.nii.gz'
	reg.inputs.num_threads = 4
	reg.plugin_args = {'qsub_args': '-pe orte 4', 'sbatch_args': '--mem=6G -c 4'}


	coregistration_designer = pe.Node(interface=FLIRT(), name="FLIRT_design")
	coregistration_designer.inputs.reference = "/home/chymera/data/reference/QBI_atlas100.nii"

	warpall = pe.Node(ants.ApplyTransforms(),name='functional_warp')
	warpall.inputs.reference_image = "/home/chymera/data/reference/QBI_atlas100.nii"
	warpall.inputs.input_image_type = 3
	warpall.inputs.interpolation = 'Linear'
	warpall.inputs.invert_transform_flags = [False, False]
	warpall.inputs.terminal_output = 'file'

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
		(skullstripping_structural, spatial_filtering_structural, [('out_file', 'in_files')]),
		(skullstripping, spatial_filtering, [('out_file', 'in_files')]),
		(skullstripping, masker, [('mask_file', 'mask_file')]),
		(spatial_filtering, reg, [('restored_image', 'moving_image')]),
		(reg, warpall, [('composite_transform', 'transforms')]),
		(masker, warpall, [('out_file', 'input_image')]),
		(warpall, melodic, [('output_image', 'in_files')]),
		(melodic, datasink, [('report_dir', 'MELODIC_reports')])
		])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([
		(bru2_preproc_workflow, analysis_workflow, [('bru2nii.nii_file','realign.in_file')]),
		(bru2_preproc_workflow, analysis_workflow, [('bru2nii_structural.nii_file','BET_structural.in_file')])
		])

	pipeline.write_graph(graph2use="flat")
	pipeline.run(plugin="MultiProc")

if __name__ == "__main__":
	fsl_glm(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", structural_scan_type="T2_TurboRARE>", experiment_type="<ofM>", omit_ID=["20151026_135856_4006_1_1", "20151027_121613_4013_ofM_1_1"])
