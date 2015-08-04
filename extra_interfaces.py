from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, File, TraitedSpec, Directory, CommandLineInputSpec, CommandLine, InputMultiPath
from nipype.utils.filemanip import split_filename

import nibabel as nb
import numpy as np
import os

class DcmToNiiInputSpec(BaseInterfaceInputSpec):
	dcm_dir = Directory(exists=True, mandatory=True)
	group_by = traits.Str(desc='everything below this value will be set to zero', mandatory=False)

class DcmToNiiOutputSpec(TraitedSpec):
	nii_files = traits.List(File(exists=True))
	echo_times = traits.List(traits.Float(exists=True))

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
		outputs["echo_times"] = self.result[1]
		return outputs

class VoxelResizeInputSpec(BaseInterfaceInputSpec):
	nii_files = traits.List(File(exists=True, mandatory=True))
	resize_factor = traits.Int(10, usedefault=True, desc="Factor by which to multiply the voxel size in the header")

class VoxelResizeOutputSpec(TraitedSpec):
	resized_files = traits.List(File(exists=True))

class VoxelResize(BaseInterface):
	input_spec = VoxelResizeInputSpec
	output_spec = VoxelResizeOutputSpec

	def _run_interface(self, runtime):
		import nibabel as nb
		nii_files = self.inputs.nii_files
		resize_factor = self.inputs.resize_factor

		self.result = []
		for nii_file in nii_files:
			nii_img = nb.load(nii_file)
			nii_img.header["pixdim"][1:4] = nii_img.header["pixdim"][1:4]*resize_factor

			_, fname = os.path.split(nii_file)
			nii_img.to_filename(fname)
			self.result.append(os.path.abspath(fname))
		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs["resized_files"] = self.result
		return outputs

class MEICAInputSpec(CommandLineInputSpec):
	echo_files = traits.List(File(exists=True), mandatory=True, position=0, argstr="-d %s", desc="4D files, for each echo time (called DSINPUTS by meica.py)")
	echo_times = traits.List(traits.Float(), mandatory=True, position=1, argstr="-e %s", desc='Echo times (in ms) corresponding to the input files (called TES by meica.py)')
	anatomical_dataset = File(exists=True, argstr="-a%s", desc='ex: -a mprage.nii.gz  Anatomical dataset (optional)')
	basetime = traits.Str(argstr="-b %s", desc="ex: -b 10s OR -b 10v  Time to steady-state equilibration in seconds(s) or volumes(v). Default 0.")
	wrap_to_mni = traits.Bool(False, usedefault=True, argstr='--MNI', desc="Warp to MNI space using high-resolution template")
	TR = traits.Float(argstr="--TR=%s", desc='The TR. Default read from input dataset header')
	tpattern = traits.Str(argstr="--tpattern=%s", desc='Slice timing (i.e. alt+z, see 3dTshift -help). Default from header. (N.B. This is important!)')
	cpus = traits.Int(argstr="--cpus=%d", desc=' Maximum number of CPUs (OpenMP threads) to use. Default 2.')
	no_despike = traits.Bool(False, usedefault=True, argstr='--no_despike', desc="Do not de-spike functional data. Default is to despike, recommended.")
	qwarp = traits.Bool(False, usedefault=True, argstr='--no_despike', desc=" Nonlinear anatomical normalization to MNI (or --space template) using 3dQWarp, after affine")

class MEICAOutputSpec(TraitedSpec):
	nii_files = File(exists=True)

class MEICA(CommandLine):
	input_spec = MEICAInputSpec
	output_spec = MEICAOutputSpec
	_cmd = "meica.py"

	def _format_arg(self, name, spec, value):

		if name in ["echo_files", "echo_times"]:
			return spec.argstr % ",".join(map(str, value))
		return super(MEICA, self)._format_arg(name, spec, value)

	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs["nii_files"] = self.result
		return outputs
