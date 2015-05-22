import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.nipy.preprocess import FmriRealign4d
from extra_interfaces import DcmToNii
from nipype.interfaces.dcmstack import DcmStack
import nipype.interfaces.io as nio
from copy import deepcopy

def preproc_workflow(data_dir, workflow_base=".", force_convert=False, source_pattern="", IDs=""):
	# make IDs strings
	if "int" or "float" in str([type(ID) for ID in IDs]):
		IDs = [str(ID) for ID in IDs]

	#initiate the infosource node
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id']), name="infosource")
	#define the list of subjects your pipeline should be executed on
	infosource.iterables = ('subject_id', IDs)

	#initiate the DataGrabber node with the infield: 'subject_id'
	#and the outfield: 'func' and 'struct'
	datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'], outfields=['func', 'struct']), name = 'datasource')
	#to specify the location of the experiment folder
	# datasource.inputs.base_directory = '~/experiment_folder'
	#define the structure of the data folders and files.
	#Each '%s' will later be filled by a template argument.
	datasource.inputs.template = source_pattern
	#First way: define the arguments for the template '%s/%s.nii' for each field individual
	datasource.inputs.template_args['func'] = [['subject_id', 'EPI']]
	datasource.inputs.template_args['struct'] = [['subject_id','anatomical']]
	datasource.inputs.sort_filelist = True

	struct_stacker = pe.Node(name="struct_stack", interface=DcmStack())

	stacker = pe.Node(name="dcm_to_nii", interface=DcmToNii())
	stacker.inputs.group_by = "EchoTime"

	realigner = pe.Node(interface=FmriRealign4d(), name='realign')
	realigner.inputs.tr = 1.5
	realigner.inputs.time_interp = True
	realigner.inputs.slice_order = range(0,20)[::2]+range(0,20)[1::2]
	struct_realigner = pe.Node(interface=FmriRealign4d(), name='struct_realign')
	struct_realigner.inputs.tr = 1.5
	struct_realigner.inputs.time_interp = True
	struct_realigner.inputs.slice_order = range(0,20)[::2]+range(0,20)[1::2]

	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = workflow_base

	workflow.connect([
		(infosource, datasource, [('subject_id', 'subject_id')]),
		(datasource, stacker, [('func', 'dcm_dir')]),
		(datasource, struct_stacker, [('struct', 'dicom_files')]),
		(stacker, realigner, [('nii_files', 'in_file')]),
		(struct_stacker, struct_realigner, [('out_file', 'in_file')]),
		])
	print datasource.outputs
	print datasource.outputs.func
	print datasource.outputs.struct
	workflow.write_graph()
	workflow.run(plugin="MultiProc")

if __name__ == "__main__":
	IDs=[4457,4459]
	data_dirs=["/home/chymera/data/dc.rs/export_ME/dicom/"+str(ID)+"/1/EPI/" for ID in IDs]
	source_pattern="/home/chymera/data/dc.rs/export_ME/dicom/%s/1/%s/"

	preproc_workflow(data_dirs, workflow_base="/home/chymera/data/dc.rs/export_ME/", source_pattern=source_pattern, IDs=IDs)
