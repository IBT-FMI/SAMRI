import nipype.pipeline.engine as pe				# pypeline engine
import nipype.interfaces.ants as ants

def structural_registration(template, num_threads=4):
	registration = pe.Node(ants.Registration(), name="s_register")
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

	f_warp = pe.Node(ants.ApplyTransforms(), name="f_warp")
	f_warp.inputs.reference_image = template
	f_warp.inputs.input_image_type = 3
	f_warp.inputs.interpolation = 'Linear'
	f_warp.inputs.invert_transform_flags = [False]
	f_warp.inputs.terminal_output = 'file'
	f_warp.num_threads = num_threads

	s_warp = pe.Node(ants.ApplyTransforms(), name="s_warp")
	s_warp.inputs.reference_image = template
	s_warp.inputs.input_image_type = 3
	s_warp.inputs.interpolation = 'Linear'
	s_warp.inputs.invert_transform_flags = [False]
	s_warp.inputs.terminal_output = 'file'
	s_warp.num_threads = num_threads

	return registration, s_warp, f_warp

def composite_registration(template, num_threads=4):
	f_registration = pe.Node(ants.Registration(), name="f_register")
	f_registration.inputs.output_transform_prefix = "output_"
	f_registration.inputs.transforms = ['Rigid']
	f_registration.inputs.transform_parameters = [(0.1,)]
	f_registration.inputs.number_of_iterations = [[40, 20, 10]]
	f_registration.inputs.dimension = 3
	f_registration.inputs.write_composite_transform = True
	f_registration.inputs.collapse_output_transforms = True
	f_registration.inputs.initial_moving_transform_com = True
	f_registration.inputs.metric = ['MeanSquares']
	f_registration.inputs.metric_weight = [1]
	f_registration.inputs.radius_or_number_of_bins = [16]
	f_registration.inputs.sampling_strategy = ["Regular"]
	f_registration.inputs.sampling_percentage = [0.3]
	f_registration.inputs.convergence_threshold = [1.e-2]
	f_registration.inputs.convergence_window_size = [8]
	f_registration.inputs.smoothing_sigmas = [[4, 2, 1]] #
	f_registration.inputs.sigma_units = ['vox']
	f_registration.inputs.shrink_factors = [[3, 2, 1]]
	f_registration.inputs.use_estimate_learning_rate_once = [True]
	f_registration.inputs.use_histogram_matching = [False]
	f_registration.inputs.winsorize_lower_quantile = 0.005
	f_registration.inputs.winsorize_upper_quantile = 0.995
	f_registration.inputs.args = '--float'
	f_registration.inputs.num_threads = num_threads

	f_warp = pe.Node(ants.ApplyTransforms(), name="f_warp")
	f_warp.inputs.reference_image = template
	f_warp.inputs.input_image_type = 3
	f_warp.inputs.interpolation = 'Linear'
	f_warp.inputs.invert_transform_flags = [False, False]
	f_warp.inputs.terminal_output = 'file'
	f_warp.num_threads = num_threads

	return f_registration, f_warp

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

	return registration, warp
