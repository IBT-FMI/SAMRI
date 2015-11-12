import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.nipy.preprocess import FmriRealign4d
from nipype.interfaces.nipy import SpaceTimeRealigner
from extra_interfaces import DcmToNii, MEICA, VoxelResize, Bru2, FindScan
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

def bru2_preproc(workflow_base, functional_scan_type, experiment_type=None, structural_scan_type=None, resize=True, omit_ID=[]):
	IDs=[]
	if experiment_type:
		for sub_dir in listdir(workflow_base):
			try:
				if experiment_type in open(workflow_base+"/"+sub_dir+"/subject").read():
					IDs.append(sub_dir)
			except IOError:
				pass
	else:
		for sub_dir in listdir(workflow_base):
			if sub_dir[:3] == "201" and sub_dir not in omit_ID:
				IDs.append(sub_dir)

	infosource = pe.Node(interface=util.IdentityInterface(fields=['measurement_id']), name="experiment_source")
	infosource.iterables = ('measurement_id', IDs)

	datasource1 = pe.Node(interface=nio.DataGrabber(infields=['measurement_id'], outfields=['measurement_path']), name='data_source')
	datasource1.inputs.template = workflow_base+"/%s"
	datasource1.inputs.template_args['measurement_path'] = [['measurement_id']]
	datasource1.inputs.template_args['measurement_path1'] = [['measurement_id']]
	datasource1.inputs.sort_filelist = True

	find_functional_scan = pe.Node(interface=FindScan(), name="functional_scan_filter")
	find_functional_scan.inputs.query = functional_scan_type
	find_functional_scan.inputs.query_file = "visu_pars"

	if structural_scan_type:
		find_structural_scan = pe.Node(interface=FindScan(), name="find_structural_scan")
		find_structural_scan.inputs.query = structural_scan_type
		find_structural_scan.inputs.query_file = "visu_pars"
		converter_structural = pe.MapNode(interface=Bru2(), name="bru2_structural", iterfield=['input_dir'])
		converter_structural.inputs.force_conversion=True
		if resize == False:
			converter_structural.inputs.actual_size=True

	converter_functional = pe.Node(interface=Bru2(), name="bru2nii")
	if resize == False:
		converter_functional.inputs.actual_size=True

	workflow = pe.Workflow(name="Preprocessing")

	workflow_connections = [
		(infosource, datasource1, [('measurement_id', 'measurement_id')]),
		(datasource1, find_functional_scan, [('measurement_path', 'scans_directory')]),
		(find_functional_scan, converter_functional, [('positive_scan', 'input_dir')])
		]

	if structural_scan_type:
		workflow_connections.extend([
			(datasource1, find_structural_scan, [('measurement_path1', 'scans_directory')]),
			(find_structural_scan, converter_structural, [('positive_scan', 'input_dir')])
			])

	workflow.connect(workflow_connections)

	return workflow


if __name__ == "__main__":
	IDs=[4457,4459]
	source_pattern="/mnt/data7/NIdata/export_ME/dicom/%s/1/%s/"
	preproc_workflow(workflow_base="/home/chymera/NIdata/export_ME/", source_pattern=source_pattern, IDs=IDs)
