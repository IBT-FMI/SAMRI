import nipype.pipeline.engine as pe
from nipype.interfaces.utility import Function
import os
import dcmstack
from functions_preprocessing import convert_dcm_to_nii

data_dir = "/home/chymera/data/dc.rs/export_ME/dicom/4457/1/EPI/"
file_list = [data_dir+file for file in os.listdir(data_dir)]

imports_parse_and_stack = ["import os",
			"from dcmstack import*",
			"from dcmstack.dcmstack import *",
			"import warnings, re, dicom",
			"from copy import deepcopy",
			"import nibabel as nb",
			"from nibabel.nifti1 import Nifti1Extensions",
			"from nibabel.spatialimages import HeaderDataError",
			"from nibabel.orientations import (io_orientation, apply_orientation, inv_ornt_aff)",
			"import numpy as np"
			]

imports_convert_dcm_to_nii = ["import nipype.interfaces.dcmstack as dcmstack",
							"from dcmstack.extract import minimal_extractor",
							"from dicom import read_file",
							"from os import listdir, path, makedirs"]

default_group_keys =  ('SeriesInstanceUID',
						'SeriesNumber',
						'ProtocolName',
						'ImageOrientationPatient')

# def parse_and_stack_wrapper(src_paths, group_by=default_group_keys, extractor=None, force=False, warn_on_except=False):
# 	from dcmstack import parse_and_stack
# 	return parse_and_stack(src_paths, group_by=group_by, extractor=extractor, force=force, warn_on_except=warn_on_except)
#
#
# parser_stacker_function = Function(input_names=["src_paths", "group_by", "extractor", "force", "warn_on_except", "**stack_args"],
# 									output_names=['out_file'],
# 									function=dcmstack.dcmstack.parse_and_stack,
# 									imports=imports)
#
# parser_stacker = pe.Node(name="parsestacker", interface=parser_stacker_function)
# parser_stacker.inputs.src_paths = file_list[:20]
# parser_stacker.inputs.group_by = "EchoTime"

convert_dcm_to_nii_function = Function(input_names=["dicom_dir", "d5_key"],
									output_names=['out_file'],
									function=convert_dcm_to_nii,
									imports=imports_convert_dcm_to_nii)

dcm_to_nii = pe.Node(name="dcm_to_nii", interface=convert_dcm_to_nii_function)
dcm_to_nii.inputs.dicom_dir = data_dir
dcm_to_nii.inputs.d5_key = "EchoTime"

pipeline = pe.Workflow(name='nipype_demo')
pipeline.add_nodes([dcm_to_nii])
pipeline.run()
pipeline.write_graph(graph2use='flat')
