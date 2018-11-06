import nipype.interfaces.ants as ants
import os
import re
from samri.pipelines.utils import TRANSFORM_PHASES
from samri.pipelines.nodes import autorotate

from samri.utilities import iter_collapse_by_path

def collapse_nifti(in_dir, out_dir,
	**kwargs):
	in_dir = os.path.abspath(os.path.expanduser(in_dir))
	out_dir = os.path.abspath(os.path.expanduser(out_dir))
	in_files = []
	for root, dirs, files in os.walk(in_dir):
		_in_files = [os.path.join(root,f) for f in files]
		_in_files = [i for i in _in_files if os.path.isfile(i)]
		# Only NIfTI files:
		_in_files = [i for i in _in_files if '.nii' in i]
		in_files.extend(_in_files)
	# Make relative to `in_dir`:
	out_files = [re.sub(r'^' + re.escape(in_dir), '', i) for i in in_files]
	out_files = [os.path.join(out_dir,i[1:]) for i in out_files]
	out_files = iter_collapse_by_path(in_files, out_files,
		**kwargs
		)

def transform_feature(feature, source_reference, target_reference,
	target_mask='',
	phase_dictionary=TRANSFORM_PHASES,
	phases=['rigid','affine','syn'],
	num_threads=4,
	output_name='transformed_feature.nii.gz',
	interpolation='NearestNeighbor',
	debug=False,
	):
	"""
	Transform a NIfTI brain volume from a source reference space to a target reference space.
	"""

	target_reference = os.path.abspath(os.path.expanduser(target_reference))
	feature = os.path.abspath(os.path.expanduser(feature))
	source_reference = os.path.abspath(os.path.expanduser(source_reference))
	if target_mask:
		target_mask = os.path.abspath(os.path.expanduser(target_mask))

	# This is unreliable and should be replaced with antsAI once an interface is available in nipype.
	init = ants.AffineInitializer()
	init.inputs.fixed_image = target_reference
	init.inputs.moving_image = source_reference
	init.inputs.out_file = 'initialization.h5'
	init.inputs.local_search = 50
	init.inputs.principal_axes = False
	init.inputs.search_factor = 180
	init_res = init.run()

	init_warp = ants.ApplyTransforms()
	init_warp.inputs.reference_image = target_reference
	init_warp.inputs.input_image_type = 3
	init_warp.inputs.interpolation = interpolation
	init_warp.inputs.invert_transform_flags = [False]
	init_warp.inputs.output_image = 'initialized.nii.gz'
	init_warp.inputs.input_image = source_reference
	init_warp.inputs.transforms = init_res.outputs.out_file
	init_warp.num_threads = num_threads
	init_warp_res = init_warp.run()

	s_parameters = [phase_dictionary[selection] for selection in phases]

	registration = ants.Registration()
	registration.inputs.fixed_image = target_reference
	registration.inputs.output_transform_prefix = "output_"
	registration.inputs.transforms = [i["transforms"] for i in s_parameters] ##
	registration.inputs.transform_parameters = [i["transform_parameters"] for i in s_parameters] ##
	registration.inputs.number_of_iterations = [i["number_of_iterations"] for i in s_parameters] #
	registration.inputs.dimension = 3
	registration.inputs.write_composite_transform = True
	registration.inputs.collapse_output_transforms = True
	registration.inputs.initial_moving_transform_com = 1
	registration.inputs.metric = [i["metric"] for i in s_parameters]
	registration.inputs.metric_weight = [i["metric_weight"] for i in s_parameters]
	registration.inputs.radius_or_number_of_bins = [i["radius_or_number_of_bins"] for i in s_parameters]
	registration.inputs.sampling_strategy = [i["sampling_strategy"] for i in s_parameters]
	registration.inputs.sampling_percentage = [i["sampling_percentage"] for i in s_parameters]
	registration.inputs.convergence_threshold = [i["convergence_threshold"] for i in s_parameters]
	registration.inputs.convergence_window_size = [i["convergence_window_size"] for i in s_parameters]
	registration.inputs.smoothing_sigmas = [i["smoothing_sigmas"] for i in s_parameters]
	registration.inputs.sigma_units = [i["sigma_units"] for i in s_parameters]
	registration.inputs.shrink_factors = [i["shrink_factors"] for i in s_parameters]
	registration.inputs.use_estimate_learning_rate_once = [i["use_estimate_learning_rate_once"] for i in s_parameters]
	registration.inputs.use_histogram_matching = [i["use_histogram_matching"] for i in s_parameters]
	registration.inputs.winsorize_lower_quantile = 0.05
	registration.inputs.winsorize_upper_quantile = 0.95
	registration.inputs.args = '--float'
	if target_mask:
		registration.inputs.fixed_image_masks = target_mask
	registration.inputs.num_threads = num_threads
	registration.inputs.moving_image = init_warp_res.outputs.output_image
	registration.inputs.output_warped_image = 'warped.nii.gz'
	registration_res = registration.run()

	warp = ants.ApplyTransforms()
	warp.inputs.reference_image = target_reference
	warp.inputs.input_image_type = 3
	warp.inputs.interpolation = interpolation
	warp.inputs.invert_transform_flags = [False, False]
	warp.inputs.output_image = output_name
	warp.inputs.input_image = feature
	warp.inputs.transforms = [registration_res.outputs.composite_transform, init_res.outputs.out_file]
	warp.num_threads = num_threads
	warp_res = warp.run()

	if not debug:
		os.remove(init_warp_res.outputs.output_image)
		os.remove(init_res.outputs.out_file)
		os.remove(registration_res.outputs.inverse_composite_transform)
		os.remove(registration_res.outputs.composite_transform)
