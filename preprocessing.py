import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, FSLCommand
from nipype.interfaces.nipy import SpaceTimeRealigner
from nipype.interfaces.afni import Bandpass
from nipype.interfaces.afni.base import AFNICommand
from extra_interfaces import DcmToNii, MEICA, VoxelResize, Bru2, FindScan, GetBrukerTiming
from nipype.interfaces.dcmstack import DcmStack
import nipype.interfaces.io as nio
from os import path, listdir
import nipype.interfaces.ants as ants

#set all outputs to compressed NIfTI
AFNICommand.set_default_output_type('NIFTI_GZ')
FSLCommand.set_default_output_type('NIFTI_GZ')

def dcm_preproc(workflow_base=".", force_convert=False, source_pattern="", IDs=""):
	# make IDs strings
	if "int" or "float" in str([type(ID) for ID in IDs]):
		IDs = [str(ID) for ID in IDs]

	#initiate the infosource node
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id']), name="subject_info_source")
	#define the list of subjects your pipeline should be executed on
	infosource.iterables = ('subject_id', IDs)

	#initiate the DataGrabber node with the infield: 'subject_id'
	#and the outfield: 'func' and 'struct'
	datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'], outfields=['func', 'struct']), name='data_source')
	datasource.inputs.template = source_pattern
	#First way: define the arguments for the template '%s/%s.nii' for each field individual
	datasource.inputs.template_args['func'] = [['subject_id', 'EPI']]
	datasource.inputs.template_args['struct'] = [['subject_id','anatomical']]
	datasource.inputs.sort_filelist = True

	stacker = pe.Node(interface=DcmToNii(), name="stack_convert_functional")
	stacker.inputs.group_by = "EchoTime"

	struct_stacker = pe.Node(interface=DcmStack(), name="stack_convert_structural")

	voxelresize = pe.Node(interface=VoxelResize(), name="voxel_resize")
	voxelresize.inputs.resize_factor = 10

	meica = pe.Node(interface=MEICA(), name="multi_echo_ICA")
	meica.inputs.TR = 1.5
	meica.inputs.tpattern = "altminus"
	meica.inputs.cpus = 3

	workflow = pe.Workflow(name='Preprocessing')
	workflow.base_dir = workflow_base

	workflow.connect([
		(infosource, datasource, [('subject_id', 'subject_id')]),
		(datasource, stacker, [('func', 'dcm_dir')]),
		(stacker, voxelresize, [('nii_files', 'nii_files')]),
		(datasource, struct_stacker, [('struct', 'dicom_files')]),
		(stacker, meica, [('echo_times', 'echo_times')]),
		(voxelresize, meica, [('resized_files', 'echo_files')]),
		])

	workflow.write_graph(graph2use="orig")
	workflow.run(plugin="MultiProc")

def bru2_preproc_lite(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, omit_ID=[], tr=1, inclusion_filter=""):
	IDs=[]
	for sub_dir in listdir(workflow_base):
		if inclusion_filter in sub_dir:
			if sub_dir not in omit_ID:
				if experiment_type:
					try:
						if experiment_type in open(workflow_base+"/"+sub_dir+"/subject").read():
							IDs.append(sub_dir)
					except IOError:
						pass
				else:
					IDs.append(sub_dir)

	infosource = pe.Node(interface=util.IdentityInterface(fields=['measurement_id']), name="infosource")
	infosource.iterables = ('measurement_id', IDs)

	data_source = pe.Node(interface=nio.DataGrabber(infields=['measurement_id'], outfields=['measurement_path']), name='data_source')
	data_source.inputs.template = workflow_base+"/%s"
	data_source.inputs.template_args['measurement_path'] = [['measurement_id']]
	data_source.inputs.sort_filelist = True

	functional_scan_finder = pe.Node(interface=FindScan(), name="functional_scan_finder")
	functional_scan_finder.inputs.query = functional_scan_type
	functional_scan_finder.inputs.query_file = "visu_pars"

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	# functional_bru2nii.inputs.actual_size=True

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	workflow = pe.Workflow(name="PreprocessingLite")

	workflow_connections = [
		(infosource, data_source, [('measurement_id', 'measurement_id')]),
		(data_source, functional_scan_finder, [('measurement_path', 'scans_directory')]),
		(functional_scan_finder, functional_bru2nii, [('positive_scan', 'input_dir')]),
		(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
		]

	workflow.connect(workflow_connections)
	workflow.base_dir = workflow_base
	return workflow

def bru2_preproc(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, resize=True, omit_ID=[], tr=1, inclusion_filter="", workflow_denominator="PreprocessingGLM", template="ds_QBI_atlas100RD.nii", standalone_execute=False):
	workflow_base = path.expanduser(workflow_base)
	IDs=[]
	for sub_dir in listdir(workflow_base):
		if inclusion_filter in sub_dir:
			if sub_dir not in omit_ID:
				if experiment_type:
					try:
						if experiment_type in open(workflow_base+"/"+sub_dir+"/subject").read():
							IDs.append(sub_dir)
					except IOError:
						pass
				else:
					IDs.append(sub_dir)

	infosource = pe.Node(interface=util.IdentityInterface(fields=['measurement_id']), name="infosource")
	infosource.iterables = ('measurement_id', IDs)

	data_source = pe.Node(interface=nio.DataGrabber(infields=['measurement_id'], outfields=['measurement_path']), name='data_source')
	data_source.inputs.template = workflow_base+"/%s"
	data_source.inputs.template_args['measurement_path'] = [['measurement_id']]
	data_source.inputs.sort_filelist = True

	functional_scan_finder = pe.Node(interface=FindScan(), name="functional_scan_finder")
	functional_scan_finder.inputs.query = functional_scan_type
	functional_scan_finder.inputs.query_file = "visu_pars"

	timing_metadata = pe.Node(interface=GetBrukerTiming(), name="timing_metadata")

	if structural_scan_type:
		structural_scan_finder = pe.Node(interface=FindScan(), name="structural_scan_finder")
		structural_scan_finder.inputs.query = structural_scan_type
		structural_scan_finder.inputs.query_file = "visu_pars"
		structural_bru2nii = pe.Node(interface=Bru2(), name="structural_bru2nii")
		structural_bru2nii.inputs.force_conversion=True
		if resize == False:
			structural_bru2nii.inputs.actual_size=True

		structural_FAST = pe.Node(interface=FAST(), name="structural_FAST")
		structural_FAST.inputs.segments = False
		structural_FAST.inputs.output_biascorrected = True
		structural_FAST.inputs.bias_iters = 8

		structural_cutoff = pe.Node(interface=ImageMaths(), name="structural_cutoff")
		structural_cutoff.inputs.op_string = "-thrP 45"

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	if resize == False:
		functional_bru2nii.inputs.actual_size=True

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	temporal_mean = pe.Node(interface=MeanImage(), name="temporal_mean")
	functional_masker = pe.Node(interface=ApplyMask(), name="functional_masker")

	structural_BET = pe.Node(interface=BET(), name="structural_BET")
	structural_BET.inputs.mask = True
	structural_BET.inputs.frac = 0.5

	structural_registration = pe.Node(ants.Registration(), name='structural_registration')
	structural_registration.inputs.fixed_image = "/home/chymera/NIdata/templates/"+template
	structural_registration.inputs.output_transform_prefix = "output_"
	structural_registration.inputs.transforms = ['Rigid', 'Affine', 'SyN']
	structural_registration.inputs.transform_parameters = [(0.1,), (0.1,), (0.2, 3.0, 0.0)]
	structural_registration.inputs.number_of_iterations = [[9000, 9990, 9990]] * 2 + [[100, 30, 20]]
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
	structural_warp.inputs.reference_image = "/home/chymera/NIdata/templates/"+template
	structural_warp.inputs.input_image_type = 3
	structural_warp.inputs.interpolation = 'Linear'
	structural_warp.inputs.invert_transform_flags = [False]
	structural_warp.inputs.terminal_output = 'file'
	structural_warp.num_threads = 4

	functional_registration = pe.Node(ants.Registration(), name='functional_registration')
	functional_registration.inputs.fixed_image = "/home/chymera/NIdata/templates/"+template
	functional_registration.inputs.output_transform_prefix = "output_"
	functional_registration.inputs.transforms = ['Rigid', 'Affine', 'SyN']
	functional_registration.inputs.transform_parameters = [(0.1,), (0.1,), (0.2, 3.0, 0.0)]
	functional_registration.inputs.number_of_iterations = [[9000, 9990, 9990]] * 2 + [[100, 30, 20]]
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
	functional_warp.inputs.reference_image = "/home/chymera/NIdata/templates/"+template
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

	functional_BET = pe.Node(interface=BET(), name="functional_BET")
	functional_BET.inputs.mask = True
	functional_BET.inputs.frac = 0.5

	functional_bandpass = pe.Node(interface=Bandpass(), name="functional_bandpass")
	functional_bandpass.inputs.highpass = 0.001
	functional_bandpass.inputs.lowpass = 9999

	structural_bandpass = pe.Node(interface=Bandpass(), name="structural_bandpass")
	structural_bandpass.inputs.highpass = 0.001
	structural_bandpass.inputs.lowpass = 9999

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	workflow = pe.Workflow(name=workflow_denominator)

	workflow_connections = [
		(infosource, data_source, [('measurement_id', 'measurement_id')]),
		(data_source, functional_scan_finder, [('measurement_path', 'scans_directory')]),
		(functional_scan_finder, functional_bru2nii, [('positive_scan', 'input_dir')]),
		(functional_scan_finder, timing_metadata, [('positive_scan', 'scan_directory')]),
		(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
		(realigner, temporal_mean, [('out_file', 'in_file')]),
		(temporal_mean, functional_FAST, [('out_file', 'in_files')]),
		(functional_FAST, functional_cutoff, [('restored_image', 'in_file')]),
		(functional_cutoff, functional_BET, [('out_file', 'in_file')]),
		(functional_BET, functional_registration, [('out_file', 'moving_image')]),
		(functional_registration, functional_warp, [('composite_transform', 'transforms')]),
		(realigner, functional_warp, [('out_file', 'input_image')]),
		(functional_warp, functional_bandpass, [('output_image', 'in_file')]),
		]

	if structural_scan_type:
		workflow_connections.extend([
			(data_source, structural_scan_finder, [('measurement_path', 'scans_directory')]),
			(structural_scan_finder, structural_bru2nii, [('positive_scan', 'input_dir')]),
			(structural_bru2nii, structural_FAST, [('nii_file', 'in_files')]),
			(structural_FAST, structural_cutoff, [('restored_image', 'in_file')]),
			(structural_cutoff, structural_BET, [('out_file', 'in_file')]),
			(structural_BET, structural_registration, [('out_file', 'moving_image')]),
			(structural_registration, structural_warp, [('composite_transform', 'transforms')]),
			(realigner, structural_warp, [('out_file', 'input_image')]),
			(structural_warp, structural_bandpass, [('output_image', 'in_file')]),
			])

	workflow.connect(workflow_connections)
	if standalone_execute:
		workflow.base_dir = workflow_base
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	return workflow

if __name__ == "__main__":
	# IDs=[4457,4459]
	# source_pattern="/mnt/data7/NIdata/export_ME/dicom/%s/1/%s/"
	# preproc_workflow(workflow_base="/home/chymera/NIdata/export_ME/", source_pattern=source_pattern, IDs=IDs)
	bru2_preproc(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", structural_scan_type="T2_TurboRARE>", experiment_type="<ofM_aF>", omit_ID=["20151027_121613_4013_1_1"], standalone_execute=True)
