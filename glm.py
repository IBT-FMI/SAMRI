import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths
# from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET
import nipype.interfaces.io as nio
from os import path
from preprocessing import bru2_preproc
from nipype.interfaces.nipy import SpaceTimeRealigner
import nipype.interfaces.ants as ants

def fsl_glm(workflow_base, functional_scan_type, structural_scan_type=None, experiment_type=None, workflow_denominator="FSL_GLM", omit_ID=[]):
	workflow_base = path.expanduser(workflow_base)
	bru2_preproc_workflow = bru2_preproc(workflow_base, functional_scan_type, structural_scan_type=structural_scan_type, experiment_type=experiment_type, omit_ID=omit_ID)

	meaner = pe.Node(interface=MeanImage(), name="temporal_mean")
	functional_masker = pe.Node(interface=ApplyMask(), name="functional_masker")

	structural_cutoff = pe.Node(interface=ImageMaths(), name="structural_cutoff")
	structural_cutoff.inputs.op_string = "-thrP 45"

	structural_BET = pe.Node(interface=BET(), name="structural_BET")
	structural_BET.inputs.mask = True
	structural_BET.inputs.frac = 0.5

	structural_registration = pe.Node(ants.Registration(), name='structural_registration')
	structural_registration.inputs.fixed_image = "/home/chymera/NIdata/templates/QBI_atlas100RD.nii.gz"
	structural_registration.inputs.output_transform_prefix = "output_"
	structural_registration.inputs.transforms = ['Rigid', 'Affine', 'SyN']
	structural_registration.inputs.transform_parameters = [(0.1,), (0.1,), (0.2, 3.0, 0.0)]
	structural_registration.inputs.number_of_iterations = [[10000, 11110, 11110]] * 2 + [[100, 30, 20]]
	structural_registration.inputs.dimension = 3
	structural_registration.inputs.write_composite_transform = True
	structural_registration.inputs.collapse_output_transforms = True
	structural_registration.inputs.initial_moving_transform_com = True
	structural_registration.inputs.metric = ['Mattes'] * 2 + [['Mattes', 'CC']]
	structural_registration.inputs.metric_weight = [1] * 2 + [[0.5, 0.5]]
	structural_registration.inputs.radius_or_number_of_bins = [32] * 2 + [[32, 4]]
	structural_registration.inputs.sampling_strategy = ['Regular'] * 2 + [[None, None]]
	structural_registration.inputs.sampling_percentage = [0.3] * 2 + [[None, None]]
	structural_registration.inputs.convergence_threshold = [1.e-8] * 2 + [-0.01]
	structural_registration.inputs.convergence_window_size = [20] * 2 + [5]
	structural_registration.inputs.smoothing_sigmas = [[4, 2, 1]] * 2 + [[1, 0.5, 0]]
	structural_registration.inputs.sigma_units = ['vox'] * 3
	structural_registration.inputs.shrink_factors = [[3, 2, 1]]*2 + [[4, 2, 1]]
	structural_registration.inputs.use_estimate_learning_rate_once = [True] * 3
	structural_registration.inputs.use_histogram_matching = [False] * 2 + [True]
	structural_registration.inputs.winsorize_lower_quantile = 0.005
	structural_registration.inputs.winsorize_upper_quantile = 0.995
	structural_registration.inputs.args = '--float'
	structural_registration.inputs.output_warped_image = 'output_warped_image.nii.gz'
	structural_registration.inputs.num_threads = 4
	structural_registration.plugin_args = {'qsub_args': '-pe orte 4', 'sbatch_args': '--mem=6G -c 4'}

	structural_warp = pe.Node(ants.ApplyTransforms(),name='structural_warp')
	structural_warp.inputs.reference_image = "/home/chymera/NIdata/templates/QBI_atlas100RD.nii.gz"
	structural_warp.inputs.input_image_type = 3
	structural_warp.inputs.interpolation = 'Linear'
	structural_warp.inputs.invert_transform_flags = [False]
	structural_warp.inputs.terminal_output = 'file'
	structural_warp.num_threads = 4

	functional_registration = pe.Node(ants.Registration(), name='functional_registration')
	functional_registration.inputs.fixed_image = "/home/chymera/NIdata/templates/QBI_atlas100RD.nii.gz"
	functional_registration.inputs.output_transform_prefix = "output_"
	functional_registration.inputs.transforms = ['Rigid', 'Affine', 'SyN']
	functional_registration.inputs.transform_parameters = [(0.1,), (0.1,), (0.2, 3.0, 0.0)]
	functional_registration.inputs.number_of_iterations = [[10000, 11110, 11110]] * 2 + [[100, 30, 20]]
	functional_registration.inputs.dimension = 3
	functional_registration.inputs.write_composite_transform = True
	functional_registration.inputs.collapse_output_transforms = True
	functional_registration.inputs.initial_moving_transform_com = True
	functional_registration.inputs.metric = ['Mattes'] * 2 + [['Mattes', 'CC']]
	functional_registration.inputs.metric_weight = [1] * 2 + [[0.5, 0.5]]
	functional_registration.inputs.radius_or_number_of_bins = [32] * 2 + [[32, 4]]
	functional_registration.inputs.sampling_strategy = ['Regular'] * 2 + [[None, None]]
	functional_registration.inputs.sampling_percentage = [0.3] * 2 + [[None, None]]
	functional_registration.inputs.convergence_threshold = [1.e-8] * 2 + [-0.01]
	functional_registration.inputs.convergence_window_size = [20] * 2 + [5]
	functional_registration.inputs.smoothing_sigmas = [[4, 2, 1]] * 2 + [[1, 0.5, 0]]
	functional_registration.inputs.sigma_units = ['vox'] * 3
	functional_registration.inputs.shrink_factors = [[3, 2, 1]]*2 + [[4, 2, 1]]
	functional_registration.inputs.use_estimate_learning_rate_once = [True] * 3
	functional_registration.inputs.use_histogram_matching = [False] * 2 + [True]
	functional_registration.inputs.winsorize_lower_quantile = 0.005
	functional_registration.inputs.winsorize_upper_quantile = 0.995
	functional_registration.inputs.args = '--float'
	functional_registration.inputs.output_warped_image = 'output_warped_image.nii.gz'
	functional_registration.inputs.num_threads = 4
	functional_registration.plugin_args = {'qsub_args': '-pe orte 4', 'sbatch_args': '--mem=6G -c 4'}

	functional_warp = pe.Node(ants.ApplyTransforms(),name='functional_warp')
	functional_warp.inputs.reference_image = "/home/chymera/NIdata/templates/QBI_atlas100RD.nii.gz"
	functional_warp.inputs.input_image_type = 3
	functional_warp.inputs.interpolation = 'Linear'
	functional_warp.inputs.invert_transform_flags = [False]
	functional_warp.inputs.terminal_output = 'file'
	functional_warp.num_threads = 4

	functional_FAST = pe.Node(interface=FAST(), name="functional_FAST")
	functional_FAST.inputs.segments = False
	functional_FAST.inputs.output_biascorrected = True
	functional_FAST.inputs.bias_iters = 8

	functional_cutoff = pe.Node(interface=ImageMaths(), name="functional_cutoff")
	functional_cutoff.inputs.op_string = "-thrP 45"

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	datasink = pe.Node(nio.DataSink(), name='sinker')
	datasink.inputs.base_directory = workflow_base+"/"+workflow_denominator+"_results"

	#SET UP ANALYSIS WORKFLOW:
	analysis_workflow = pe.Workflow(name="GLM")

	analysis_workflow.connect([
		(structural_cutoff, structural_BET, [('out_file', 'in_file')]),
		(realigner, structural_warp, [('out_file', 'input_image')]),
		(structural_BET, structural_registration, [('out_file', 'moving_image')]),
		(structural_registration, structural_warp, [('composite_transform', 'transforms')]),
		(meaner, functional_FAST, [('out_file', 'in_file')]),
		(functional_FAST, functional_cutoff, [('restored_image', 'in_file')]),
		(functional_cutoff, functional_BET, [('out_file', 'in_file')]),
		(functional_BET, functional_registration, [('out_file', 'moving_image')]),
		(functional_registration, functional_warp, [('composite_transform', 'transforms')]),
		])
		# (functional_masker, functional_warp, [('out_file', 'input_image')]),
		# (functional_registration, functional_warp, [('composite_transform', 'transforms')]),
		# (functional_masker, structural_warp, [('out_file', 'input_image')]),
		# (functional_BET, functional_masker, [('mask_file', 'mask_file')]),
		# (realigner, functional_masker, [('out_file', 'in_file')]),
		# (realigner, meaner, [('out_file', 'in_file')]),
		# (warpall, melodic, [('output_image', 'in_files')]),
		# (melodic, datasink, [('report_dir', 'MELODIC_reports')])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([
		(bru2_preproc_workflow, analysis_workflow, [('realign.out_file','structural_warp.input_image')]),
		(bru2_preproc_workflow, analysis_workflow, [('realign.out_file','functional_warp.input_image')]),
		(bru2_preproc_workflow, analysis_workflow, [('realign.out_file','meaner.input_image')]),
		(bru2_preproc_workflow, analysis_workflow, [('structural_FAST.restored_image','structural_cutoff.in_file')])
		])

	pipeline.write_graph(graph2use="flat")
	pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})

if __name__ == "__main__":
	fsl_glm(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", structural_scan_type="T2_TurboRARE>", experiment_type="<ofM>", omit_ID=["20151026_135856_4006_1_1", "20151027_121613_4013_ofM_1_1","20151102_131136_4004_1_2","20151102_151940_4005_1_1","20151103_115031_4007_1_1","20151103_144306_4008_1_1","20151103_163137_4009_1_1","20151103_231827_4002_1_1"])
