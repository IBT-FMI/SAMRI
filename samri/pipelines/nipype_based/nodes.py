import nipype.pipeline.engine as pe				# pypeline engine
import nipype.interfaces.ants as ants
from copy import deepcopy

def sturctural_registration(template, num_threads=4):
	registration = pe.Node(ants.Registration(), name="register")
	registration.inputs.fixed_image = template
	registration.inputs.output_transform_prefix = "output_"
	registration.inputs.transforms = ['Affine', 'SyN'] ##
	registration.inputs.transform_parameters = [(1.0,), (1.0, 3.0, 5.0)] ##
	registration.inputs.number_of_iterations = [[2000, 1000, 500], [100, 100, 100]] #
	registration.inputs.dimension = 3
	registration.inputs.write_composite_transform = True
	registration.inputs.collapse_output_transforms = True
	registration.inputs.initial_moving_transform_com = True
	# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on; MI and MeanSquares seem equally good
	registration.inputs.metric = ['MeanSquares', 'Mattes']
	registration.inputs.metric_weight = [1, 1]
	registration.inputs.radius_or_number_of_bins = [16, 32] #
	registration.inputs.sampling_strategy = ['Random', None]
	registration.inputs.sampling_percentage = [0.3, 0.3]
	registration.inputs.convergence_threshold = [1.e-11, 1.e-8] #
	registration.inputs.convergence_window_size = [20, 20]
	registration.inputs.smoothing_sigmas = [[4, 2, 1], [4, 2, 1]]
	registration.inputs.sigma_units = ['vox', 'vox']
	registration.inputs.shrink_factors = [[3, 2, 1],[3, 2, 1]]
	registration.inputs.use_estimate_learning_rate_once = [True, True]
	# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
	registration.inputs.use_histogram_matching = [False, False]
	registration.inputs.winsorize_lower_quantile = 0.005
	registration.inputs.winsorize_upper_quantile = 0.995
	registration.inputs.args = '--float'
	registration.inputs.num_threads = num_threads

	func_warp = pe.Node(ants.ApplyTransforms(), name="f_warp")
	func_warp.inputs.reference_image = template
	func_warp.inputs.input_image_type = 3
	func_warp.inputs.interpolation = 'Linear'
	func_warp.inputs.invert_transform_flags = [False]
	func_warp.inputs.terminal_output = 'file'
	func_warp.num_threads = num_threads

	struct_warp = pe.Node(ants.ApplyTransforms(), name="s_warp")
	struct_warp.inputs.reference_image = template
	struct_warp.inputs.input_image_type = 3
	struct_warp.inputs.interpolation = 'Linear'
	struct_warp.inputs.invert_transform_flags = [False]
	struct_warp.inputs.terminal_output = 'file'
	struct_warp.num_threads = num_threads

	return registration, struct_warp, func_warp

def functional_registration(template):
	registration = pe.Node(ants.Registration(), name="register")
	registration.inputs.fixed_image = template
	registration.inputs.output_transform_prefix = "output_"
	registration.inputs.transforms = ['Affine', 'SyN']
	registration.inputs.transform_parameters = [(0.1,), (3.0, 3.0, 5.0)]
	registration.inputs.number_of_iterations = [[10000, 10000, 10000], [100, 100, 100]]
	registration.inputs.dimension = 3
	registration.inputs.write_composite_transform = True
	registration.inputs.collapse_output_transforms = True
	registration.inputs.initial_moving_transform_com = True
	registration.inputs.metric = ['Mattes'] * 2 + [['Mattes', 'CC']]
	registration.inputs.metric_weight = [1] * 2 + [[0.5, 0.5]]
	registration.inputs.radius_or_number_of_bins = [32] * 2 + [[32, 4]]
	registration.inputs.sampling_strategy = ['Regular'] * 2 + [[None, None]]
	registration.inputs.sampling_percentage = [0.3] * 2 + [[None, None]]
	registration.inputs.convergence_threshold = [1.e-8] * 2 + [-0.01]
	registration.inputs.convergence_window_size = [20] * 2 + [5]
	registration.inputs.smoothing_sigmas = [[4, 2, 1]] * 2 + [[1, 0.5, 0]]
	registration.inputs.sigma_units = ['vox'] * 3
	registration.inputs.shrink_factors = [[3, 2, 1]]*2 + [[4, 2, 1]]
	registration.inputs.use_estimate_learning_rate_once = [True] * 3
	registration.inputs.use_histogram_matching = [False] * 2 + [True]
	registration.inputs.winsorize_lower_quantile = 0.005
	registration.inputs.winsorize_upper_quantile = 0.995
	registration.inputs.args = '--float'
	registration.inputs.output_warped_image = 'output_warped_image.nii.gz'
	registration.inputs.num_threads = 4
	registration.plugin_args = {'qsub_args': '-pe orte 4', 'sbatch_args': '--mem=6G -c 4'}

	warp = pe.Node(ants.ApplyTransforms(), name="f_warp")
	warp.inputs.reference_image = template
	warp.inputs.input_image_type = 3
	warp.inputs.interpolation = 'Linear'
	warp.inputs.invert_transform_flags = [False]
	warp.inputs.terminal_output = 'file'
	warp.num_threads = 4

	return registration, func_warp
