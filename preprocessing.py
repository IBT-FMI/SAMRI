import nipype.pipeline.engine as pe				# workflow and node wrappers
import os										# system functions
import nipype.interfaces.freesurfer as fs		# freesurfer
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
import nipype.interfaces.dcmstack as dcmstack
from dcmstack.extract import default_extractor
from nipype.interfaces.nipy.preprocess import FmriRealign4d
from os import listdir
from dicom import read_file

def preproc_workflow(data_dir, workflow_base=".", force_convert=False):

	if "dicom" in data_dir:
		stacker = pe.Node(interface=dcmstack.DcmStack(), name='stack')
		dicom_files = listdir(data_dir)
		echo_times=[]
		for dicom_file in dicom_files:
			meta = default_extractor(read_file(data_dir+dicom_file, stop_before_pixels=True, force=True))
			echo_times += [meta["EchoTime"]]

		for echo_time in list(set(echo_times)):
			echo_indices = [i for i, j in enumerate(echo_times) if j == echo_time]
			stacker.inputs.embed_meta = True
			# destination_file_name = nii_dir+"/"
			# stacker.inputs.out_path = destination_file_name
			# result = stacker.run()
			# print(result.outputs.out_file)
			# stacker.inputs.dicom_files = [data_dir+dicom_files[index] for index in echo_indices]
			stacker.inputs.dicom_files = [data_dir+dicom_files[index] for index in echo_indices]

		# nii_dir = convert_dcm_dir(data_dir)
	elif "nii" in data_dir:
		nii_dir = data_dir
	else:
		raise RuntimeError("Format of files in path is ambiguous (we determine the format frm the path, and not the extension). Most likely your path contains both 'nii' and 'dicom'.")

	realigner = pe.Node(interface=FmriRealign4d(), name='realign')
	# realigner.inputs.in_files = 'somefuncrun.nii'
	realigner.inputs.tr = 1.5
	# realigner.inputs.in_file = "in_files"
	realigner.inputs.slice_order = range(0,20)

	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = workflow_base
	workflow.connect([
		(stacker, realigner, [('out_file', 'in_file')])
		])
	workflow.run()

if __name__ == "__main__":
	preproc_workflow("/home/chymera/data2/dc.rs/export_ME/dicom/4459/1/EPI/")
