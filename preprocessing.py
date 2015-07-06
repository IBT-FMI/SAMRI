import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.nipy.preprocess import FmriRealign4d
from nipype.interfaces.nipy import SpaceTimeRealigner
from extra_interfaces import DcmToNii
from nipype.interfaces.dcmstack import DcmStack
import nipype.interfaces.io as nio

def preproc_workflow(workflow_base=".", force_convert=False, source_pattern="", IDs=""):
	# make IDs strings
	if "int" or "float" in str([type(ID) for ID in IDs]):
		IDs = [str(ID) for ID in IDs]

	#initiate the infosource node
	infosource = pe.Node(interface=util.IdentityInterface(fields=['subject_id']), name="subject_info_source")
	#define the list of subjects your pipeline should be executed on
	infosource.iterables = ('subject_id', IDs)

	#initiate the DataGrabber node with the infield: 'subject_id'
	#and the outfield: 'func' and 'struct'
	datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'], outfields=['func', 'struct']), name = 'data_source')
	datasource.inputs.template = source_pattern
	#First way: define the arguments for the template '%s/%s.nii' for each field individual
	datasource.inputs.template_args['func'] = [['subject_id', 'EPI']]
	datasource.inputs.template_args['struct'] = [['subject_id','anatomical']]
	datasource.inputs.sort_filelist = True

	stacker = pe.Node(interface=DcmToNii(), name="stack_convert_functional")
	stacker.inputs.group_by = "EchoTime"
	struct_stacker = pe.Node(interface=DcmStack(), name="stack_convert_structural")

	realigner = pe.Node(interface=FmriRealign4d(), name='realign_functional')
	realigner.inputs.tr = 1.5
	realigner.inputs.time_interp = True
	realigner.inputs.slice_order = range(0,20)[::2]+range(0,20)[1::2]

	workflow = pe.Workflow(name='Preprocessing')
	workflow.base_dir = workflow_base

	workflow.connect([
		(infosource, datasource, [('subject_id', 'subject_id')]),
		(datasource, stacker, [('func', 'dcm_dir')]),
		(datasource, struct_stacker, [('struct', 'dicom_files')]),
		(stacker, realigner, [('nii_files', 'in_file')]),
		])
	print datasource.outputs
	print datasource.outputs.func
	print datasource.outputs.struct
	workflow.write_graph()
	workflow.run(plugin="MultiProc")

if __name__ == "__main__":
	IDs=[4457,4459]
	source_pattern="/mnt/data7/NIdata/dc.rs/export_ME/dicom/%s/1/%s/"

	preproc_workflow(workflow_base="/home/chymera/NIdata/dc.rs/export_ME/", source_pattern=source_pattern, IDs=IDs)
