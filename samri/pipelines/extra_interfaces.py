from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, traits, File, TraitedSpec, Directory, CommandLineInputSpec, CommandLine, InputMultiPath, isdefined, Bunch, OutputMultiPath, load_template
from nipype.interfaces.afni.base import AFNICommandOutputSpec, AFNICommandInputSpec, AFNICommand
from nipype.utils.filemanip import split_filename
from itertools import product
from nibabel import load

import nibabel as nb
import numpy as np
import csv
import os

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


def gen_info(run_event_files, habituation_regressor):
	"""Generate subject_info structure from a list of event files or a multirow event file.
	"""
	info = []
	for i, event_file in enumerate(run_event_files):
		runinfo = Bunch(conditions=[], onsets=[], durations=[], amplitudes=[])
		if event_file.endswith(".tsv"):
			with open(event_file) as tsv:
				eventfile_data = list(csv.reader(tsv, delimiter="\t"))
				if isinstance(eventfile_data[0][0], str):
					eventfile_data = eventfile_data[1:]
				eventfile_data_ = []
				for sublist in eventfile_data:
					sublist_ = []
					for i in sublist:
						try:
							i_ = round(float(i))
						except ValueError:
							i_ = i
						sublist_.append(i_)
					eventfile_data_.append(sublist_)
				eventfile_data = eventfile_data_
				name = "e0"
				onsets = [i[0] for i in eventfile_data]
				durations = [i[1] for i in eventfile_data]
				amplitudes = [i[2] for i in eventfile_data]
				runinfo.conditions.append(name)
				runinfo.onsets.append(onsets)
				runinfo.durations.append(durations)
				runinfo.amplitudes.append(amplitudes)
				if habituation_regressor:
					name = "e1"
					onsets = [i[0] for i in eventfile_data]
					durations = [i[1] for i in eventfile_data]
					amplitudes = [len(eventfile_data)-i for i in range(len(eventfile_data))]
					runinfo.conditions.append(name)
					runinfo.onsets.append(onsets)
					runinfo.durations.append(durations)
					runinfo.amplitudes.append(amplitudes)
		else:
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
	subject_info = InputMultiPath(Bunch, mandatory=True, xor=['subject_info',
															  'event_files'],
								  desc=("Bunch or List(Bunch) subject specific condition information. "
										"see :ref:`SpecifyModel` or SpecifyModel.__doc__ for details"))
	event_files = InputMultiPath(traits.Either(traits.List(File(exists=True)),File(exists=True)), mandatory=True,
								 xor=['subject_info', 'event_files'],
								 desc=('list of event description files 1, 2 or 3 column format '
									   'corresponding to onsets, durations and amplitudes'))
	realignment_parameters = InputMultiPath(File(exists=True),
											desc="Realignment parameters returned by motion correction algorithm",
											copyfile=False)
	outlier_files = InputMultiPath(File(exists=True),
								   desc="Files containing scan outlier indices that should be tossed",
								   copyfile=False)
	functional_runs = InputMultiPath(traits.Either(traits.List(File(exists=True)),
												   File(exists=True)),
									 mandatory=True,
									 desc=("Data files for model. List of 4D files or list of list of 3D "
										   "files per session"), copyfile=False)
	input_units = traits.Enum('secs', 'scans', mandatory=True,
							  desc=("Units of event onsets and durations (secs or scans). Output "
									"units are always in secs"))
	high_pass_filter_cutoff = traits.Float(mandatory=True,
										   desc="High-pass filter cutoff in secs")
	time_repetition = traits.Float(mandatory=True,
								   desc=("Time between the start of one volume to the start of "
										 "the next image volume."))
	habituation_regressor = traits.Bool(mandatory=False,default=False)
	# Not implemented yet
	# polynomial_order = traits.Range(0, low=0,
	#		desc ="Number of polynomial functions to model high pass filter.")


class SpecifyModelOutputSpec(TraitedSpec):
	session_info = traits.Any(desc="session info for level1designs")


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

	>>> from nipype.interfaces.base import Bunch
	>>> s = SpecifyModel()
	>>> s.inputs.input_units = 'secs'
	>>> s.inputs.functional_runs = ['functional2.nii', 'functional3.nii']
	>>> s.inputs.time_repetition = 6
	>>> s.inputs.high_pass_filter_cutoff = 128.
	>>> info = [Bunch(conditions=['cond1'], onsets=[[2, 50, 100, 180]],\
					  durations=[[1]]), \
				Bunch(conditions=['cond1'], onsets=[[30, 40, 100, 150]], \
					  durations=[[1]])]
	>>> s.inputs.subject_info = info

	Using pmod:

	>>> info = [Bunch(conditions=['cond1', 'cond2'], \
					  onsets=[[2, 50],[100, 180]], durations=[[0],[0]], \
					  pmod=[Bunch(name=['amp'], poly=[2], param=[[1, 2]]),\
					  None]), \
				Bunch(conditions=['cond1', 'cond2'], \
					  onsets=[[20, 120],[80, 160]], durations=[[0],[0]], \
					  pmod=[Bunch(name=['amp'], poly=[2], param=[[1, 2]]), \
					  None])]
	>>> s.inputs.subject_info = info

	"""
	input_spec = SpecifyModelInputSpec
	output_spec = SpecifyModelOutputSpec

	def _generate_standard_design(self, infolist,
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
					scaled_onset = scale_timings(info.onsets[cid],
												 self.inputs.input_units,
												 output_units,
												 self.inputs.time_repetition)
					sessinfo[i]['cond'][cid]['onset'] = scaled_onset
					scaled_duration = scale_timings(info.durations[cid],
													self.inputs.input_units,
													output_units,
													self.inputs.time_repetition)
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
					sessinfo[i]['regress'].insert(colidx, dict(name='', val=[]))
					sessinfo[i]['regress'][colidx]['name'] = 'Realign%d' % (col + 1)
					sessinfo[i]['regress'][colidx]['val'] = mc[:, col].tolist()
		if outliers is not None:
			for i, out in enumerate(outliers):
				numscans = 0
				for f in filename_to_list(sessinfo[i]['scans']):
					shape = load(f).shape
					if len(shape) == 3 or shape[3] == 1:
						iflogger.warning(("You are using 3D instead of 4D "
										  "files. Are you sure this was "
										  "intended?"))
						numscans += 1
					else:
						numscans += shape[3]
				for j, scanno in enumerate(out):
					colidx = len(sessinfo[i]['regress'])
					sessinfo[i]['regress'].insert(colidx, dict(name='', val=[]))
					sessinfo[i]['regress'][colidx]['name'] = 'Outlier%d' % (j + 1)
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
				realignment_parameters.append(np.loadtxt(parfile))
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
			else:
				infolist = gen_info(self.inputs.event_files, self.inputs.habituation_regressor)
		self._sessinfo = self._generate_standard_design(infolist,
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




class GenL2ModelInputSpec(BaseInterfaceInputSpec):
	num_copes = traits.Range(low=1, mandatory=True, desc='number of copes to be combined')
	conditions = traits.List(mandatory=True)
	subjects = traits.List(mandatory=True)
	# contrasts = traits.List(traits.Str(), default=["group mean"])

class GenL2ModelOutputSpec(TraitedSpec):
	design_mat = File(exists=True, desc='design matrix file')
	design_con = File(exists=True, desc='design contrast file')
	design_grp = File(exists=True, desc='design group file')

class GenL2Model(BaseInterface):
	"""Generate subject specific second level model

	Examples
	--------

	>>> from nipype.interfaces.fsl import L2Model
	>>> model = L2Model(num_copes=3) # 3 sessions

	"""

	input_spec = GenL2ModelInputSpec
	output_spec = GenL2ModelOutputSpec

	def _run_interface(self, runtime):
		cwd = os.getcwd()
		num_conditions=len(self.inputs.conditions)
		num_subjects=len(self.inputs.subjects)
		num_copes = int(num_conditions * num_subjects)
		num_waves = int(1 + num_subjects)
		mat_txt = ['/NumWaves	{}'.format(num_waves),
					'/NumPoints	{}'.format(num_copes),
					'/PPheights	{}'.format(1),
					'',
					'/Matrix']
		for condition, subject in product(range(num_conditions),range(num_subjects)):
			new_line = [0] * num_waves
			if condition == 0:
				new_line[0] = -1
			if condition == 1:
				new_line[0] = 1
			new_line[1+subject] = 1
			new_line = [str(i) for i in new_line]
			new_line = " ".join(new_line)
			mat_txt += [new_line]
		mat_txt = '\n'.join(mat_txt)

		con_txt = ['/ContrastName1   post > pre',
					'/NumWaves	   {}'.format(num_waves),
					'/NumContrasts   {}'.format(num_conditions-1),
					'/PPheights		  {}'.format(1),
					'',
					'/Matrix']
		con_txt += ["1" + "".join(" 0"*num_subjects)]
		con_txt = '\n'.join(con_txt)

		grp_txt = ['/NumWaves	1',
					'/NumPoints	{}'.format(num_copes),
					'',
					'/Matrix']
		for i in range(num_conditions):
			for subject in range(num_subjects):
				#write subject+1 in the innermost parantheses to have per-subject variance structure, or 1 for glob variance, the numbering has to start at 1, not 0
				grp_txt += [str(1)]
		grp_txt = '\n'.join(grp_txt)

		txt = {'design.mat': mat_txt,
				'design.con': con_txt,
				'design.grp': grp_txt}

		# write design files
		for i, name in enumerate(['design.mat', 'design.con', 'design.grp']):
			f = open(os.path.join(cwd, name), 'wt')
			f.write(txt[name])
			f.close()

		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		for field in list(outputs.keys()):
			outputs[field] = os.path.join(os.getcwd(),field.replace('_', '.'))
		return outputs


class SubjectInfoInputSpec(BaseInterfaceInputSpec):
	conditions = traits.List(traits.Str(exists=True))
	durations = traits.List(traits.List(traits.Float(exists=True)))
	measurement_delay = traits.Float(exists=True, mandatory=True)
	onsets = traits.List(traits.List(traits.Float(exists=True)))

class SubjectInfoOutputSpec(TraitedSpec):
	information = traits.List(Bunch())

class SubjectInfo(BaseInterface):
	input_spec = SubjectInfoInputSpec
	output_spec = SubjectInfoOutputSpec

	def _run_interface(self, runtime):
		conditions = self.inputs.conditions
		durations = self.inputs.durations
		measurement_delay = self.inputs.measurement_delay
		onsets = self.inputs.onsets
		for idx_a, a in enumerate(onsets):
			for idx_b, b in enumerate(a):
				onsets[idx_a][idx_b] = b-measurement_delay

		self.results = Bunch(conditions=conditions, onsets=onsets, durations=durations)

		return runtime

	def _list_outputs(self):
		outputs = self._outputs().get()
		outputs["information"] = [self.results]
		return outputs


class VoxelResizeInputSpec(BaseInterfaceInputSpec):
	nii_files = traits.List(File(exists=True, mandatory=True))
	resize_factors = traits.List(traits.Int([10,10,10], usedefault=True, desc="Factor by which to multiply the voxel size in the header"))

class VoxelResizeOutputSpec(TraitedSpec):
	resized_files = traits.List(File(exists=True))

class VoxelResize(BaseInterface):
	input_spec = VoxelResizeInputSpec
	output_spec = VoxelResizeOutputSpec

	def _run_interface(self, runtime):
		import nibabel as nb
		nii_files = self.inputs.nii_files
		resize_factors = self.inputs.resize_factors

		self.result = []
		for nii_file in nii_files:
			nii_img = nb.load(nii_file)
			aff = nii_img.affine
			# take original image affine, and scale the voxel size and first voxel coordinates for each dimension
			aff[0,0] = aff[0,0]*resize_factors[0]
			aff[0,3] = aff[0,3]*resize_factors[0]
			aff[1,1] = aff[1,1]*resize_factors[1]
			aff[1,3] = aff[1,3]*resize_factors[1]
			aff[2,2] = aff[2,2]*resize_factors[2]
			aff[2,3] = aff[2,3]*resize_factors[2]
			#apply the affine
			nii_img.set_sform(aff)
			nii_img.set_qform(aff)

			#set the sform and qform codes to "scanner" (other settings will lead to AFNI/meica.py assuming talairach space)
			nii_img.header["qform_code"] = 1
			nii_img.header["sform_code"] = 1

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

class Level1DesignInputSpec(BaseInterfaceInputSpec):
	interscan_interval = traits.Float(mandatory=True,
									  desc='Interscan  interval (in secs)')
	session_info = traits.Any(mandatory=True,
							  desc=('Session specific information generated '
									'by ``modelgen.SpecifyModel``'))
	bases = traits.Either(
		traits.Dict(traits.Enum(
			'dgamma'), traits.Dict(traits.Enum('derivs'), traits.Bool)),
		traits.Dict(traits.Enum('gamma'), traits.Dict(
					traits.Enum('derivs', 'gammasigma', 'gammadelay'))),
		traits.Dict(traits.Enum('none'), traits.Dict()),
		mandatory=True,
		desc=("name of basis function and options e.g., "
			  "{'dgamma': {'derivs': True}}"))
	orthogonalization = traits.Dict(
		traits.Int, traits.Dict(traits.Int, traits.Either(traits.Bool,traits.Int)),
		mandatory=False,
		default={},
		)
	model_serial_correlations = traits.Bool(
		desc="Option to model serial correlations using an \
autoregressive estimator (order 1). Setting this option is only \
useful in the context of the fsf file. If you set this to False, you need to \
repeat this option for FILMGLS by setting autocorr_noestimate to True",
		mandatory=True)
	contrasts = traits.List(
		traits.Either(traits.Tuple(traits.Str,
								   traits.Enum('T'),
								   traits.List(traits.Str),
								   traits.List(traits.Float)),
					  traits.Tuple(traits.Str,
								   traits.Enum('T'),
								   traits.List(traits.Str),
								   traits.List(traits.Float),
								   traits.List(traits.Float)),
					  traits.Tuple(traits.Str,
								   traits.Enum('F'),
								   traits.List(
									   traits.Either(
										   traits.Tuple(traits.Str,
														traits.Enum('T'),
														traits.List(
															traits.Str),
														traits.List(
															traits.Float)),
										   traits.Tuple(
											   traits.Str,
											   traits.Enum('T'),
											   traits.List(
												   traits.Str),
											   traits.List(
												   traits.Float),
											   traits.List(
												   traits.Float)))))),
		desc="List of contrasts with each contrast being a list of the form - \
[('name', 'stat', [condition list], [weight list], [session list])]. if \
session list is None or not provided, all sessions are used. For F \
contrasts, the condition list should contain previously defined \
T-contrasts.")


class Level1DesignOutputSpec(TraitedSpec):
	fsf_files = OutputMultiPath(File(exists=True),
								desc='FSL feat specification files')
	ev_files = OutputMultiPath(traits.List(File(exists=True)),
							   desc='condition information files')


class Level1Design(BaseInterface):
	"""Generate FEAT specific files

	Examples
	--------

	>>> level1design = Level1Design()
	>>> level1design.inputs.interscan_interval = 2.5
	>>> level1design.inputs.bases = {'dgamma':{'derivs': False}}
	>>> level1design.inputs.session_info = 'session_info.npz'
	>>> level1design.run() # doctest: +SKIP

	"""

	input_spec = Level1DesignInputSpec
	output_spec = Level1DesignOutputSpec

	def _create_ev_file(self, evfname, evinfo):
		f = open(evfname, 'wt')
		for i in evinfo:
			if len(i) == 3:
				f.write('%f %f %f\n' % (i[0], i[1], i[2]))
			else:
				f.write('%f\n' % i[0])
		f.close()

	def _create_ev_files(
		self, cwd, runinfo, runidx, ev_parameters, orthogonalization, contrasts,
			do_tempfilter, basis_key):
		"""Creates EV files from condition and regressor information.

		   Parameters:
		   -----------

		   runinfo : dict
			   Generated by `SpecifyModel` and contains information
			   about events and other regressors.
		   runidx  : int
			   Index to run number
		   design_parameters : dict
			   A dictionary containing the model parameters for the
			   given design type.
		   contrasts : list of lists
			   Information on contrasts to be evaluated
		"""
		conds = {}
		evname = []
		if basis_key == "dgamma":
			basis_key = "hrf"
		elif basis_key == "gamma":
			try:
				_ = ev_parameters['gammasigma']
			except KeyError:
				ev_parameters['gammasigma'] = 3
			try:
				_ = ev_parameters['gammadelay']
			except KeyError:
				ev_parameters['gammadelay'] = 6
		ev_template = load_template('feat_ev_'+basis_key+'.tcl')
		ev_none = load_template('feat_ev_none.tcl')
		ev_ortho = load_template('feat_ev_ortho.tcl')
		ev_txt = ''
		# generate sections for conditions and other nuisance
		# regressors
		num_evs = [0, 0]
		for field in ['cond', 'regress']:
			for i, cond in enumerate(runinfo[field]):
				name = cond['name']
				evname.append(name)
				evfname = os.path.join(cwd, 'ev_%s_%d_%d.txt' % (name, runidx,
																 len(evname)))
				evinfo = []
				num_evs[0] += 1
				num_evs[1] += 1
				if field == 'cond':
					for j, onset in enumerate(cond['onset']):
						try:
							amplitudes = cond['amplitudes']
							if len(amplitudes) > 1:
								amp = amplitudes[j]
							else:
								amp = amplitudes[0]
						except KeyError:
							amp = 1
						if len(cond['duration']) > 1:
							evinfo.insert(j, [onset, cond['duration'][j], amp])
						else:
							evinfo.insert(j, [onset, cond['duration'][0], amp])
					ev_parameters['ev_num'] = num_evs[0]
					ev_parameters['ev_name'] = name
					ev_parameters['tempfilt_yn'] = do_tempfilter
					ev_parameters['cond_file'] = evfname
					try:
						ev_parameters['temporalderiv'] = ev_parameters.pop('derivs')
					except KeyError:
						pass
					else:
						if ev_parameters['temporalderiv']:
							evname.append(name + 'TD')
							num_evs[1] += 1
					ev_txt += ev_template.substitute(ev_parameters)
				elif field == 'regress':
					evinfo = [[j] for j in cond['val']]
					ev_txt += ev_none.substitute(ev_num=num_evs[0],
												 ev_name=name,
												 tempfilt_yn=do_tempfilter,
												 cond_file=evfname)
				ev_txt += "\n"
				conds[name] = evfname
				self._create_ev_file(evfname, evinfo)
		# add ev orthogonalization
		for i in range(1, num_evs[0] + 1):
			for j in range(0, num_evs[0] + 1):
				try:
					orthogonal = int(orthogonalization[i][j])
				except (ValueError, TypeError):
					orthogonal = 0
				ev_txt += ev_ortho.substitute(c0=i, c1=j, orthogonal=orthogonal)
				ev_txt += "\n"
		# add contrast info to fsf file
		if isdefined(contrasts):
			contrast_header = load_template('feat_contrast_header.tcl')
			contrast_prolog = load_template('feat_contrast_prolog.tcl')
			contrast_element = load_template('feat_contrast_element.tcl')
			contrast_ftest_element = load_template(
				'feat_contrast_ftest_element.tcl')
			contrastmask_header = load_template('feat_contrastmask_header.tcl')
			contrastmask_footer = load_template('feat_contrastmask_footer.tcl')
			contrastmask_element = load_template(
				'feat_contrastmask_element.tcl')
			# add t/f contrast info
			ev_txt += contrast_header.substitute()
			con_names = []
			for j, con in enumerate(contrasts):
				con_names.append(con[0])
			con_map = {}
			ftest_idx = []
			ttest_idx = []
			for j, con in enumerate(contrasts):
				if con[1] == 'F':
					ftest_idx.append(j)
					for c in con[2]:
						if c[0] not in list(con_map.keys()):
							con_map[c[0]] = []
						con_map[c[0]].append(j)
				else:
					ttest_idx.append(j)

			for ctype in ['real', 'orig']:
				for j, con in enumerate(contrasts):
					if con[1] == 'F':
						continue
					tidx = ttest_idx.index(j) + 1
					ev_txt += contrast_prolog.substitute(cnum=tidx,
														 ctype=ctype,
														 cname=con[0])
					count = 0
					for c in range(1, len(evname) + 1):
						if evname[c - 1].endswith('TD') and ctype == 'orig':
							continue
						count = count + 1
						if evname[c - 1] in con[2]:
							val = con[3][con[2].index(evname[c - 1])]
						else:
							val = 0.0
						ev_txt += contrast_element.substitute(
							cnum=tidx, element=count, ctype=ctype, val=val)
						ev_txt += "\n"

					for fconidx in ftest_idx:
						fval = 0
						if (con[0] in con_map.keys() and
								fconidx in con_map[con[0]]):
							fval = 1
						ev_txt += contrast_ftest_element.substitute(
							cnum=ftest_idx.index(fconidx) + 1,
							element=tidx,
							ctype=ctype,
							val=fval)
						ev_txt += "\n"

			# add contrast mask info
			ev_txt += contrastmask_header.substitute()
			for j, _ in enumerate(contrasts):
				for k, _ in enumerate(contrasts):
					if j != k:
						ev_txt += contrastmask_element.substitute(c1=j + 1,
																  c2=k + 1)
			ev_txt += contrastmask_footer.substitute()
		return num_evs, ev_txt

	def _format_session_info(self, session_info):
		if isinstance(session_info, dict):
			session_info = [session_info]
		return session_info

	def _get_func_files(self, session_info):
		"""Returns functional files in the order of runs
		"""
		func_files = []
		for i, info in enumerate(session_info):
			func_files.insert(i, info['scans'])
		return func_files

	def _run_interface(self, runtime):
		cwd = os.getcwd()
		fsf_header = load_template('feat_header_l1.tcl')
		fsf_postscript = load_template('feat_nongui.tcl')

		prewhiten = 0
		if isdefined(self.inputs.model_serial_correlations):
			prewhiten = int(self.inputs.model_serial_correlations)
		basis_key = list(self.inputs.bases.keys())[0]
		ev_parameters = dict(self.inputs.bases[basis_key])
		session_info = self._format_session_info(self.inputs.session_info)
		func_files = self._get_func_files(session_info)
		n_tcon = 0
		n_fcon = 0
		if isdefined(self.inputs.contrasts):
			for i, c in enumerate(self.inputs.contrasts):
				if c[1] == 'T':
					n_tcon += 1
				elif c[1] == 'F':
					n_fcon += 1

		for i, info in enumerate(session_info):
			do_tempfilter = 1
			if info['hpf'] == np.inf:
				do_tempfilter = 0
			num_evs, cond_txt = self._create_ev_files(cwd, info, i, ev_parameters, self.inputs.orthogonalization,
													  self.inputs.contrasts,
													  do_tempfilter, basis_key)
			nim = load(func_files[i])
			(_, _, _, timepoints) = nim.shape
			fsf_txt = fsf_header.substitute(
				run_num=i,
				interscan_interval=self.inputs.interscan_interval,
				num_vols=timepoints,
				prewhiten=prewhiten,
				num_evs=num_evs[0],
				num_evs_real=num_evs[1],
				num_tcon=n_tcon,
				num_fcon=n_fcon,
				high_pass_filter_cutoff=info[
					'hpf'],
				temphp_yn=do_tempfilter,
				func_file=func_files[i])
			fsf_txt += cond_txt
			fsf_txt += fsf_postscript.substitute(overwrite=1)

			f = open(os.path.join(cwd, 'run%d.fsf' % i), 'w')
			f.write(fsf_txt)
			f.close()

		return runtime

	def _list_outputs(self):
		outputs = self.output_spec().get()
		cwd = os.getcwd()
		outputs['fsf_files'] = []
		outputs['ev_files'] = []
		usetd = 0
		basis_key = list(self.inputs.bases.keys())[0]
		if basis_key in ['dgamma', 'gamma']:
			usetd = int(self.inputs.bases[basis_key]['derivs'])
		for runno, runinfo in enumerate(
				self._format_session_info(self.inputs.session_info)):
			outputs['fsf_files'].append(os.path.join(cwd, 'run%d.fsf' % runno))
			outputs['ev_files'].insert(runno, [])
			evname = []
			for field in ['cond', 'regress']:
				for i, cond in enumerate(runinfo[field]):
					name = cond['name']
					evname.append(name)
					evfname = os.path.join(
						cwd, 'ev_%s_%d_%d.txt' % (name, runno,
												len(evname)))
					if field == 'cond':
						if usetd:
							evname.append(name + 'TD')
					outputs['ev_files'][runno].append(
						os.path.join(cwd, evfname))
		return outputs
