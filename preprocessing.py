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
import numpy as np
from functions_preprocessing import *
from extra_interfaces import DcmToNii

def preproc_workflow(data_dir, workflow_base=".", force_convert=False):
	stacker = pe.Node(name="dcm_to_nii", interface=DcmToNii())
	stacker.inputs.dcm_dir = data_dir
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
	preproc_workflow("/home/chymera/data/dc.rs/export_ME/dicom/4459/1/EPI/", workflow_base="/home/chymera/data/dc.rs/export_ME/")
