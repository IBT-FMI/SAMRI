import nipype.interfaces.ants as ants
import os
from nipype.interfaces.fsl import ApplyMask, GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ImageMaths, FSLCommand
from nipype.interfaces import ants, fsl
import nipype.pipeline.engine as pe

from samri.utilities import bids_substitution_iterator
from samri.pipelines.utils import GENERIC_PHASES

try:
	FileNotFoundError
except NameError:
	FileNotFoundError = IOError

PHASES = {
	"rigid":{
		"transforms":"Rigid",
		"transform_parameters":(0.1,),
		"number_of_iterations":[6000,3000],
		"metric":"GC",
		"metric_weight":1,
		"radius_or_number_of_bins":64,
		"sampling_strategy":"Regular",
		"sampling_percentage":0.2,
		"convergence_threshold":1.e-16,
		"convergence_window_size":30,
		"smoothing_sigmas":[1,0],
		"sigma_units":"vox",
		"shrink_factors":[2,1],
		"use_estimate_learning_rate_once":False,
		"use_histogram_matching":True,
		},
	"affine":{
		"transforms":"Affine",
		"transform_parameters":(0.1,),
		"number_of_iterations":[500,250],
		"metric":"MI",
		"metric_weight":1,
		"radius_or_number_of_bins":8,
		"sampling_strategy":None,
		"sampling_percentage":0.3,
		"convergence_threshold":1.e-32,
		"convergence_window_size":30,
		"smoothing_sigmas":[1,0],
		"sigma_units":"vox",
		"shrink_factors":[1,1],
		"use_estimate_learning_rate_once":False,
		"use_histogram_matching":True,
		},
	"syn":{
		"transforms":"SyN",
		"transform_parameters":(0.1, 2.0, 0.2),
		"number_of_iterations":[500,250],
		"metric":"MI",
		"metric_weight":1,
		"radius_or_number_of_bins":16,
		"sampling_strategy":None,
		"sampling_percentage":0.3,
		"convergence_threshold":1.e-32,
		"convergence_window_size":30,
		"smoothing_sigmas":[1,0],
		"sigma_units":"vox",
		"shrink_factors":[1,1],
		"use_estimate_learning_rate_once":False,
		"use_histogram_matching":True,
		},
	}

def single_generic(in_func, in_anat, template,
	mask=False,
	phases=GENERIC_PHASES,
	out_base='/var/tmp/samri_optimize',
	**kwargs):
	in_anat=os.path.abspath(os.path.expanduser(in_anat))
	in_func=os.path.abspath(os.path.expanduser(in_func))
	template=os.path.abspath(os.path.expanduser(template))

	from samri.pipelines.nodes import generic_registration

	in_anat_name = os.path.basename(in_anat).split('.nii')[0]
	in_func_name = os.path.basename(in_func).split('.nii')[0]

	try:
		os.makedirs(out_base)
	except OSError:
		pass
	s_biascorrect_outfile = '{}/{}_biascorrected.nii.gz'.format(out_base,in_anat_name)
	try:
		os.remove(s_biascorrect_outfile)
	except OSError:
		pass

	s_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="s_biascorrect")
	s_biascorrect.inputs.dimension = 3
	s_biascorrect.inputs.bspline_fitting_distance = 10
	s_biascorrect.inputs.bspline_order = 4
	s_biascorrect.inputs.shrink_factor = 2
	s_biascorrect.inputs.n_iterations = [150,100,50,30]
	s_biascorrect.inputs.convergence_threshold = 1e-16
	s_biascorrect.inputs.input_image = in_anat
	s_biascorrect.inputs.output_image = s_biascorrect_outfile
	s_biascorrect_run = s_biascorrect.run()

	#f_biascorrect = pe.Node(interface=ants.N4BiasFieldCorrection(), name="f_biascorrect")
	#f_biascorrect.inputs.dimension = 3
	#f_biascorrect.inputs.bspline_fitting_distance = 10
	#f_biascorrect.inputs.bspline_order = 4
	#f_biascorrect.inputs.shrink_factor = 2
	#f_biascorrect.inputs.n_iterations = [150,100,50,30]
	#f_biascorrect.inputs.convergence_threshold = 1e-11
	#f_biascorrect.inputs.input_image = in_func
	#f_biascorrect_run = f_biascorrect.run()

	s_register_outfile = '{}/{}_warped.nii.gz'.format(out_base,in_anat_name)
	try:
		os.remove(s_register_outfile)
	except OSError:
		pass
	s_register, s_warp, f_register, f_warp = generic_registration(template,mask,None,4,phases,
		**kwargs)
	s_register.inputs.moving_image = s_biascorrect_run.outputs.output_image
	s_register.inputs.output_warped_image = s_register_outfile
	s_register.run()

def structural(substitutions, parameters,
	reference="/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
	structural_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_workdir}/_subject_session_{subject}.{session}/_scan_type_{scan}/s_bru2nii/",
	workdir="~/samri_optimize/structural",
	threads=6,
	prefix="_",
	):

	reference=os.path.abspath(os.path.expanduser(reference))
	workdir=os.path.abspath(os.path.expanduser("~/samri_optimize/structural"))
	if not os.path.exists(workdir):
		os.makedirs(workdir)

	for substitution in substitutions:
		image_path = structural_file_template.format(**substitution)
		image_path = os.path.abspath(os.path.expanduser(image_path))
		if os.path.isdir(image_path):
			try:
				for myfile in os.listdir(image_path):
					if myfile.endswith(".nii") and ( not prefix or myfile.startswith(prefix) ):
						image_path = os.path.join(image_path,myfile)
			except FileNotFoundError:
				pass
		if not os.path.isfile(image_path):
			print("{} not found!".format(image_path))
			pass
		else:
			n4_out = os.path.join(workdir,'n4_{subject}_{session}.nii.gz'.format(**substitution))
			n4 = ants.N4BiasFieldCorrection()
			n4.inputs.dimension = 3
			n4.inputs.input_image = image_path
			# correction bias is introduced (along the z-axis) if the following value is set to under 85. This is likely contingent on resolution.
			n4.inputs.bspline_fitting_distance = 10
			n4.inputs.bspline_order = 4
			# n4.inputs.bspline_fitting_distance = 95
			n4.inputs.shrink_factor = 2
			n4.inputs.n_iterations = [150,100,50,30]
			n4.inputs.convergence_threshold = 1e-16
			n4.inputs.num_threads = threads
			n4.inputs.output_image = n4_out
			print("Running bias field correction:\n{}".format(n4.cmdline))
			n4_run = n4.run()

			struct_registration = ants.Registration()
			struct_registration.inputs.fixed_image = reference
			struct_registration.inputs.output_transform_prefix = "output_"
			struct_registration.inputs.transforms = [i["transforms"] for i in parameters] ##
			# for stability: high second SyN parameter, low first and third (https://www.neuro.polymtl.ca/tips_and_tricks/how_to_use_ants)
			struct_registration.inputs.transform_parameters = [i["transform_parameters"] for i in parameters] ##
			struct_registration.inputs.number_of_iterations = [i["number_of_iterations"] for i in parameters] #
			struct_registration.inputs.dimension = 3
			struct_registration.inputs.write_composite_transform = True
			struct_registration.inputs.collapse_output_transforms = True
			struct_registration.inputs.initial_moving_transform_com = True
			# Tested on Affine transform: CC takes too long; Demons does not tilt, but moves the slices too far caudally;
			# MeanSquares is ok
			# GC tilts too much if sampling_percentage is set too high, but GC with sampling_percentage <= 20 is the only metric that can prevent bits skin on the skull from being mapped onto the brain
			struct_registration.inputs.metric = [i["metric"] for i in parameters]
			struct_registration.inputs.metric_weight = [i["metric_weight"] for i in parameters]
			#the following relates to the similarity metric (e.g. size of the bins for the histogram):
			struct_registration.inputs.radius_or_number_of_bins = [i["radius_or_number_of_bins"] for i in parameters]
			#Regular and Random sampling for SyN over-stretch the brain rostrocaudally
			struct_registration.inputs.sampling_strategy = [i["sampling_strategy"] for i in parameters]
			#The Rigid sampling_percentage needs to be kept low to ensure that the image does not start to rotate
			#very weird thins happen at sampling_percentage==0.15 but not at sampling_percentage==0.2 or sampling_percentage==0.1
			struct_registration.inputs.sampling_percentage = [i["sampling_percentage"] for i in parameters]
			struct_registration.inputs.convergence_threshold = [i["convergence_threshold"] for i in parameters]
			#the above threshold pertains to similarity improvement over the last <convergenceWindowSize> iterations
			struct_registration.inputs.convergence_window_size = [i["convergence_window_size"] for i in parameters]
			struct_registration.inputs.smoothing_sigmas = [i["smoothing_sigmas"] for i in parameters]
			struct_registration.inputs.sigma_units = [i["sigma_units"] for i in parameters]
			struct_registration.inputs.shrink_factors = [i["shrink_factors"] for i in parameters]
			struct_registration.inputs.use_estimate_learning_rate_once = [i["use_estimate_learning_rate_once"] for i in parameters]
			# if the fixed_image is not acquired similarly to the moving_image (e.g. RARE to histological (e.g. AMBMC)) this should be False
			struct_registration.inputs.use_histogram_matching = [i["use_histogram_matching"] for i in parameters]
			struct_registration.inputs.winsorize_lower_quantile = 0.05
			struct_registration.inputs.winsorize_upper_quantile = 0.95
			struct_registration.inputs.args = '--float'
			struct_registration.inputs.fixed_image_mask = "/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii"
			struct_registration.inputs.num_threads = threads
			struct_registration.inputs.output_warped_image = os.path.join(workdir,'{subject}_{session}.nii.gz'.format(**substitution))
			struct_registration.inputs.moving_image = n4_out
			print("Running registration:\n{}".format(struct_registration.cmdline))
			struct_registration_run = struct_registration.run()
