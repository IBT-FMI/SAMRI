import nipype.interfaces.ants as ants
import os
from nipype.interfaces.fsl import ApplyMask, GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ImageMaths, FSLCommand
from nipype.interfaces import fsl

try:
	FileNotFoundError
except NameError:
	FileNotFoundError = IOError

def structural_rigid_affine(template="/Users/marksm/GitHub/mriPipeline/ants_test/template4.nii.gz",
	input_image = "/Users/marksm/GitHub/mriPipeline/ants_test/source_add.nii.gz",
	output_image = 'new_with_flirt.nii.gz',
	):
	"""
	Registers a structural scan to the reference template using rigid body transformation and an affine matrix.
	"""
		
	template = os.path.abspath(os.path.expanduser(template))
	input_image = os.path.abspath(os.path.expanduser(input_image))
	output_image = os.path.abspath(os.path.expanduser(output_image))

	n4 = ants.N4BiasFieldCorrection()
	n4.inputs.dimension = 3
	n4.inputs.input_image = input_image
	# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
	n4.inputs.bspline_fitting_distance = 10
	# n4.inputs.shrink_factor = 2
	n4.inputs.n_iterations = [200,200,200,200]
	n4.inputs.convergence_threshold = 1e-11
	# n4.inputs.output_image = 'ss_n4_{}_ofM{}.nii.gz'.format(participant,i)
	n4.inputs.output_image = 'hard_flirt.nii.gz'
	n4_res = n4.run()

	flt = fsl.FLIRT(cost_func='corratio', dof = 6, searchr_x = [-180,180], searchr_y = [-180,180], searchr_z = [-180,180], force_scaling = True)
	flt.inputs.in_file = n4_res.outputs.output_image
	flt.inputs.reference = template
	flt.inputs.out_file = 'after_flirt.nii.gz'
	flt.inputs.out_matrix_file = 'subject_to_template.mat'
	flt_res = flt.run()

	struct_registration = ants.Registration()
	struct_registration.inputs.fixed_image = template
	struct_registration.inputs.output_transform_prefix = "output_"
	struct_registration.inputs.transforms = ['Similarity','Affine'] ##
	struct_registration.inputs.transform_parameters = [(5.,),(0.2,)] ##
	struct_registration.inputs.number_of_iterations = [[1000,1000,200], [5000, 2500, 1000]] #
	struct_registration.inputs.dimension = 3
	struct_registration.inputs.write_composite_transform = True
	struct_registration.inputs.collapse_output_transforms = True
	struct_registration.inputs.initial_moving_transform_com = True
	# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
	struct_registration.inputs.metric = ['MI', 'MI']
	struct_registration.inputs.metric_weight = [1, 1]
	struct_registration.inputs.radius_or_number_of_bins = [10, 10] #
	struct_registration.inputs.sampling_strategy = ['Random','Random']
	struct_registration.inputs.sampling_percentage = [0.3, 0.3]
	struct_registration.inputs.convergence_threshold = [1.e-16, 1.e-18] #
	struct_registration.inputs.convergence_window_size = [10, 10]
	struct_registration.inputs.smoothing_sigmas = [[4, 2, 1], [4, 2, 1]]
	struct_registration.inputs.sigma_units = ['vox', 'vox']
	struct_registration.inputs.shrink_factors = [[4, 2, 1],[3, 2, 1]]
	struct_registration.inputs.use_estimate_learning_rate_once = [True, True]
	# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
	struct_registration.inputs.use_histogram_matching = [False, False]
	struct_registration.inputs.winsorize_lower_quantile = 0.005
	struct_registration.inputs.winsorize_upper_quantile = 0.98
	struct_registration.inputs.args = '--float'
	struct_registration.inputs.num_threads = 6

	struct_registration.inputs.moving_image = flt_res.outputs.out_file
	# struct_registration.inputs.output_warped_image = 'ss_{}_ofM{}.nii.gz'.format(participant,i)
	struct_registration.inputs.output_warped_image = output_image
	res = struct_registration.run()

def structural_rigid_flirt_nonlin_syn(template="/Users/marksm/GitHub/mriPipeline/ants_test/template4.nii.gz",
	input_image = "/Users/marksm/GitHub/mriPipeline/ants_test/source_add.nii.gz",
	output_image = 'final_test.nii.gz',
	):

	"""Experimental Registration. Performs Rigid body transformation using FSL's FLIRT,
	including transformations of the coordinate systems. Subsequently ANTs' SyN performes
	the non-linear part of the Registration process.
	"""

	template = os.path.abspath(os.path.expanduser(template))
	input_image = os.path.abspath(os.path.expanduser(input_image))
	output_image = os.path.abspath(os.path.expanduser(output_image))

	n4 = ants.N4BiasFieldCorrection()
	n4.inputs.dimension = 3
	n4.inputs.input_image = input_image
	# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
	n4.inputs.bspline_fitting_distance = 10
	# n4.inputs.shrink_factor = 2
	n4.inputs.n_iterations = [200,200,200,200]
	n4.inputs.convergence_threshold = 1e-11
	# n4.inputs.output_image = 'ss_n4_{}_ofM{}.nii.gz'.format(participant,i)
	n4.inputs.output_image = 'hard_flirt.nii.gz'
	n4_res = n4.run()

	flt = fsl.FLIRT(cost_func='corratio', dof = 6, searchr_x = [-180,180], searchr_y = [-180,180], searchr_z = [-180,180], force_scaling = True)
	flt.inputs.in_file = n4_res.outputs.output_image
	flt.inputs.reference = template
	flt.inputs.out_file = 'after_flirt.nii.gz'
	flt.inputs.out_matrix_file = 'subject_to_template.mat'
	flt_res = flt.run()

	struct_registration = ants.Registration()
	struct_registration.inputs.fixed_image = template
	struct_registration.inputs.output_transform_prefix = "output_"
	struct_registration.inputs.transforms = ['SyN'] ##
	struct_registration.inputs.transform_parameters = [(0.1, 3.0, 0.0)] ##
	struct_registration.inputs.number_of_iterations = [[2000, 1000, 500]] #
	struct_registration.inputs.dimension = 3
	struct_registration.inputs.write_composite_transform = True
	struct_registration.inputs.collapse_output_transforms = True
	struct_registration.inputs.initial_moving_transform_com = True
	# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
	struct_registration.inputs.metric = ['Mattes']
	struct_registration.inputs.metric_weight = [1]
	struct_registration.inputs.radius_or_number_of_bins = [8] #
	struct_registration.inputs.sampling_strategy = ['Random']
	struct_registration.inputs.sampling_percentage = [0.3]
	struct_registration.inputs.convergence_threshold = [1.e-10] #
	struct_registration.inputs.convergence_window_size = [4]
	struct_registration.inputs.smoothing_sigmas = [[4, 2, 1]]
	struct_registration.inputs.sigma_units = ['vox']
	struct_registration.inputs.shrink_factors = [[4, 2, 1]]
	struct_registration.inputs.use_estimate_learning_rate_once = [True]
	# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
	struct_registration.inputs.use_histogram_matching = [False,]
	struct_registration.inputs.winsorize_lower_quantile = 0.005
	struct_registration.inputs.winsorize_upper_quantile = 0.98
	struct_registration.inputs.args = '--float'
	struct_registration.inputs.num_threads = 6

	struct_registration.inputs.moving_image = flt_res.outputs.out_file
	# struct_registration.inputs.output_warped_image = 'ss_{}_ofM{}.nii.gz'.format(participant,i)
	struct_registration.inputs.output_warped_image = output_image
	res = struct_registration.run()

def structural_rigid(template="/Users/marksm/GitHub/mriPipeline/ants_test/template4.nii.gz",
	input_image = "/Users/marksm/GitHub/mriPipeline/ants_test/source.nii",
	output_image = 'hard2_new_32_rigid_affine_more_rigid_CC.nii.gz',
	):
	"""
	Registers a structural scan to the reference template using rigid body transformation. 
	"""

	template = os.path.abspath(os.path.expanduser(template))
	input_image = os.path.abspath(os.path.expanduser(input_image))
	output_image = os.path.abspath(os.path.expanduser(output_image))

	n4 = ants.N4BiasFieldCorrection()
	n4.inputs.dimension = 3
	n4.inputs.input_image = input_image
	# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
	n4.inputs.bspline_fitting_distance = 100
	n4.inputs.shrink_factor = 2
	n4.inputs.n_iterations = [200,200,200,200]
	n4.inputs.convergence_threshold = 1e-11
	# n4.inputs.output_image = 'ss_n4_{}_ofM{}.nii.gz'.format(participant,i)
	n4.inputs.output_image = 'hard.nii.gz'
	n4_res = n4.run()

	struct_registration = ants.Registration()
	struct_registration.inputs.fixed_image = template
	struct_registration.inputs.output_transform_prefix = "output_"
	struct_registration.inputs.transforms = ['Similarity'] ##
	struct_registration.inputs.transform_parameters = [(60.,),] ##
	struct_registration.inputs.number_of_iterations = [[1000,1000,200],] #
	struct_registration.inputs.dimension = 3
	struct_registration.inputs.write_composite_transform = True
	struct_registration.inputs.collapse_output_transforms = True
	struct_registration.inputs.initial_moving_transform_com = True
	# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
	struct_registration.inputs.metric = ['MI',]
	struct_registration.inputs.metric_weight = [1,]
	struct_registration.inputs.radius_or_number_of_bins = [10,] #
	struct_registration.inputs.sampling_strategy = ['Random',]
	struct_registration.inputs.sampling_percentage = [0.3,]
	struct_registration.inputs.convergence_threshold = [1.e-16,] #
	struct_registration.inputs.convergence_window_size = [10,]
	struct_registration.inputs.smoothing_sigmas = [[4, 2, 1],]
	struct_registration.inputs.sigma_units = ['vox',]
	struct_registration.inputs.shrink_factors = [[4, 2, 1],]
	struct_registration.inputs.use_estimate_learning_rate_once = [True,]
	# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
	struct_registration.inputs.use_histogram_matching = [False,]
	struct_registration.inputs.winsorize_lower_quantile = 0.005
	struct_registration.inputs.winsorize_upper_quantile = 0.98
	struct_registration.inputs.args = '--float'
	struct_registration.inputs.num_threads = 6

	struct_registration.inputs.moving_image = n4_res.outputs.output_image
	# struct_registration.inputs.output_warped_image = 'ss_{}_ofM{}.nii.gz'.format(participant,i)
	struct_registration.inputs.output_warped_image = output_image
	res = struct_registration.run()


def functional_per_participant_test():
	for i in ["","_aF","_cF1","_cF2","_pF"]:
		template = "~/ni_data/templates/ds_QBI_chr.nii.gz"
		participant = "4008"
		image_dir = "~/ni_data/ofM.dr/preprocessing/generic_work/_subject_session_{}.ofM{}/_scan_type_7_EPI_CBV/temporal_mean/".format(participant,i)
		try:
			for myfile in os.listdir(image_dir):
				if myfile.endswith(".nii.gz"):
					mimage = os.path.join(image_dir,myfile)
		except FileNotFoundError:
			pass
		else:
			n4 = ants.N4BiasFieldCorrection()
			n4.inputs.dimension = 3
			n4.inputs.input_image = mimage
			n4.inputs.bspline_fitting_distance = 100
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [200,200,200,200]
			n4.inputs.convergence_threshold = 1e-11
			n4.inputs.output_image = 'n4_{}_ofM{}.nii.gz'.format(participant,i)
			n4_res = n4.run()

			functional_cutoff = ImageMaths()
			functional_cutoff.inputs.op_string = "-thrP 30"
			functional_cutoff.inputs.in_file = n4_res.outputs.output_image
			functional_cutoff_res = functional_cutoff.run()

			functional_BET = BET()
			functional_BET.inputs.mask = True
			functional_BET.inputs.frac = 0.5
			functional_BET.inputs.in_file = functional_cutoff_res.outputs.out_file
			functional_BET_res = functional_BET.run()

			registration = ants.Registration()
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
			registration.inputs.num_threads = 4
			registration.plugin_args = {'qsub_args': '-pe orte 4', 'sbatch_args': '--mem=6G -c 4'}

			registration.inputs.moving_image = functional_BET_res.outputs.out_file
			registration.inputs.output_warped_image = '{}_ofM{}.nii.gz'.format(participant,i)
			res = registration.run()

def structural_to_functional_per_participant_test(subjects_sessions,
	template = "~/GitHub/mriPipeline/templates/waxholm/new/WHS_SD_masked.nii.gz",
	f_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_SE_EPI/f_bru2nii/",
	s_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_T2_TurboRARE/s_bru2nii/",
	num_threads = 3,
	):

	template = os.path.expanduser(template)
	for subject_session in subjects_sessions:
		func_image_dir = os.path.expanduser(f_file_format.format(**subject_session))
		struct_image_dir = os.path.expanduser(s_file_format.format(**subject_session))
		try:
			for myfile in os.listdir(func_image_dir):
				if myfile.endswith((".nii.gz", ".nii")):
					func_image = os.path.join(func_image_dir,myfile)
			for myfile in os.listdir(struct_image_dir):
				if myfile.endswith((".nii.gz", ".nii")):
					struct_image = os.path.join(struct_image_dir,myfile)
		except FileNotFoundError:
			pass
		else:
			n4 = ants.N4BiasFieldCorrection()
			n4.inputs.dimension = 3
			n4.inputs.input_image = struct_image
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			n4.inputs.bspline_fitting_distance = 100
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [200,200,200,200]
			n4.inputs.convergence_threshold = 1e-11
			n4.inputs.output_image = '{}_{}_1_biasCorrection_forRegistration.nii.gz'.format(*subject_session.values())
			n4_res = n4.run()

			_n4 = ants.N4BiasFieldCorrection()
			_n4.inputs.dimension = 3
			_n4.inputs.input_image = struct_image
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			_n4.inputs.bspline_fitting_distance = 95
			_n4.inputs.shrink_factor = 2
			_n4.inputs.n_iterations = [500,500,500,500]
			_n4.inputs.convergence_threshold = 1e-14
			_n4.inputs.output_image = '{}_{}_1_biasCorrection_forMasking.nii.gz'.format(*subject_session.values())
			_n4_res = _n4.run()

			#we do this on a separate bias-corrected image to remove hyperintensities which we have to create in order to prevent brain regions being caught by the negative threshold
			struct_cutoff = ImageMaths()
			struct_cutoff.inputs.op_string = "-thrP 20 -uthrp 98"
			struct_cutoff.inputs.in_file = _n4_res.outputs.output_image
			struct_cutoff_res = struct_cutoff.run()

			struct_BET = BET()
			struct_BET.inputs.mask = True
			struct_BET.inputs.frac = 0.3
			struct_BET.inputs.robust = True
			struct_BET.inputs.in_file = struct_cutoff_res.outputs.out_file
			struct_BET.inputs.out_file = '{}_{}_2_brainExtraction.nii.gz'.format(*subject_session.values())
			struct_BET_res = struct_BET.run()

			# we need/can not apply a fill, because the "holes" if any, will be at the rostral edge (touching it, and thus not counting as holes)
			struct_mask = ApplyMask()
			struct_mask.inputs.in_file = n4_res.outputs.output_image
			struct_mask.inputs.mask_file = struct_BET_res.outputs.mask_file
			struct_mask.inputs.out_file = '{}_{}_3_brainMasked.nii.gz'.format(*subject_session.values())
			struct_mask_res = struct_mask.run()

			struct_registration = ants.Registration()
			struct_registration.inputs.fixed_image = template
			struct_registration.inputs.output_transform_prefix = "output_"
			struct_registration.inputs.transforms = ['Affine', 'SyN'] ##
			struct_registration.inputs.transform_parameters = [(1.0,), (1.0, 3.0, 5.0)] ##
			struct_registration.inputs.number_of_iterations = [[2000, 1000, 500], [100, 100, 100]] #
			struct_registration.inputs.dimension = 3
			struct_registration.inputs.write_composite_transform = True
			struct_registration.inputs.collapse_output_transforms = True
			struct_registration.inputs.initial_moving_transform_com = True
			# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
			struct_registration.inputs.metric = ['MeanSquares', 'Mattes']
			struct_registration.inputs.metric_weight = [1, 1]
			struct_registration.inputs.radius_or_number_of_bins = [16, 32] #
			struct_registration.inputs.sampling_strategy = ['Random', None]
			struct_registration.inputs.sampling_percentage = [0.3, 0.3]
			struct_registration.inputs.convergence_threshold = [1.e-11, 1.e-8] #
			struct_registration.inputs.convergence_window_size = [20, 20]
			struct_registration.inputs.smoothing_sigmas = [[4, 2, 1], [4, 2, 1]]
			struct_registration.inputs.sigma_units = ['vox', 'vox']
			struct_registration.inputs.shrink_factors = [[3, 2, 1],[3, 2, 1]]
			struct_registration.inputs.use_estimate_learning_rate_once = [True, True]
			# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
			struct_registration.inputs.use_histogram_matching = [False, False]
			struct_registration.inputs.winsorize_lower_quantile = 0.005
			struct_registration.inputs.winsorize_upper_quantile = 0.98
			struct_registration.inputs.args = '--float'
			struct_registration.inputs.num_threads = num_threads

			struct_registration.inputs.moving_image = struct_mask_res.outputs.out_file
			struct_registration.inputs.output_warped_image = '{}_{}_4_structuralRegistration.nii.gz'.format(*subject_session.values())
			struct_registration_res = struct_registration.run()

			warp = ants.ApplyTransforms()
			warp.inputs.reference_image = template
			warp.inputs.input_image_type = 3
			warp.inputs.interpolation = 'Linear'
			warp.inputs.invert_transform_flags = [False]
			warp.inputs.terminal_output = 'file'
			warp.inputs.output_image = '{}_{}_5_functionalWarp.nii.gz'.format(*subject_session.values())
			warp.num_threads = num_threads

			warp.inputs.input_image = func_image
			warp.inputs.transforms = struct_registration_res.outputs.composite_transform
			warp.run()

def canonical_(subjects_participants,
	conditions=["","_aF","_cF1","_cF2","_pF"],
	template = "~/GitHub/mriPipeline/templates/waxholm/WHS_SD_rat_T2star_v1.01_downsample3.nii.gz",
	f_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_SE_EPI/f_bru2nii/",
	s_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_T2_TurboRARE/s_bru2nii/",
	):

	"""Warp a functional image based on the functional-to-structural and the structural-to-template registrations.
	Currently this approach is failing because the functiona-to-structural registration pushes the brain stem too far down.
	This may be

	"""
	template = os.path.expanduser(template)
	for subject_participant in subjects_participants:
		func_image_dir = os.path.expanduser(f_file_format.format(**subject_participant))
		struct_image_dir = os.path.expanduser(s_file_format.format(**subject_participant))
		try:
			for myfile in os.listdir(func_image_dir):
				if myfile.endswith((".nii.gz", ".nii")):
					func_image = os.path.join(func_image_dir,myfile)
			for myfile in os.listdir(struct_image_dir):
				if myfile.endswith((".nii.gz", ".nii")):
					struct_image = os.path.join(struct_image_dir,myfile)
		except FileNotFoundError:
			pass
		else:
			#struct
			n4 = ants.N4BiasFieldCorrection()
			n4.inputs.dimension = 3
			n4.inputs.input_image = struct_image
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			n4.inputs.bspline_fitting_distance = 100
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [200,200,200,200]
			n4.inputs.convergence_threshold = 1e-11
			n4.inputs.output_image = 'ss_n4_{}_ofM{}.nii.gz'.format(participant,i)
			n4_res = n4.run()

			_n4 = ants.N4BiasFieldCorrection()
			_n4.inputs.dimension = 3
			_n4.inputs.input_image = struct_image
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			_n4.inputs.bspline_fitting_distance = 95
			_n4.inputs.shrink_factor = 2
			_n4.inputs.n_iterations = [500,500,500,500]
			_n4.inputs.convergence_threshold = 1e-14
			_n4.inputs.output_image = 'ss__n4_{}_ofM{}.nii.gz'.format(participant,i)
			_n4_res = _n4.run()

			#we do this on a separate bias-corrected image to remove hyperintensities which we have to create in order to prevent brain regions being caught by the negative threshold
			struct_cutoff = ImageMaths()
			struct_cutoff.inputs.op_string = "-thrP 20 -uthrp 98"
			struct_cutoff.inputs.in_file = _n4_res.outputs.output_image
			struct_cutoff_res = struct_cutoff.run()

			struct_BET = BET()
			struct_BET.inputs.mask = True
			struct_BET.inputs.frac = 0.3
			struct_BET.inputs.robust = True
			struct_BET.inputs.in_file = struct_cutoff_res.outputs.out_file
			struct_BET_res = struct_BET.run()

			struct_mask = ApplyMask()
			struct_mask.inputs.in_file = n4_res.outputs.output_image
			struct_mask.inputs.mask_file = struct_BET_res.outputs.mask_file
			struct_mask_res = struct_mask.run()

			struct_registration = ants.Registration()
			struct_registration.inputs.fixed_image = template
			struct_registration.inputs.output_transform_prefix = "output_"
			struct_registration.inputs.transforms = ['Affine', 'SyN'] ##
			struct_registration.inputs.transform_parameters = [(1.0,), (1.0, 3.0, 5.0)] ##
			struct_registration.inputs.number_of_iterations = [[2000, 1000, 500], [100, 100, 100]] #
			struct_registration.inputs.dimension = 3
			struct_registration.inputs.write_composite_transform = True
			struct_registration.inputs.collapse_output_transforms = True
			struct_registration.inputs.initial_moving_transform_com = True
			# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
			struct_registration.inputs.metric = ['MeanSquares', 'Mattes']
			struct_registration.inputs.metric_weight = [1, 1]
			struct_registration.inputs.radius_or_number_of_bins = [16, 32] #
			struct_registration.inputs.sampling_strategy = ['Random', None]
			struct_registration.inputs.sampling_percentage = [0.3, 0.3]
			struct_registration.inputs.convergence_threshold = [1.e-11, 1.e-8] #
			struct_registration.inputs.convergence_window_size = [20, 20]
			struct_registration.inputs.smoothing_sigmas = [[4, 2, 1], [4, 2, 1]]
			struct_registration.inputs.sigma_units = ['vox', 'vox']
			struct_registration.inputs.shrink_factors = [[3, 2, 1],[3, 2, 1]]
			struct_registration.inputs.use_estimate_learning_rate_once = [True, True]
			# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
			struct_registration.inputs.use_histogram_matching = [False, False]
			struct_registration.inputs.winsorize_lower_quantile = 0.005
			struct_registration.inputs.winsorize_upper_quantile = 0.98
			struct_registration.inputs.args = '--float'
			struct_registration.inputs.num_threads = 6

			struct_registration.inputs.moving_image = struct_mask_res.outputs.out_file
			struct_registration.inputs.output_warped_image = 's_{}_ofM{}.nii.gz'.format(participant,i)
			struct_registration_res = struct_registration.run()

			#func
			func_n4 = ants.N4BiasFieldCorrection()
			func_n4.inputs.dimension = 3
			func_n4.inputs.input_image = func_image
			func_n4.inputs.bspline_fitting_distance = 100
			func_n4.inputs.shrink_factor = 2
			func_n4.inputs.n_iterations = [200,200,200,200]
			func_n4.inputs.convergence_threshold = 1e-11
			func_n4.inputs.output_image = 'f_n4_{}_ofM{}.nii.gz'.format(participant,i)
			func_n4_res = func_n4.run()

			func_registration = ants.Registration()
			func_registration.inputs.fixed_image = n4_res.outputs.output_image
			func_registration.inputs.output_transform_prefix = "func_"
			func_registration.inputs.transforms = ['Rigid']
			func_registration.inputs.transform_parameters = [(0.1,)]
			func_registration.inputs.number_of_iterations = [[40, 20, 10]]
			func_registration.inputs.dimension = 3
			func_registration.inputs.write_composite_transform = True
			func_registration.inputs.collapse_output_transforms = True
			func_registration.inputs.initial_moving_transform_com = True
			func_registration.inputs.metric = ['MeanSquares']
			func_registration.inputs.metric_weight = [1]
			func_registration.inputs.radius_or_number_of_bins = [16]
			func_registration.inputs.sampling_strategy = ["Regular"]
			func_registration.inputs.sampling_percentage = [0.3]
			func_registration.inputs.convergence_threshold = [1.e-2]
			func_registration.inputs.convergence_window_size = [8]
			func_registration.inputs.smoothing_sigmas = [[4, 2, 1]] # [1,0.5,0]
			func_registration.inputs.sigma_units = ['vox']
			func_registration.inputs.shrink_factors = [[3, 2, 1]]
			func_registration.inputs.use_estimate_learning_rate_once = [True]
			func_registration.inputs.use_histogram_matching = [False]
			func_registration.inputs.winsorize_lower_quantile = 0.005
			func_registration.inputs.winsorize_upper_quantile = 0.995
			func_registration.inputs.args = '--float'
			func_registration.inputs.num_threads = 6

			func_registration.inputs.moving_image = func_n4_res.outputs.output_image
			func_registration.inputs.output_warped_image = 'f_{}_ofM{}.nii.gz'.format(participant,i)
			func_registration_res = func_registration.run()

			warp = ants.ApplyTransforms()
			warp.inputs.reference_image = template
			warp.inputs.input_image_type = 3
			warp.inputs.interpolation = 'Linear'
			warp.inputs.invert_transform_flags = [False, False]
			warp.inputs.terminal_output = 'file'
			warp.inputs.output_image = '{}_ofM{}.nii.gz'.format(participant,i)
			warp.num_threads = 6

			warp.inputs.input_image = func_image
			warp.inputs.transforms = [func_registration_res.outputs.composite_transform, struct_registration_res.outputs.composite_transform]
			warp.run()


def canonical(subjects_participants, regdir, f2s,
	template = "~/GitHub/mriPipeline/templates/waxholm/WHS_SD_rat_T2star_v1.01_downsample3.nii.gz",
	f_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_SE_EPI/f_bru2nii/",
	s_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_T2_TurboRARE/s_bru2nii/",
	):

	"""Warp a functional image based on the functional-to-structural and the structural-to-template registrations.
	Currently this approach is failing because the functiona-to-structural registration pushes the brain stem too far down.
	This may be

	"""
	template = os.path.expanduser(template)
	for subject_participant in subjects_participants:
		func_image_dir = os.path.expanduser(f_file_format.format(**subject_participant))
		struct_image_dir = os.path.expanduser(s_file_format.format(**subject_participant))
		try:
			for myfile in os.listdir(func_image_dir):
				if myfile.endswith((".nii.gz", ".nii")):
					func_image = os.path.join(func_image_dir,myfile)
			for myfile in os.listdir(struct_image_dir):
				if myfile.endswith((".nii.gz", ".nii")):
					struct_image = os.path.join(struct_image_dir,myfile)
		except FileNotFoundError:
			pass
		else:
			#struct
			n4 = ants.N4BiasFieldCorrection()
			n4.inputs.dimension = 3
			n4.inputs.input_image = struct_image
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			n4.inputs.bspline_fitting_distance = 100
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [200,200,200,200]
			n4.inputs.convergence_threshold = 1e-11
			n4.inputs.output_image = '{}/ss_n4_{}_ofM{}.nii.gz'.format(regdir,participant,i)
			n4_res = n4.run()

			_n4 = ants.N4BiasFieldCorrection()
			_n4.inputs.dimension = 3
			_n4.inputs.input_image = struct_image
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			_n4.inputs.bspline_fitting_distance = 95
			_n4.inputs.shrink_factor = 2
			_n4.inputs.n_iterations = [500,500,500,500]
			_n4.inputs.convergence_threshold = 1e-14
			_n4.inputs.output_image = '{}/ss__n4_{}_ofM{}.nii.gz'.format(regdir,participant,i)
			_n4_res = _n4.run()

			#we do this on a separate bias-corrected image to remove hyperintensities which we have to create in order to prevent brain regions being caught by the negative threshold
			struct_cutoff = ImageMaths()
			struct_cutoff.inputs.op_string = "-thrP 20 -uthrp 98"
			struct_cutoff.inputs.in_file = _n4_res.outputs.output_image
			struct_cutoff_res = struct_cutoff.run()

			struct_BET = BET()
			struct_BET.inputs.mask = True
			struct_BET.inputs.frac = 0.3
			struct_BET.inputs.robust = True
			struct_BET.inputs.in_file = struct_cutoff_res.outputs.out_file
			struct_BET_res = struct_BET.run()

			struct_mask = ApplyMask()
			struct_mask.inputs.in_file = n4_res.outputs.output_image
			struct_mask.inputs.mask_file = struct_BET_res.outputs.mask_file
			struct_mask_res = struct_mask.run()

			struct_registration = ants.Registration()
			struct_registration.inputs.fixed_image = template
			struct_registration.inputs.output_transform_prefix = "output_"
			struct_registration.inputs.transforms = ['Affine', 'SyN'] ##
			struct_registration.inputs.transform_parameters = [(1.0,), (1.0, 3.0, 5.0)] ##
			struct_registration.inputs.number_of_iterations = [[2000, 1000, 500], [100, 100, 100]] #
			struct_registration.inputs.dimension = 3
			struct_registration.inputs.write_composite_transform = True
			struct_registration.inputs.collapse_output_transforms = True
			struct_registration.inputs.initial_moving_transform_com = True
			# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
			struct_registration.inputs.metric = ['MeanSquares', 'Mattes']
			struct_registration.inputs.metric_weight = [1, 1]
			struct_registration.inputs.radius_or_number_of_bins = [16, 32] #
			struct_registration.inputs.sampling_strategy = ['Random', None]
			struct_registration.inputs.sampling_percentage = [0.3, 0.3]
			struct_registration.inputs.convergence_threshold = [1.e-11, 1.e-8] #
			struct_registration.inputs.convergence_window_size = [20, 20]
			struct_registration.inputs.smoothing_sigmas = [[4, 2, 1], [4, 2, 1]]
			struct_registration.inputs.sigma_units = ['vox', 'vox']
			struct_registration.inputs.shrink_factors = [[3, 2, 1],[3, 2, 1]]
			struct_registration.inputs.use_estimate_learning_rate_once = [True, True]
			# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
			struct_registration.inputs.use_histogram_matching = [False, False]
			struct_registration.inputs.winsorize_lower_quantile = 0.005
			struct_registration.inputs.winsorize_upper_quantile = 0.98
			struct_registration.inputs.args = '--float'
			struct_registration.inputs.num_threads = 6

			struct_registration.inputs.moving_image = struct_mask_res.outputs.out_file
			struct_registration.inputs.output_warped_image = '{}/s_{}_ofM{}.nii.gz'.format(regdir,participant,i)
			struct_registration_res = struct_registration.run()

			#func
			func_n4 = ants.N4BiasFieldCorrection()
			func_n4.inputs.dimension = 3
			func_n4.inputs.input_image = func_image
			func_n4.inputs.bspline_fitting_distance = 100
			func_n4.inputs.shrink_factor = 2
			func_n4.inputs.n_iterations = [200,200,200,200]
			func_n4.inputs.convergence_threshold = 1e-11
			func_n4.inputs.output_image = '{}/f_n4_{}_ofM{}.nii.gz'.format(regdir,participant,i)
			func_n4_res = func_n4.run()

			func_registration = ants.Registration()
			func_registration.inputs.fixed_image = n4_res.outputs.output_image
			func_registration.inputs.output_transform_prefix = "func_"
			func_registration.inputs.transforms = [f2s]
			func_registration.inputs.transform_parameters = [(0.1,)]
			func_registration.inputs.number_of_iterations = [[40, 20, 10]]
			func_registration.inputs.dimension = 3
			func_registration.inputs.write_composite_transform = True
			func_registration.inputs.collapse_output_transforms = True
			func_registration.inputs.initial_moving_transform_com = True
			func_registration.inputs.metric = ['MeanSquares']
			func_registration.inputs.metric_weight = [1]
			func_registration.inputs.radius_or_number_of_bins = [16]
			func_registration.inputs.sampling_strategy = ["Regular"]
			func_registration.inputs.sampling_percentage = [0.3]
			func_registration.inputs.convergence_threshold = [1.e-2]
			func_registration.inputs.convergence_window_size = [8]
			func_registration.inputs.smoothing_sigmas = [[4, 2, 1]] # [1,0.5,0]
			func_registration.inputs.sigma_units = ['vox']
			func_registration.inputs.shrink_factors = [[3, 2, 1]]
			func_registration.inputs.use_estimate_learning_rate_once = [True]
			func_registration.inputs.use_histogram_matching = [False]
			func_registration.inputs.winsorize_lower_quantile = 0.005
			func_registration.inputs.winsorize_upper_quantile = 0.995
			func_registration.inputs.args = '--float'
			func_registration.inputs.num_threads = 6

			func_registration.inputs.moving_image = func_n4_res.outputs.output_image
			func_registration.inputs.output_warped_image = '{}/f_{}_ofM{}.nii.gz'.format(regdir,participant,i)
			func_registration_res = func_registration.run()

			warp = ants.ApplyTransforms()
			warp.inputs.reference_image = template
			warp.inputs.input_image_type = 3
			warp.inputs.interpolation = 'Linear'
			warp.inputs.invert_transform_flags = [False, False]
			warp.inputs.terminal_output = 'file'
			warp.inputs.output_image = '{}/{}_ofM{}.nii.gz'.format(regdir,participant,i)
			warp.num_threads = 6

			warp.inputs.input_image = func_image
			warp.inputs.transforms = [func_registration_res.outputs.composite_transform, struct_registration_res.outputs.composite_transform]
			warp.run()

