import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, FSLCommand
from nipype.interfaces.nipy import SpaceTimeRealigner
from nipype.interfaces.afni import Bandpass
from nipype.interfaces.afni.base import AFNICommand
from nipype.interfaces.dcmstack import DcmStack
import nipype.interfaces.io as nio
from os import path, listdir
import nipype.interfaces.ants as ants
from extra_interfaces import DcmToNii, MEICA, VoxelResize, Bru2, FindScan, GetBrukerTiming
from extra_functions import get_data_selection
from nodes import ants_standard_registration_warp

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

def bru_preproc_lite(measurements_base, functional_scan_type, tr=1, conditions=[], include_subjects=[], exclude_subjects=[], include_measurements=[], exclude_measurements=[], actual_size=False, realign=False):

	# define measurement directories to be processed, and populate the list either with the given include_measurements, or with an intelligent selection
	infosource = pe.Node(interface=util.IdentityInterface(fields=['measurement']), name="infosource")
	if include_measurements:
		infosource.iterables = ('measurement', include_measurements)
	else:
		data_selection=get_data_selection(measurements_base, conditions, include_subjects=include_subjects, exclude_subjects=exclude_subjects, exclude_measurements=exclude_measurements)
		infosource.iterables = ('measurement', list(data_selection["measurement"]))

	data_source = pe.Node(interface=nio.DataGrabber(infields=['id'], outfields=['measurement_path']), name='data_source')
	data_source.inputs.template = measurements_base+"/%s"
	data_source.inputs.template_args['measurement_path'] = [['id']]
	data_source.inputs.sort_filelist = True

	functional_scan_finder = pe.Node(interface=FindScan(), name="functional_scan_finder")
	functional_scan_finder.inputs.query = functional_scan_type
	functional_scan_finder.inputs.query_file = "visu_pars"

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	functional_bru2nii.inputs.actual_size=actual_size

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	workflow = pe.Workflow(name="PreprocessingLite")

	workflow_connections = [
		(infosource, data_source, [('measurement', 'id')]),
		(data_source, functional_scan_finder, [('measurement_path', 'scans_directory')]),
		(functional_scan_finder, functional_bru2nii, [('positive_scan', 'input_dir')]),
		]
	if realign:
		workflow_connections.extend([
			(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
			])

	workflow.connect(workflow_connections)
	return workflow

def bru2_preproc2(measurements_base, functional_scan_type, structural_scan_type=None, tr=1, conditions=[], include_subjects=[], exclude_subjects=[], include_measurements=[], exclude_measurements=[], actual_size=False, workflow_denominator="Preprocessing", template="ds_QBI_atlas100RD.nii", standalone_execute=False):
	measurements_base = path.expanduser(measurements_base)
	data_selection=get_data_selection(measurements_base, conditions, include_subjects=include_subjects, exclude_subjects=exclude_subjects, exclude_measurements=exclude_measurements)

	infosource = pe.Node(interface=util.IdentityInterface(fields=["condition","subject"]), name="infosource")
	infosource.iterables = [('condition', list(set(data_selection["condition"]))), ('subject', list(set(data_selection["subject"])))]

	# data_source = pe.Node(interface=nio.DataGrabber(infields=["condition_id","subject_id"], outfields=['measurement_path']), name='data_source')
	# data_source.inputs.base_directory = measurements_base
	# data_source.inputs.template = "/%s"
	# data_source.inputs.template_args['measurement_path'] = [[data_selection[(data_selection["condition"] == "condition_id")&(data_selection["subject"] == "subject_id")]]]
	# data_source.inputs.sort_filelist = True

	# def get_measurement(condition_id, subject_id, data_selection, measurements_base):
	# 	measurement_path = data_selection[(data_selection["condition"] == condition_id)&(data_selection["subject"] == subject_id)]["measurement"]
	# 	measurement_path = measurements_base + "/" + measurement_path
	# 	return measurement_path
	#
	# getmeasurement = pe.Node(name='getmeasurement', interface=util.Function(function=get_measurement, input_names=['condition_id',"subject_id","data_selection","measurements_base"], output_names=['measurement_path']))
	# getmeasurement.inputs.data_selection = data_selection
	# getmeasurement.inputs.measurements_base = measurements_base

	def get_measurement(condition_id, subject_id, measurements_base, data_selection):
		measurement_path = data_selection[(data_selection["condition"] == condition_id)&(data_selection["subject"] == subject_id)]["measurement"]
		measurement_path = measurements_base + "/" + measurement_id
		return measurement_path

	getmeasurement = pe.Node(name='getmeasurement', interface=util.Function(function=get_measurement, input_names=["condition_id","subject_id","measurements_base","data_selection"], output_names=['measurement_path']))
	getmeasurement.inputs.data_selection = data_selection
	getmeasurement.inputs.measurements_base = measurements_base

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
		structural_bru2nii.inputs.actual_size=actual_size

		structural_FAST = pe.Node(interface=FAST(), name="structural_FAST")
		structural_FAST.inputs.segments = False
		structural_FAST.inputs.output_biascorrected = True
		structural_FAST.inputs.bias_iters = 8

		structural_cutoff = pe.Node(interface=ImageMaths(), name="structural_cutoff")
		structural_cutoff.inputs.op_string = "-thrP 45"

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	functional_bru2nii.inputs.actual_size=actual_size

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	temporal_mean = pe.Node(interface=MeanImage(), name="temporal_mean")
	functional_masker = pe.Node(interface=ApplyMask(), name="functional_masker")

	structural_BET = pe.Node(interface=BET(), name="structural_BET")
	structural_BET.inputs.mask = True
	structural_BET.inputs.frac = 0.5

	structural_registration, structural_warp = ants_standard_registration_warp(template, "structural_registration", "structural_warp")
	functional_registration, functional_warp = ants_standard_registration_warp(template, "functional_registration", "functional_warp")

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
		(infosource, getmeasurement, [('condition', 'condition_id'), ('subject', 'subject_id')]),
		(getmeasurement, functional_scan_finder, [('measurement_path', 'scans_directory')]),
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
			(getmeasurement, structural_scan_finder, [('measurement_path', 'scans_directory')]),
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
		workflow.base_dir = measurements_base
		workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	else:
		return workflow

def bru2_preproc(measurements_base, functional_scan_type, structural_scan_type=None, tr=1, conditions=[], include_subjects=[], exclude_subjects=[], include_measurements=[], exclude_measurements=[], actual_size=False, workflow_denominator="PreprocessingGLM", template="ds_QBI_atlas100RD.nii"):
	workflow_base = path.expanduser(workflow_base)
	data_selection=get_data_selection(measurements_base, conditions, include_subjects=include_subjects, exclude_subjects=exclude_subjects, exclude_measurements=exclude_measurements)

	infosource = pe.Node(interface=util.IdentityInterface(fields=['measurement_id']), name="infosource")
	infosource.iterables = ('measurement', IDs)

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
		structural_bru2nii.inputs.actual_size=actual_size

		structural_FAST = pe.Node(interface=FAST(), name="structural_FAST")
		structural_FAST.inputs.segments = False
		structural_FAST.inputs.output_biascorrected = True
		structural_FAST.inputs.bias_iters = 8

		structural_cutoff = pe.Node(interface=ImageMaths(), name="structural_cutoff")
		structural_cutoff.inputs.op_string = "-thrP 45"

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	functional_bru2nii.inputs.actual_size=actual_size

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.slice_times = "asc_alt_2"
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)

	temporal_mean = pe.Node(interface=MeanImage(), name="temporal_mean")
	functional_masker = pe.Node(interface=ApplyMask(), name="functional_masker")

	structural_BET = pe.Node(interface=BET(), name="structural_BET")
	structural_BET.inputs.mask = True
	structural_BET.inputs.frac = 0.5

	structural_registration, structural_warp = ants_standard_registration_warp(template, "structural_registration", "structural_warp")
	functional_registration, functional_warp = ants_standard_registration_warp(template, "functional_registration", "functional_warp")

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
	return workflow

if __name__ == "__main__":
	# bru2_preproc_lite(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", conditions=["ofM"], subjects_include=[], subjects_exclude=[], measurements_exclude=["20151027_121613_4013_1_1"])
	bru2_preproc2("~/NIdata/ofM.dr/", "7_EPI_CBV", structural_scan_type="T2_TurboRARE>", conditions=["<ofM>","<ofM_aF>"], exclude_measurements=["20151027_121613_4013_1_1"], standalone_execute=True)
