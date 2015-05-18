import nipype.pipeline.engine as pe				# workflow and node wrappers
import os										# system functions
import nipype.interfaces.freesurfer as fs		# freesurfer
import nipype.interfaces.utility as util		# utility
import nipype.pipeline.engine as pe				# pypeline engine
from nipype.interfaces.utility import Function	# wrap your own functions
import nipype.interfaces.dcmstack as dcmstack
from dcmstack.extract import default_extractor
from nipype.interfaces.nipy.preprocess import FmriRealign4d
from os import listdir
from dicom import read_file
import numpy as np
from functions_preprocessing import *

dcm_to_nii_imports = ["import nipype.interfaces.dcmstack as dcmstack",
					"from dcmstack.extract import minimal_extractor",
					"from dicom import read_file",
					"from os import listdir, path, makedirs"]

def preproc_workflow(data_dir, workflow_base=".", force_convert=False):

	dcm_to_nii_function = Function(input_names=["dicom_dir", "d5_key"],
										output_names=['out_file'],
										function=dcm_to_nii,
										imports=dcm_to_nii_imports)

	stacker = pe.Node(name="dcm_to_nii", interface=dcm_to_nii_function)
	stacker.inputs.dicom_dir = data_dir
	stacker.inputs.d5_key = "EchoTime"

	realigner = pe.Node(interface=FmriRealign4d(), name='realign')
	realigner.inputs.tr = 1.5
	realigner.inputs.time_interp = True
	realigner.inputs.slice_order = range(0,20)[::2]+range(0,20)[1::2]

	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = workflow_base
	workflow.connect([
		(stacker, realigner, [('out_file', 'in_file')])
		])
	workflow.run()

if __name__ == "__main__":
	preproc_workflow("/home/chymera/data/dc.rs/export_ME/dicom/4459/1/EPI/")
