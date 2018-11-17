from os import path

import nipype.pipeline.engine as pe				# pypeline engine
import nipype.interfaces.ants as ants
from nipype.interfaces import fsl
from samri.pipelines.utils import GENERIC_PHASES

def autorotate(template,
	in_file='structural.nii',
	):
	flt = fsl.FLIRT(bins=640, cost_func='mutualinfo')
	flt.inputs.in_file = in_file
	flt.inputs.reference = template
	flt.inputs.output_type = "NIFTI_GZ"
	flt.inputs.dof = 6
	flt.input.searchr_x = [-180,180]
	flt.input.searchr_y = [-180,180]
	flt.input.searchr_z = [-180,180]
	flt.input.force_scaling = True
	flt.cmdline
	flt_res = flt.run()
	return flt_res

def structural_registration(template, num_threads=4):
	registration = pe.Node(ants.Registration(), name="s_register")
	registration.inputs.fixed_image = path.abspath(path.expanduser(template))
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
	f_warp.inputs.reference_image = path.abspath(path.expanduser(template))
	f_warp.inputs.input_image_type = 3
	f_warp.inputs.interpolation = 'NearestNeighbor'
	f_warp.inputs.invert_transform_flags = [False]
	f_warp.inputs.terminal_output = 'file'
	f_warp.num_threads = num_threads

	s_warp = pe.Node(ants.ApplyTransforms(), name="s_warp")
	s_warp.inputs.reference_image = path.abspath(path.expanduser(template))
	s_warp.inputs.input_image_type = 3
	s_warp.inputs.interpolation = 'NearestNeighbor'
	s_warp.inputs.invert_transform_flags = [False]
	s_warp.inputs.terminal_output = 'file'
	s_warp.num_threads = num_threads

	return registration, s_warp, f_warp

def DSURQEc_structural_registration(template,
	structural_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	functional_mask='',
	num_threads=4,
	phase_dictionary=GENERIC_PHASES,
	s_phases=["s_rigid","affine","syn"],
	f_phases=["f_rigid",],
	parameters=None,
	):

	s_parameters = [phase_dictionary[selection] for selection in s_phases]

	s_registration = pe.Node(ants.Registration(), name="s_register")
	s_registration.inputs.fixed_image = path.abspath(path.expanduser(template))
	s_registration.inputs.output_transform_prefix = "output_"
	s_registration.inputs.transforms = [i["transforms"] for i in s_parameters] ##
	s_registration.inputs.transform_parameters = [i["transform_parameters"] for i in s_parameters] ##
	s_registration.inputs.number_of_iterations = [i["number_of_iterations"] for i in s_parameters] #
	s_registration.inputs.dimension = 3
	s_registration.inputs.write_composite_transform = True
	s_registration.inputs.collapse_output_transforms = True
	s_registration.inputs.initial_moving_transform_com = True
	s_registration.inputs.metric = [i["metric"] for i in s_parameters]
	s_registration.inputs.metric_weight = [i["metric_weight"] for i in s_parameters]
	s_registration.inputs.radius_or_number_of_bins = [i["radius_or_number_of_bins"] for i in s_parameters]
	s_registration.inputs.sampling_strategy = [i["sampling_strategy"] for i in s_parameters]
	s_registration.inputs.sampling_percentage = [i["sampling_percentage"] for i in s_parameters]
	s_registration.inputs.convergence_threshold = [i["convergence_threshold"] for i in s_parameters]
	s_registration.inputs.convergence_window_size = [i["convergence_window_size"] for i in s_parameters]
	s_registration.inputs.smoothing_sigmas = [i["smoothing_sigmas"] for i in s_parameters]
	s_registration.inputs.sigma_units = [i["sigma_units"] for i in s_parameters]
	s_registration.inputs.shrink_factors = [i["shrink_factors"] for i in s_parameters]
	s_registration.inputs.use_estimate_learning_rate_once = [i["use_estimate_learning_rate_once"] for i in s_parameters]
	s_registration.inputs.use_histogram_matching = [i["use_histogram_matching"] for i in s_parameters]
	s_registration.inputs.winsorize_lower_quantile = 0.05
	s_registration.inputs.winsorize_upper_quantile = 0.95
	s_registration.inputs.args = '--float'
	if structural_mask:
		s_registration.inputs.fixed_image_masks = [path.abspath(path.expanduser(structural_mask))]
	s_registration.inputs.num_threads = num_threads

	f_parameters = [phase_dictionary[selection] for selection in f_phases]

	f_registration = pe.Node(ants.Registration(), name="f_register")
	f_registration.inputs.fixed_image = path.abspath(path.expanduser(template))
	f_registration.inputs.output_transform_prefix = "output_"
	f_registration.inputs.transforms = [i["transforms"] for i in f_parameters] ##
	f_registration.inputs.transform_parameters = [i["transform_parameters"] for i in f_parameters] ##
	f_registration.inputs.number_of_iterations = [i["number_of_iterations"] for i in f_parameters] #
	f_registration.inputs.dimension = 3
	f_registration.inputs.write_composite_transform = True
	f_registration.inputs.collapse_output_transforms = True
	f_registration.inputs.initial_moving_transform_com = True
	f_registration.inputs.metric = [i["metric"] for i in f_parameters]
	f_registration.inputs.metric_weight = [i["metric_weight"] for i in f_parameters]
	f_registration.inputs.radius_or_number_of_bins = [i["radius_or_number_of_bins"] for i in f_parameters]
	f_registration.inputs.sampling_strategy = [i["sampling_strategy"] for i in f_parameters]
	f_registration.inputs.sampling_percentage = [i["sampling_percentage"] for i in f_parameters]
	f_registration.inputs.convergence_threshold = [i["convergence_threshold"] for i in f_parameters]
	f_registration.inputs.convergence_window_size = [i["convergence_window_size"] for i in f_parameters]
	f_registration.inputs.smoothing_sigmas = [i["smoothing_sigmas"] for i in f_parameters]
	f_registration.inputs.sigma_units = [i["sigma_units"] for i in f_parameters]
	f_registration.inputs.shrink_factors = [i["shrink_factors"] for i in f_parameters]
	f_registration.inputs.use_estimate_learning_rate_once = [i["use_estimate_learning_rate_once"] for i in f_parameters]
	f_registration.inputs.use_histogram_matching = [i["use_histogram_matching"] for i in f_parameters]
	f_registration.inputs.winsorize_lower_quantile = 0.05
	f_registration.inputs.winsorize_upper_quantile = 0.95
	f_registration.inputs.args = '--float'
	if functional_mask:
		f_registration.inputs.fixed_image_masks = [path.abspath(path.expanduser(functional_mask))]
	f_registration.inputs.num_threads = num_threads


	#f_warp = pe.Node(ants.WarpTimeSeriesImageMultiTransform(), name='f_warp')
	#f_warp.inputs.reference_image = template
	#f_warp.inputs.dimension = 4
	f_warp = pe.Node(ants.ApplyTransforms(), name="f_warp")
	f_warp.inputs.reference_image = path.abspath(path.expanduser(template))
	f_warp.inputs.input_image_type = 3
	f_warp.inputs.interpolation = 'BSpline'
	f_warp.inputs.interpolation_parameters = (5,)
	f_warp.inputs.invert_transform_flags = [False, False]
	#DEPRECATED in =nipype-1.1.0
	#f_warp.inputs.terminal_output = 'file'
	f_warp.num_threads = num_threads
	f_warp.interface.mem_gb = 12

	s_warp = pe.Node(ants.ApplyTransforms(), name="s_warp")
	s_warp.inputs.reference_image = path.abspath(path.expanduser(template))
	s_warp.inputs.input_image_type = 0
	s_warp.inputs.interpolation = 'BSpline'
	s_warp.inputs.interpolation_parameters = (5,)
	s_warp.inputs.invert_transform_flags = [False]
	#DEPRECATED in =nipype-1.1.0
	#s_warp.inputs.terminal_output = 'file'
	s_warp.num_threads = num_threads

	return s_registration, s_warp, f_registration, f_warp

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
	f_warp.inputs.reference_image = path.abspath(path.expanduser(template))
	f_warp.inputs.input_image_type = 3
	f_warp.inputs.interpolation = 'NearestNeighbor'
	f_warp.inputs.invert_transform_flags = [False, False]
	f_warp.inputs.terminal_output = 'file'
	f_warp.num_threads = num_threads

	return f_registration, f_warp

def functional_registration(template,
	mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	num_threads=4,
	phase_dictionary=GENERIC_PHASES,
	f_phases=["s_rigid","affine","syn"],
	):

	template = path.abspath(path.expanduser(template))

	f_parameters = [phase_dictionary[selection] for selection in f_phases]

	f_registration = pe.Node(ants.Registration(), name="f_register")
	f_registration.inputs.fixed_image = template
	f_registration.inputs.output_transform_prefix = "output_"
	f_registration.inputs.transforms = [i["transforms"] for i in f_parameters] ##
	f_registration.inputs.transform_parameters = [i["transform_parameters"] for i in f_parameters] ##
	f_registration.inputs.number_of_iterations = [i["number_of_iterations"] for i in f_parameters] #
	f_registration.inputs.dimension = 3
	f_registration.inputs.write_composite_transform = True
	f_registration.inputs.collapse_output_transforms = True
	f_registration.inputs.initial_moving_transform_com = True
	f_registration.inputs.metric = [i["metric"] for i in f_parameters]
	f_registration.inputs.metric_weight = [i["metric_weight"] for i in f_parameters]
	f_registration.inputs.radius_or_number_of_bins = [i["radius_or_number_of_bins"] for i in f_parameters]
	f_registration.inputs.sampling_strategy = [i["sampling_strategy"] for i in f_parameters]
	f_registration.inputs.sampling_percentage = [i["sampling_percentage"] for i in f_parameters]
	f_registration.inputs.convergence_threshold = [i["convergence_threshold"] for i in f_parameters]
	f_registration.inputs.convergence_window_size = [i["convergence_window_size"] for i in f_parameters]
	f_registration.inputs.smoothing_sigmas = [i["smoothing_sigmas"] for i in f_parameters]
	f_registration.inputs.sigma_units = [i["sigma_units"] for i in f_parameters]
	f_registration.inputs.shrink_factors = [i["shrink_factors"] for i in f_parameters]
	f_registration.inputs.use_estimate_learning_rate_once = [i["use_estimate_learning_rate_once"] for i in f_parameters]
	f_registration.inputs.use_histogram_matching = [i["use_histogram_matching"] for i in f_parameters]
	f_registration.inputs.winsorize_lower_quantile = 0.05
	f_registration.inputs.winsorize_upper_quantile = 0.95
	f_registration.inputs.args = '--float'
	if mask:
		f_registration.inputs.fixed_image_masks = [path.abspath(path.expanduser(mask))]
	f_registration.inputs.num_threads = num_threads

	warp = pe.Node(ants.ApplyTransforms(), name="f_warp")
	warp.inputs.reference_image = template
	warp.inputs.input_image_type = 3
	warp.inputs.interpolation = 'NearestNeighbor'
	warp.inputs.invert_transform_flags = [False]
	warp.inputs.terminal_output = 'file'
	warp.num_threads = 4

	return f_registration, warp

def real_size_nodes():
	s_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="s_biascorrect")
	s_biascorrect.inputs.dimension = 3
	s_biascorrect.inputs.bspline_fitting_distance = 10
	s_biascorrect.inputs.bspline_order = 4
	s_biascorrect.inputs.shrink_factor = 2
	s_biascorrect.inputs.n_iterations = [150,100,50,30]
	s_biascorrect.inputs.convergence_threshold = 1e-16

	f_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="f_biascorrect")
	f_biascorrect.inputs.dimension = 3
	f_biascorrect.inputs.bspline_fitting_distance = 10
	f_biascorrect.inputs.bspline_order = 4
	f_biascorrect.inputs.shrink_factor = 2
	f_biascorrect.inputs.n_iterations = [150,100,50,30]
	f_biascorrect.inputs.convergence_threshold = 1e-11

	return s_biascorrect, f_biascorrect

def inflated_size_nodes():
	s_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="s_biascorrect")
	s_biascorrect.inputs.dimension = 3
	s_biascorrect.inputs.bspline_fitting_distance = 100
	s_biascorrect.inputs.shrink_factor = 2
	s_biascorrect.inputs.n_iterations = [200,200,200,200]
	s_biascorrect.inputs.convergence_threshold = 1e-11

	f_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="f_biascorrect")
	f_biascorrect.inputs.dimension = 3
	f_biascorrect.inputs.bspline_fitting_distance = 100
	f_biascorrect.inputs.shrink_factor = 2
	f_biascorrect.inputs.n_iterations = [200,200,200,200]
	f_biascorrect.inputs.convergence_threshold = 1e-11

	return s_biascorrect, f_biascorrect
