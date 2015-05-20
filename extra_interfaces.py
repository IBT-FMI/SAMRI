from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, File, TraitedSpec, Directory
from nipype.utils.filemanip import split_filename

import nibabel as nb
import numpy as np
import os

class DcmToNiiInputSpec(BaseInterfaceInputSpec):
	dcm_dir = Directory(exists=True, mandatory=True)
	group_by = traits.Str(desc='everything below this value will be set to zero', mandatory=False)

class DcmToNiiOutputSpec(TraitedSpec):
	nii_files = traits.List(File(exists=True))

class DcmToNii(BaseInterface):
	input_spec = DcmToNiiInputSpec
	output_spec = DcmToNiiOutputSpec

	def _run_interface(self, runtime):
		from functions_preprocessing import dcm_to_nii
		dcm_dir = self.inputs.dcm_dir
		group_by = self.inputs.group_by
		dcm_to_nii(dcm_dir, group_by)
		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		print outputs
		print self.result
		outputs["nii_files"] = self.result
		return outputs
