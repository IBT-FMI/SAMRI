import nipype.interfaces.ants as ants
import os
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ImageMaths, FSLCommand

def Sfunctional_per_participant_test():
	for i in ["","_aF","_cF1","_cF2","_pF"]:
		template = "/home/chymera/NIdata/templates/ds_QBI_chr.nii.gz"
		image_dir = "/home/chymera/NIdata/ofM.dr/preprocessing/generic_work/_subject_condition_4007.ofM{}/_scan_type_7_EPI_CBV/temporal_mean/".format(i)
		for myfile in os.listdir(image_dir):
			if myfile.endswith(".nii.gz"):
				mimage = os.path.join(image_dir,myfile)

		n4 = ants.N4BiasFieldCorrection()
		n4.inputs.dimension = 3
		n4.inputs.input_image = mimage
		n4.inputs.bspline_fitting_distance = 100
		n4.inputs.shrink_factor = 2
		n4.inputs.n_iterations = [100,100,100,100]
		n4.inputs.convergence_threshold = 1e-10
		n4.inputs.output_image = 'n4_4001_ofM{}.nii.gz'.format(i)
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
		registration.inputs.output_warped_image = '4001_ofM{}.nii.gz'.format(i)
		res = registration.run()

def structural_per_participant_test():
	for i in ["","_aF","_cF1","_cF2","_pF"]:
		template = "/home/chymera/NIdata/templates/ds_QBI_chr.nii.gz"
		participant_no = "4012"
		image_dir = "/home/chymera/NIdata/ofM.dr/preprocessing/generic_work/_subject_condition_{}.ofM{}/_scan_type_T2_TurboRARE/structural_bru2nii/".format(participant_no,i)
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
			n4.inputs.bspline_fitting_distance = 100
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [200,200,200,200]
			n4.inputs.convergence_threshold = 1e-11
			n4.inputs.output_image = 'n4_{}_ofM{}.nii.gz'.format(participant_no,i)
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
			registration.inputs.output_warped_image = '{}_ofM{}.nii.gz'.format(participant_no,i)
			res = registration.run()

def functional_per_participant_test():
	for i in ["","_aF","_cF1","_cF2","_pF"]:
		template = "/home/chymera/NIdata/templates/ds_QBI_chr.nii.gz"
		participant_no = "4011"
		image_dir = "/home/chymera/NIdata/ofM.dr/preprocessing/generic_work/_subject_condition_{}.ofM{}/_scan_type_7_EPI_CBV/temporal_mean/".format(participant_no,i)
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
			n4.inputs.output_image = 'n4_{}_ofM{}.nii.gz'.format(participant_no,i)
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
			registration.inputs.output_warped_image = '{}_ofM{}.nii.gz'.format(participant_no,i)
			res = registration.run()

if __name__ == '__main__':
	# structural_per_participant_test()
	functional_per_participant_test()
