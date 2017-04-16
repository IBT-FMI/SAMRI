import nipype.interfaces.ants as ants
import os
from nipype.interfaces.fsl import ApplyMask, GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ImageMaths, FSLCommand
from nipype.interfaces import fsl

from samri.utilities import bids_substitution_iterator

try:
	FileNotFoundError
except NameError:
	FileNotFoundError = IOError

def structural(substitutions,
	reference="~/ni_data/templates/DSURQEc_40micron_average.nii",
	structural_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_workdir}/_subject_session_{subject}.{session}/_scan_type_{scan}/s_bru2nii/",
	workdir="~/samri_optimize/structural",
	run=True,
	):

	reference=os.path.abspath(os.path.expanduser("~/ni_data/templates/DSURQEc_40micron_average.nii"))
	workdir=os.path.abspath(os.path.expanduser("~/samri_optimize/structural"))
	if not os.path.exists(workdir):
		os.makedirs(workdir)

	for substitution in substitutions:
		image_dir = structural_file_template.format(**substitution)
		image_dir = os.path.abspath(os.path.expanduser(image_dir))
		try:
			for myfile in os.listdir(image_dir):
				if myfile.endswith(".nii"):
					mimage = os.path.join(image_dir,myfile)
		except FileNotFoundError:
			pass
		else:
			n4 = ants.N4BiasFieldCorrection()
			n4.inputs.dimension = 3
			n4.inputs.input_image = mimage
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			n4.inputs.bspline_fitting_distance = 100
			# n4.inputs.bspline_fitting_distance = 95
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [200,200,200,200]
			n4.inputs.convergence_threshold = 1e-14
			# n4.inputs.convergence_threshold = 1e-11
			n4.inputs.output_image = os.path.join(workdir,'n4_{subject}_{session}.nii.gz'.format(**substitution))

			struct_registration = ants.Registration()
			struct_registration.inputs.fixed_image = reference
			struct_registration.inputs.output_transform_prefix = "output_"
			struct_registration.inputs.transforms = ['Rigid', 'Affine', 'SyN'] ##
			struct_registration.inputs.transform_parameters = [(1,), (1.0,), (1.0, 3.0, 5.0)] ##
			struct_registration.inputs.number_of_iterations = [[300,150,50], [1500, 500, 250], [100, 100, 100]] #
			struct_registration.inputs.dimension = 3
			struct_registration.inputs.write_composite_transform = True
			struct_registration.inputs.collapse_output_transforms = True
			struct_registration.inputs.initial_moving_transform_com = True
			# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally; GC tilts too much on
			struct_registration.inputs.metric = ['MeanSquares', 'MeanSquares', 'Mattes']
			struct_registration.inputs.metric_weight = [1, 1, 1]
			struct_registration.inputs.radius_or_number_of_bins = [16, 16, 32] #
			struct_registration.inputs.sampling_strategy = ['Random','Random', None]
			struct_registration.inputs.sampling_percentage = [0.3, 0.3, 0.3]
			struct_registration.inputs.convergence_threshold = [1.e-10, 1.e-11, 1.e-8] #
			struct_registration.inputs.convergence_window_size = [20, 20, 20]
			struct_registration.inputs.smoothing_sigmas = [[4, 2, 1], [4, 2, 1], [4, 2, 1]]
			struct_registration.inputs.sigma_units = ['vox', 'vox', 'vox']
			struct_registration.inputs.shrink_factors = [[3, 2, 1],[3, 2, 1],[3, 2, 1]]
			struct_registration.inputs.use_estimate_learning_rate_once = [True, True, True]
			# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
			struct_registration.inputs.use_histogram_matching = [False, False, False]
			struct_registration.inputs.winsorize_lower_quantile = 0.005
			struct_registration.inputs.winsorize_upper_quantile = 0.98
			struct_registration.inputs.args = '--float'
			struct_registration.inputs.num_threads = 6

			struct_registration.inputs.output_warped_image = os.path.join(workdir,'{subject}_{session}.nii.gz'.format(**substitution))

			#node linking is only done if and after the interfaces are run. If they are not to be run, all inputs are set to the preexisting `mimage` file.
			if run:
				n4_res = n4.run()
				struct_registration.inputs.moving_image = n4.inputs.output_image
				res = struct_registration.run()
			else:
				struct_registration.inputs.moving_image = mimage
				print(n4.cmdline)
				print(struct_registration.cmdline)

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

if __name__ == '__main__':
	# substitutions = bids_substitution_iterator(
	# 	["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
	# 	["4011","4012","5689","5690","5691"],
	# 	["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
	# 	"composite")
	substitutions = bids_substitution_iterator(
		["ofM"],
		["4011","4012"],
		["TurboRARE"],
		"composite")
	structural(substitutions,
		structural_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_workdir}/_subject_session_{subject}.{session}/_scan_type_{scan}/s_bru2nii/",
		run=False,
		)

	# structural_to_functional_per_participant_test(
	# 	subjects_participants = [{'subjfect' : 11, 'session': 'rstFMRI_with_medetadomine'}],
	# 	template = "~/GitHub/mriPipeline/templates/waxholm/WHS_SD_rat_T2star_v1.01_downsample3.nii.gz",
	# 	f_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_SE_EPI/f_bru2nii/",
	# 	s_file_format = "~/GitHub/mripipeline/base/preprocessing/generic_work/_subject_session_{subject}.{session}/_scan_type_T2_TurboRARE/s_bru2nii/",
	# 	)
