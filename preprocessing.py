import nipype.pipeline.engine as pe				# workflow and node wrappers
import os										# system functions
import nipype.interfaces.freesurfer as fs		# freesurfer
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.nipy.preprocess import FmriRealign4d
from os import listdir
from extra_interfaces import DcmToNii
import nipype.interfaces.io as nio


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
	datasource.inputs.template = 'source_pattern'

	#First way: define the arguments for the template '%s/%s.nii' for each field individual
	datasource.inputs.template_args['func'] = [['subject_id', 'EPI']]
	datasource.inputs.template_args['struct'] = [['subject_id','anatomical']]

	datasource.inputs.sort_filelist = True

	#initiate the meta workflow
	metaflow = pe.Workflow(name='metaflow')

	#connect infosource, datasource and inputnode to each other
	metaflow.connect([(infosource, datasource,[('subject_id','subject_id')])])
	metaflow.run(plugin="MultiProc")

	return
	stacker = pe.Node(name="dcm_to_nii", interface=DcmToNii())
	stacker.iterables = ("dcm_dir", data_dir)
	stacker.inputs.group_by = "EchoTime"

	realigner = pe.Node(interface=FmriRealign4d(), name='realign')
	realigner.inputs.tr = 1.5
	realigner.inputs.time_interp = True
	realigner.inputs.slice_order = range(0,20)[::2]+range(0,20)[1::2]

	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = workflow_base

	workflow.connect([
		(stacker, realigner, [('nii_files', 'in_file')])
		])
	workflow.run(plugin="MultiProc")

if __name__ == "__main__":
	IDs=[4457,4459,4460]
	data_dirs=["/home/chymera/data/dc.rs/export_ME/dicom/"+str(ID)+"/1/EPI/" for ID in IDs]
	source_pattern="/home/chymera/data/dc.rs/export_ME/dicom/%s/1/%s/"

	preproc_workflow(data_dirs, workflow_base="/home/chymera/data/dc.rs/export_ME/", source_pattern=source_pattern, IDs=IDs)
