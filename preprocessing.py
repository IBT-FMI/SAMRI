import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.fsl import FAST
from nipype.interfaces.nipy import SpaceTimeRealigner
from extra_interfaces import DcmToNii, MEICA, VoxelResize, Bru2, FindScan, GetBrukerTiming
from nipype.interfaces.dcmstack import DcmStack
import nipype.interfaces.io as nio
from os import path, listdir

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

	functional_bru2nii.inputs.actual_size=True

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
	realigner.inputs.slice_times = "asc_alt_2"

	workflow = pe.Workflow(name="PreprocessingLite")

	workflow_connections = [
		(infosource, data_source, [('measurement_id', 'measurement_id')]),
		(data_source, functional_scan_finder, [('measurement_path', 'scans_directory')]),
		(functional_scan_finder, functional_bru2nii, [('positive_scan', 'input_dir')]),
		(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
		]

def bru2_preproc(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, resize=True, omit_ID=[], tr=1, inclusion_filter=""):
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

	functional_bru2nii = pe.Node(interface=Bru2(), name="functional_bru2nii")
	if resize == False:
		functional_bru2nii.inputs.actual_size=True

	realigner = pe.Node(interface=SpaceTimeRealigner(), name="realigner")
	realigner.inputs.tr = tr
	realigner.inputs.slice_info = 3 #3 for coronal slices (2 for horizontal, 1 for sagittal)
	realigner.inputs.slice_times = "asc_alt_2"

	workflow = pe.Workflow(name="Preprocessing")

	workflow_connections = [
		(infosource, data_source, [('measurement_id', 'measurement_id')]),
		(data_source, functional_scan_finder, [('measurement_path', 'scans_directory')]),
		(functional_scan_finder, functional_bru2nii, [('positive_scan', 'input_dir')]),
		(functional_scan_finder, timing_metadata, [('positive_scan', 'scan_directory')]),
		(functional_bru2nii, realigner, [('nii_file', 'in_file')]),
		]

	if structural_scan_type:
		workflow_connections.extend([
			(data_source, structural_scan_finder, [('measurement_path', 'scans_directory')]),
			(structural_scan_finder, structural_bru2nii, [('positive_scan', 'input_dir')]),
			(structural_bru2nii, structural_FAST, [('nii_file', 'in_files')])
			])

	workflow.connect(workflow_connections)

	return workflow

if __name__ == "__main__":
	IDs=[4457,4459]
	source_pattern="/mnt/data7/NIdata/export_ME/dicom/%s/1/%s/"
	preproc_workflow(workflow_base="/home/chymera/NIdata/export_ME/", source_pattern=source_pattern, IDs=IDs)
