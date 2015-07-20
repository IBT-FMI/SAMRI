from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, File, TraitedSpec, Directory, CommandLineInputSpec, CommandLine
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
		from extra_functions import dcm_to_nii
		dcm_dir = self.inputs.dcm_dir
		group_by = self.inputs.group_by
		self.result = dcm_to_nii(dcm_dir, group_by, node=True)
		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs["nii_files"] = self.result[0]
		outputs["nii_files"] = self.result[1]
		return outputs


class MEICAInputSpec(CommandLineInputSpec):
	echo_files = traits.List(File(exists=True, mandatory=True))
	group_by = traits.Str(desc='everything below this value will be set to zero', mandatory=False)

class MEICAOutputSpec(TraitedSpec):
	nii_files = traits.List(File(exists=True))

class MEICA(CommandLine):
	input_spec = DcmToNiiInputSpec
	output_spec = DcmToNiiOutputSpec

	def _run_interface(self, runtime):
		from extra_functions import dcm_to_nii
		dcm_dir = self.inputs.dcm_dir
		group_by = self.inputs.group_by
		self.result = dcm_to_nii(dcm_dir, group_by, node=True)
		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs["nii_files"] = self.result
		return outputs
