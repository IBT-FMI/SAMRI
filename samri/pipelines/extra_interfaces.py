from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, File, Str, TraitedSpec, Directory, CommandLineInputSpec, CommandLine, InputMultiPath, isdefined, Bunch, OutputMultiPath
from nipype.interfaces.ants.base import ANTSCommand, ANTSCommandInputSpec
from nipype.interfaces.fsl.base import FSLCommandInputSpec, FSLCommand
from nibabel import load

import csv
import math
import numpy as np
import os
import shutil

def scale_timings(timelist, input_units, output_units, time_repetition):
	"""Scales timings given input and output units (scans/secs)

	Parameters
	----------

	timelist: list of times to scale
	input_units: 'secs' or 'scans'
	output_units: Ibid.
	time_repetition: float in seconds

	"""
	if input_units == output_units:
		_scalefactor = 1.

	if (input_units == 'scans') and (output_units == 'secs'):
		_scalefactor = time_repetition

	if (input_units == 'secs') and (output_units == 'scans'):
		_scalefactor = 1. / time_repetition
	timelist = [np.max([0., _scalefactor * t]) for t in timelist]
	return timelist

def bids_gen_info(bids_event_files,
				  condition_column='trial_type',
				  amplitude_column=None,
				  time_repetition=False,
				  ):
	"""Generate subject_info structure from a list of BIDS .tsv event files.

	Parameters
	----------

	bids_event_files : list of str
		Filenames of BIDS .tsv event files containing columns including:
		'onset', 'duration', and 'trial_type' or the `condition_column` value.
	condition_column : str or bool
		Column of files in `bids_event_files` based on the values of which
		events will be sorted into different regressors. If parameter evaluates
		as `False`, all events are modelled in the same regressor, named 'e0'.
	amplitude_column : str
		Column of files in `bids_event_files` based on the values of which
		to apply amplitudes to events. If unspecified, all events will be
		represented with an amplitude of 1.

	Returns
	-------

	list of Bunch
	"""
	info = []
	for bids_event_file in bids_event_files:
		with open(bids_event_file) as f:
			f_events = csv.DictReader(f, skipinitialspace=True, delimiter='\t')
			events = [{k: v for k, v in row.items()} for row in f_events]
		if not condition_column:
			condition_column = '_trial_type'
			for i in events:
				i.update({condition_column:'ev0'})
		conditions = list(set([i[condition_column] for i in events]))
		conditions = sorted(conditions)
		runinfo = Bunch(conditions=[], onsets=[], durations=[], amplitudes=[])
		for condition in conditions:
			selected_events = [i for i in events if i[condition_column]==condition]
			onsets = [float(i['onset']) for i in selected_events]
			durations = [float(i['duration']) for i in selected_events]
			if time_repetition:
				decimals = math.ceil(-math.log10(time_repetition))
				onsets = [np.round(i, decimals) for i in onsets]
				durations = [np.round(i ,decimals) for i in durations]
			runinfo.conditions.append(condition)
			runinfo.onsets.append(onsets)
			runinfo.durations.append(durations)
			try:
				amplitudes = [float(i[amplitude_column]) for i in selected_events]
				runinfo.amplitudes.append(amplitudes)
			except KeyError:
				runinfo.amplitudes.append([1] * len(onsets))
		info.append(runinfo)
	return info


def gen_info(run_event_files):
	"""Generate subject_info structure from a list of event files
	"""
	info = []
	for i, event_files in enumerate(run_event_files):
		runinfo = Bunch(conditions=[], onsets=[], durations=[], amplitudes=[])
		for event_file in event_files:
			_, name = os.path.split(event_file)
			if '.run' in name:
				name, _ = name.split('.run%03d' % (i + 1))
			elif '.txt' in name:
				name, _ = name.split('.txt')

			runinfo.conditions.append(name)
			event_info = np.atleast_2d(np.loadtxt(event_file))
			runinfo.onsets.append(event_info[:, 0].tolist())
			if event_info.shape[1] > 1:
				runinfo.durations.append(event_info[:, 1].tolist())
			else:
				runinfo.durations.append([0])

			if event_info.shape[1] > 2:
				runinfo.amplitudes.append(event_info[:, 2].tolist())
			else:
				delattr(runinfo, 'amplitudes')
		info.append(runinfo)
	return info


class SpecifyModelInputSpec(BaseInterfaceInputSpec):
	subject_info = InputMultiPath(
		Bunch,
		mandatory=True,
		xor=['subject_info', 'event_files', 'bids_event_file'],
		desc='Bunch or List(Bunch) subject-specific '
		'condition information. see '
		':ref:`SpecifyModel` or '
		'SpecifyModel.__doc__ for details')
	event_files = InputMultiPath(
		traits.List(File(exists=True)),
		mandatory=True,
		xor=['subject_info', 'event_files', 'bids_event_file'],
		desc='List of event description files 1, 2 or 3 '
		'column format corresponding to onsets, '
		'durations and amplitudes')
	bids_event_file = InputMultiPath(
		File(exists=True),
		mandatory=True,
		xor=['subject_info', 'event_files', 'bids_event_file'],
		desc='TSV event file containing common BIDS fields: `onset`,'
		'`duration`, and categorization and amplitude columns')
	bids_condition_column = traits.Str(exists=True,
		mandatory=False,
		default_value='trial_type',
		usedefault=True,
		desc='Column of the file passed to `bids_event_file` to the '
		'unique values of which events will be assigned'
		'to regressors')
	bids_amplitude_column = traits.Str(exists=True,
		mandatory=False,
		desc='Column of the file passed to `bids_event_file` '
		'according to which to assign amplitudes to events')
	realignment_parameters = InputMultiPath(
		File(exists=True),
		desc='Realignment parameters returned '
		'by motion correction algorithm',
		copyfile=False)
	parameter_source = traits.Enum(
		"SPM",
		"FSL",
		"AFNI",
		"FSFAST",
		"NIPY",
		usedefault=True,
		desc="Source of motion parameters")
	outlier_files = InputMultiPath(
		File(exists=True),
		desc='Files containing scan outlier indices '
		'that should be tossed',
		copyfile=False)
	functional_runs = InputMultiPath(
		traits.Either(traits.List(File(exists=True)), File(exists=True)),
		mandatory=True,
		desc='Data files for model. List of 4D '
		'files or list of list of 3D '
		'files per session',
		copyfile=False)
	input_units = traits.Enum(
		'secs',
		'scans',
		mandatory=True,
		desc='Units of event onsets and durations (secs '
		'or scans). Output units are always in secs')
	high_pass_filter_cutoff = traits.Float(
		mandatory=True, desc='High-pass filter cutoff in secs')
	time_repetition = traits.Float(
		mandatory=True,
		desc='Time between the start of one volume '
		'to the start of  the next image volume.')
	# Not implemented yet
	# polynomial_order = traits.Range(0, low=0,
	#		desc ='Number of polynomial functions to model high pass filter.')


class SpecifyModelOutputSpec(TraitedSpec):
	session_info = traits.Any(desc='Session info for level1designs')


class SpecifyModel(BaseInterface):
	"""Makes a model specification compatible with spm/fsl designers.

	The subject_info field should contain paradigm information in the form of
	a Bunch or a list of Bunch. The Bunch should contain the following
	information::

	 [Mandatory]
	 - conditions : list of names
	 - onsets : lists of onsets corresponding to each condition
	 - durations : lists of durations corresponding to each condition. Should be
	 left to a single 0 if all events are being modelled as impulses.

	 [Optional]
	 - regressor_names : list of str
		 list of names corresponding to each column. Should be None if
		 automatically assigned.
	 - regressors : list of lists
		values for each regressor - must correspond to the number of
		volumes in the functional run
	 - amplitudes : lists of amplitudes for each event. This will be ignored by
	   SPM's Level1Design.

	 The following two (tmod, pmod) will be ignored by any Level1Design class
	 other than SPM:

	 - tmod : lists of conditions that should be temporally modulated. Should
	   default to None if not being used.
	 - pmod : list of Bunch corresponding to conditions
	   - name : name of parametric modulator
	   - param : values of the modulator
	   - poly : degree of modulation

	Alternatively, you can provide information through event files.

	The event files have to be in 1, 2 or 3 column format with the columns
	corresponding to Onsets, Durations and Amplitudes and they have to have the
	name event_name.runXXX... e.g.: Words.run001.txt. The event_name part will
	be used to create the condition names.

	Examples
	--------

	>>> from nipype.algorithms import modelgen
	>>> from nipype.interfaces.base import Bunch
	>>> s = modelgen.SpecifyModel()
	>>> s.inputs.input_units = 'secs'
	>>> s.inputs.functional_runs = ['functional2.nii', 'functional3.nii']
	>>> s.inputs.time_repetition = 6
	>>> s.inputs.high_pass_filter_cutoff = 128.
	>>> evs_run2 = Bunch(conditions=['cond1'], onsets=[[2, 50, 100, 180]], durations=[[1]])
	>>> evs_run3 = Bunch(conditions=['cond1'], onsets=[[30, 40, 100, 150]], durations=[[1]])
	>>> s.inputs.subject_info = [evs_run2, evs_run3]

	Using pmod:

	>>> evs_run2 = Bunch(conditions=['cond1', 'cond2'], onsets=[[2, 50], [100, 180]], \
durations=[[0], [0]], pmod=[Bunch(name=['amp'], poly=[2], param=[[1, 2]]), \
None])
	>>> evs_run3 = Bunch(conditions=['cond1', 'cond2'], onsets=[[20, 120], [80, 160]], \
durations=[[0], [0]], pmod=[Bunch(name=['amp'], poly=[2], param=[[1, 2]]), \
None])
	>>> s.inputs.subject_info = [evs_run2, evs_run3]

	"""
	input_spec = SpecifyModelInputSpec
	output_spec = SpecifyModelOutputSpec

	def _generate_standard_design(self,
								  infolist,
								  functional_runs=None,
								  realignment_parameters=None,
								  outliers=None):
		""" Generates a standard design matrix paradigm given information about
			each run
		"""
		sessinfo = []
		output_units = 'secs'
		if 'output_units' in self.inputs.traits():
			output_units = self.inputs.output_units

		for i, info in enumerate(infolist):
			sessinfo.insert(i, dict(cond=[]))
			if isdefined(self.inputs.high_pass_filter_cutoff):
				sessinfo[i]['hpf'] = \
					np.float(self.inputs.high_pass_filter_cutoff)

			if hasattr(info, 'conditions') and info.conditions is not None:
				for cid, cond in enumerate(info.conditions):
					sessinfo[i]['cond'].insert(cid, dict())
					sessinfo[i]['cond'][cid]['name'] = info.conditions[cid]
					scaled_onset = scale_timings(
						info.onsets[cid], self.inputs.input_units,
						output_units, self.inputs.time_repetition)
					sessinfo[i]['cond'][cid]['onset'] = scaled_onset
					scaled_duration = scale_timings(
						info.durations[cid], self.inputs.input_units,
						output_units, self.inputs.time_repetition)
					sessinfo[i]['cond'][cid]['duration'] = scaled_duration
					if hasattr(info, 'amplitudes') and info.amplitudes:
						sessinfo[i]['cond'][cid]['amplitudes'] = \
							info.amplitudes[cid]

					if hasattr(info, 'tmod') and info.tmod and \
							len(info.tmod) > cid:
						sessinfo[i]['cond'][cid]['tmod'] = info.tmod[cid]

					if hasattr(info, 'pmod') and info.pmod and \
							len(info.pmod) > cid:
						if info.pmod[cid]:
							sessinfo[i]['cond'][cid]['pmod'] = []
							for j, name in enumerate(info.pmod[cid].name):
								sessinfo[i]['cond'][cid]['pmod'].insert(j, {})
								sessinfo[i]['cond'][cid]['pmod'][j]['name'] = \
									name
								sessinfo[i]['cond'][cid]['pmod'][j]['poly'] = \
									info.pmod[cid].poly[j]
								sessinfo[i]['cond'][cid]['pmod'][j]['param'] = \
									info.pmod[cid].param[j]

			sessinfo[i]['regress'] = []
			if hasattr(info, 'regressors') and info.regressors is not None:
				for j, r in enumerate(info.regressors):
					sessinfo[i]['regress'].insert(j, dict(name='', val=[]))
					if hasattr(info, 'regressor_names') and \
							info.regressor_names is not None:
						sessinfo[i]['regress'][j]['name'] = \
							info.regressor_names[j]
					else:
						sessinfo[i]['regress'][j]['name'] = 'UR%d' % (j + 1)
					sessinfo[i]['regress'][j]['val'] = info.regressors[j]
			sessinfo[i]['scans'] = functional_runs[i]

		if realignment_parameters is not None:
			for i, rp in enumerate(realignment_parameters):
				mc = realignment_parameters[i]
				for col in range(mc.shape[1]):
					colidx = len(sessinfo[i]['regress'])
					sessinfo[i]['regress'].insert(colidx, dict(
						name='', val=[]))
					sessinfo[i]['regress'][colidx]['name'] = 'Realign%d' % (
						col + 1)
					sessinfo[i]['regress'][colidx]['val'] = mc[:, col].tolist()

		if outliers is not None:
			for i, out in enumerate(outliers):
				numscans = 0
				for f in ensure_list(sessinfo[i]['scans']):
					shape = load(f, mmap=NUMPY_MMAP).shape
					if len(shape) == 3 or shape[3] == 1:
						iflogger.warning('You are using 3D instead of 4D '
										 'files. Are you sure this was '
										 'intended?')
						numscans += 1
					else:
						numscans += shape[3]

				for j, scanno in enumerate(out):
					colidx = len(sessinfo[i]['regress'])
					sessinfo[i]['regress'].insert(colidx, dict(
						name='', val=[]))
					sessinfo[i]['regress'][colidx]['name'] = 'Outlier%d' % (
						j + 1)
					sessinfo[i]['regress'][colidx]['val'] = \
						np.zeros((1, numscans))[0].tolist()
					sessinfo[i]['regress'][colidx]['val'][int(scanno)] = 1
		return sessinfo

	def _generate_design(self, infolist=None):
		"""Generate design specification for a typical fmri paradigm
		"""
		realignment_parameters = []
		if isdefined(self.inputs.realignment_parameters):
			for parfile in self.inputs.realignment_parameters:
				realignment_parameters.append(
					np.apply_along_axis(
						func1d=normalize_mc_params,
						axis=1,
						arr=np.loadtxt(parfile),
						source=self.inputs.parameter_source))
		outliers = []
		if isdefined(self.inputs.outlier_files):
			for filename in self.inputs.outlier_files:
				try:
					outindices = np.loadtxt(filename, dtype=int)
				except IOError:
					outliers.append([])
				else:
					if outindices.size == 1:
						outliers.append([outindices.tolist()])
					else:
						outliers.append(outindices.tolist())

		if infolist is None:
			if isdefined(self.inputs.subject_info):
				infolist = self.inputs.subject_info
			elif isdefined(self.inputs.event_files):
				infolist = gen_info(self.inputs.event_files)
			elif isdefined(self.inputs.bids_event_file):
				infolist = bids_gen_info(
					self.inputs.bids_event_file,
					self.inputs.bids_condition_column,
					self.inputs.bids_amplitude_column,
					self.inputs.time_repetition,
					)
		self._sessinfo = self._generate_standard_design(
			infolist,
			functional_runs=self.inputs.functional_runs,
			realignment_parameters=realignment_parameters,
			outliers=outliers)

	def _run_interface(self, runtime):
		"""
		"""
		self._sessioninfo = None
		self._generate_design()
		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		if not hasattr(self, '_sessinfo'):
			self._generate_design()
		outputs['session_info'] = self._sessinfo

		return outputs


class VoxelResizeInputSpec(BaseInterfaceInputSpec):
	in_file = File(exists=True, mandatory=True)
	out_file = traits.Str(
		default_value="fslorient_out.nii.gz",
		usedefault=True,
		desc="image written after calculations",
		)
	resize_factors = traits.List(
		traits.Int([10,10,10],
		usedefault=True,
		desc="Factor by which to multiply the voxel size in the header",
		))

class VoxelResizeOutputSpec(TraitedSpec):
	out_file = File(exists=True)

class VoxelResize(BaseInterface):
	input_spec = VoxelResizeInputSpec
	output_spec = VoxelResizeOutputSpec

	def _run_interface(self, runtime):
		import nibabel as nb
		nii_file = self.inputs.in_file
		resize_factors = self.inputs.resize_factors

		nii_img = nb.load(nii_file)
		aff = nii_img.affine
		# take original image affine, and scale the voxel size and first voxel coordinates for each dimension
		aff[0] = aff[0]*resize_factors[0]
		aff[1] = aff[1]*resize_factors[1]
		aff[2] = aff[2]*resize_factors[2]
		#apply the affine
		nii_img.set_sform(aff)
		nii_img.set_qform(aff)

		#set the sform and qform codes to "scanner" (other settings will lead to AFNI/meica.py assuming talairach space)
		nii_img.header["qform_code"] = 1
		nii_img.header["sform_code"] = 1

		out_file = self.inputs.out_file
		nii_img.to_filename(out_file)
		self.result = os.path.abspath(out_file)

		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs['out_file'] = self.result
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


class FSLOrientInput(FSLCommandInputSpec):

	in_file = File(exists=True,
		mandatory=True,
		desc="image written after calculations",
		copyfile=True,
		output_name='out_file',
		name_source='dest_file',
		argstr="%s",
		position=1,
		)
	#out_file = traits.Str(
	#	default_value="fslorient_out.nii.gz",
	#	usedefault=True,
	#	desc="image written after calculations",
	#	argstr="%s",
	#	position=1,
	#	)
	main_option = traits.Enum(
		'getorient',
		'getsform',
		'getqform',
		'setsform',
		'setqform',
		'getsformcode',
		'getqformcode',
		'setsformcode',
		'setqformcode',
		'copysform2qform',
		'copyqform2sform',
		'deleteorient',
		'forceradiological',
		'forceneurological',
		'swaporient',
		argstr="-%s",
		position=0,
		)

class FSLOrientOutput(TraitedSpec):

	out_file = File(exists=True, desc="image written after calculations")


class FSLOrient(FSLCommand):

	_cmd = "fslorient"
	input_spec = FSLOrientInput
	output_spec = FSLOrientOutput

	#def run(self, **inputs):
	#	shutil.copyfile(self.inputs.in_file, self.inputs.out_file)
	#	FSLCommand.run(self)

	def _list_outputs(self):
		outputs = self.output_spec().get()
		outputs["out_file"] = self.inputs.in_file
		outputs["out_file"] = os.path.abspath(outputs["out_file"])
		return outputs

class Bru2InputSpec(CommandLineInputSpec):
	input_dir = Directory(
		desc="Input Directory",
		exists=True,
		mandatory=True,
		position=-1,
		argstr="%s")
	actual_size = traits.Bool(
		argstr='-a',
		desc="Keep actual size - otherwise x10 scale so animals match human.")
	force_conversion = traits.Bool(
		argstr='-f',
		desc="Force conversion of localizers images (multiple slice "
		"orientations).")
	compress = traits.Bool(
		argstr='-z', desc='gz compress images (".nii.gz").')
	append_protocol_name = traits.Bool(
		argstr='-p', desc="Append protocol name to output filename.")
	output_filename = traits.Str(
		argstr="-o %s",
		desc='Output filename (".nii" will be appended, or ".nii.gz" if the "-z" compress option is selected)',
		genfile=True)


class Bru2OutputSpec(TraitedSpec):
	nii_file = File(exists=True)


class Bru2(CommandLine):
	"""Uses bru2nii's Bru2 to convert Bruker files

	Examples
	========

	>>> from nipype.interfaces.bru2nii import Bru2
	>>> converter = Bru2()
	>>> converter.inputs.input_dir = "brukerdir"
	>>> converter.cmdline  # doctest: +ELLIPSIS
	'Bru2 -o .../nipype/testing/data/brukerdir brukerdir'
	"""
	input_spec = Bru2InputSpec
	output_spec = Bru2OutputSpec
	_cmd = "Bru2"

	def _list_outputs(self):
		outputs = self._outputs().get()
		if isdefined(self.inputs.output_filename):
			output_filename1 = os.path.abspath(self.inputs.output_filename)
		else:
			output_filename1 = self._gen_filename('output_filename')
		if self.inputs.compress:
			outputs["nii_file"] = output_filename1 + ".nii.gz"
		else:
			outputs["nii_file"] = output_filename1 + ".nii"
		return outputs

	def _gen_filename(self, name):
		if name == 'output_filename':
			outfile = os.path.join(
				os.getcwd(),
				os.path.basename(os.path.normpath(self.inputs.input_dir)))
			return outfile

class CompositeTransformUtilInputSpec(ANTSCommandInputSpec):
	process = traits.Enum('assemble', 'disassemble', argstr='--%s',
		position=1, usedefault=True,
		desc='What to do with the transform inputs (assemble or disassemble)',
		)
	in_file = InputMultiPath(File(exists=True), mandatory=True, argstr='%s...',
		position=2, desc='Input transform file(s)')
	output_prefix = Str("transform", usedefault=True, argstr='%s',
		position=3, desc="A prefix that is prepended to all output files")

class CompositeTransformUtilOutputSpec(TraitedSpec):
	affine_transform = File(exists=True, desc="Affine transform component",
			mandatory=True, position=2)
	displacement_field = File(desc="Displacement field component")

class CompositeTransformUtil(ANTSCommand):
	"""
	ANTs utility which can combine or break apart transform files into their individual
	constituent components.

	Examples
	--------

	>>> from nipype.interfaces.ants import CompositeTransformUtil
	>>> tran = CompositeTransformUtil()
	>>> tran.inputs.process = 'disassemble'
	>>> tran.inputs.in_file = 'output_Composite.h5'
	>>> reg.cmdline
	'CompositeTransformUtil --disassemble output_Composite.h5 transform'
	>>> reg.run()  # doctest: +SKIP
	"""

	_cmd = 'CompositeTransformUtil'
	input_spec = CompositeTransformUtilInputSpec
	output_spec = CompositeTransformUtilOutputSpec

	def _num_threads_update(self):
		"""
		CompositeTransformUtil ignores environment variables,
		so override environment update from ANTSCommand class
		"""
		pass

	def _format_arg(self, name, spec, value):
		if name == 'output_prefix' and self.inputs.process == 'assemble':
			value = ''
		return super(CompositeTransformUtil, self)._format_arg(name, spec, value)

	def _list_outputs(self):
		outputs = self.output_spec().get()
		outputs['affine_transform'] = os.path.abspath(
			'00_'+self.inputs.output_prefix+'_AffineTransform.mat')
		outputs['displacement_field'] = os.path.abspath(
			'01_'+self.inputs.output_prefix+'_DisplacementFieldTransform.nii.gz')
		return outputs
