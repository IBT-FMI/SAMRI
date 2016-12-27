# -*- coding: utf-8 -*-

"""The bru2nii module provides basic functions for dicom conversion

	Change directory to provide relative paths for doctests
	>>> import os
	>>> filepath = os.path.dirname( os.path.realpath( __file__ ) )
	>>> datadir = os.path.realpath(os.path.join(filepath, '../testing/data'))
	>>> os.chdir(datadir)
"""
from __future__ import print_function, division, unicode_literals, absolute_import

import os
from nipype.interfaces.base import (CommandLine, CommandLineInputSpec,
					traits, TraitedSpec, isdefined, File, Directory,
					InputMultiPath)
from nipype.interfaces.fsl.base import (FSLCommand, FSLCommandInputSpec)


class MELODICInputSpec(FSLCommandInputSpec):
	in_files = InputMultiPath(
		File(exists=True), argstr="-i %s", mandatory=True, position=0,
		desc="input file names (either single file name or a list)",
		sep=",")
	out_dir = Directory(
		argstr="-o %s", desc="output directory name", genfile=True)
	mask = File(exists=True, argstr="-m %s",
				desc="file name of mask for thresholding")
	no_mask = traits.Bool(argstr="--nomask", desc="switch off masking")
	update_mask = traits.Bool(
		argstr="--update_mask", desc="switch off mask updating")
	no_bet = traits.Bool(argstr="--nobet", desc="switch off BET")
	bg_threshold = traits.Float(
		argstr="--bgthreshold=%f",
		desc=("brain/non-brain threshold used to mask non-brain voxels, as a "
			  "percentage (only if --nobet selected)"))
	dim = traits.Int(
		argstr="-d %d",
		desc=("dimensionality reduction into #num dimensions (default: "
			  "automatic estimation)"))
	dim_est = traits.Str(argstr="--dimest=%s",
						 desc=("use specific dim. estimation technique: lap, "
							   "bic, mdl, aic, mean (default: lap)"))
	sep_whiten = traits.Bool(
		argstr="--sep_whiten", desc="switch on separate whitening")
	sep_vn = traits.Bool(
		argstr="--sep_vn", desc="switch off joined variance normalization")
	num_ICs = traits.Int(
		argstr="-n %d",
		desc="number of IC's to extract (for deflation approach)")
	approach = traits.Str(
		argstr="-a %s",
		desc="approach for decomposition, 2D: defl, symm (default), 3D: tica "
			 "(default), concat")
	non_linearity = traits.Str(
		argstr="--nl=%s", desc="nonlinearity: gauss, tanh, pow3, pow4")
	var_norm = traits.Bool(
		argstr="--vn", desc="switch off variance normalization")
	pbsc = traits.Bool(
		argstr="--pbsc",
		desc="switch off conversion to percent BOLD signal change")
	cov_weight = traits.Float(
		argstr="--covarweight=%f",
		desc=("voxel-wise weights for the covariance matrix (e.g. "
			  "segmentation information)"))
	epsilon = traits.Float(argstr="--eps=%f", desc="minimum error change")
	epsilonS = traits.Float(
		argstr="--epsS=%f",
		desc="minimum error change for rank-1 approximation in TICA")
	maxit = traits.Int(argstr="--maxit=%d",
					   desc="maximum number of iterations before restart")
	max_restart = traits.Int(
		argstr="--maxrestart=%d", desc="maximum number of restarts")
	mm_thresh = traits.Float(
		argstr="--mmthresh=%f",
		desc="threshold for Mixture Model based inference")
	no_mm = traits.Bool(
		argstr="--no_mm", desc="switch off mixture modelling on IC maps")
	ICs = File(exists=True, argstr="--ICs=%s",
			   desc="filename of the IC components file for mixture modelling")
	mix = File(exists=True, argstr="--mix=%s",
			   desc="mixing matrix for mixture modelling / filtering")
	smode = File(exists=True, argstr="--smode=%s",
				 desc="matrix of session modes for report generation")
	rem_cmp = traits.List(
		traits.Int, argstr="-f %d", desc="component numbers to remove")
	report = traits.Bool(argstr="--report", desc="generate Melodic web report")
	bg_image = File(
		exists=True, argstr="--bgimage=%s",
		desc="specify background image for report (default: mean image)")
	tr_sec = traits.Float(argstr="--tr=%f", desc="TR in seconds")
	log_power = traits.Bool(
		argstr="--logPower",
		desc="calculate log of power for frequency spectrum")
	t_des = File(exists=True, argstr="--Tdes=%s",
				 desc="design matrix across time-domain")
	t_con = File(exists=True, argstr="--Tcon=%s",
				 desc="t-contrast matrix across time-domain")
	s_des = File(exists=True, argstr="--Sdes=%s",
				 desc="design matrix across subject-domain")
	s_con = File(exists=True, argstr="--Scon=%s",
				 desc="t-contrast matrix across subject-domain")
	out_all = traits.Bool(argstr="--Oall", desc="output everything")
	out_unmix = traits.Bool(argstr="--Ounmix", desc="output unmixing matrix")
	out_stats = traits.Bool(
		argstr="--Ostats", desc="output thresholded maps and probability maps")
	out_pca = traits.Bool(argstr="--Opca", desc="output PCA results")
	out_white = traits.Bool(
		argstr="--Owhite", desc="output whitening/dewhitening matrices")
	out_orig = traits.Bool(argstr="--Oorig", desc="output the original ICs")
	out_mean = traits.Bool(argstr="--Omean", desc="output mean volume")
	report_maps = traits.Str(
		argstr="--report_maps=%s",
		desc="control string for spatial map images (see slicer)")
	remove_deriv = traits.Bool(
		argstr="--remove_deriv",
		desc="removes every second entry in paradigm file (EV derivatives)")


class MELODICOutputSpec(TraitedSpec):
	out_dir = Directory(exists=True)
	report_dir = Directory(exists=True)


class MELODIC(FSLCommand):
	"""Multivariate Exploratory Linear Optimised Decomposition into Independent
	Components

	Examples
	--------

	>>> melodic_setup = MELODIC()
	>>> melodic_setup.inputs.approach = 'tica'
	>>> melodic_setup.inputs.in_files = ['functional.nii', 'functional2.nii', 'functional3.nii']
	>>> melodic_setup.inputs.no_bet = True
	>>> melodic_setup.inputs.bg_threshold = 10
	>>> melodic_setup.inputs.tr_sec = 1.5
	>>> melodic_setup.inputs.mm_thresh = 0.5
	>>> melodic_setup.inputs.out_stats = True
	>>> melodic_setup.inputs.t_des = 'timeDesign.mat'
	>>> melodic_setup.inputs.t_con = 'timeDesign.con'
	>>> melodic_setup.inputs.s_des = 'subjectDesign.mat'
	>>> melodic_setup.inputs.s_con = 'subjectDesign.con'
	>>> melodic_setup.inputs.out_dir = 'groupICA.out'
	>>> melodic_setup.cmdline # doctest: +ALLOW_UNICODE
	'melodic -i functional.nii,functional2.nii,functional3.nii -a tica --bgthreshold=10.000000 --mmthresh=0.500000 --nobet -o groupICA.out --Ostats --Scon=subjectDesign.con --Sdes=subjectDesign.mat --Tcon=timeDesign.con --Tdes=timeDesign.mat --tr=1.500000'
	>>> melodic_setup.run() # doctest: +SKIP


	"""
	input_spec = MELODICInputSpec
	output_spec = MELODICOutputSpec
	_cmd = 'melodic'

	def _list_outputs(self):
		outputs = self.output_spec().get()
		if isdefined(self.inputs.out_dir):
			outputs['out_dir'] = os.path.abspath(self.inputs.out_dir)
		else:
			outputs['out_dir'] = self._gen_filename("out_dir")
		if isdefined(self.inputs.report) and self.inputs.report:
			outputs['report_dir'] = os.path.join(
				outputs['out_dir'], "report")
		return outputs

	def _gen_filename(self, name):
		if name == "out_dir":
			return os.getcwd()

class Bru2InputSpec(CommandLineInputSpec):
	input_dir = Directory(
		desc="Input Directory", exists=True, mandatory=True, position=-1, argstr="%s")
	actual_size = traits.Bool(
		argstr='-a', desc="Keep actual size - otherwise x10 scale so animals match human.")
	force_conversion = traits.Bool(
		argstr='-f', desc="Force conversion of localizers images (multiple slice orientations).")
	append_protocol_name = traits.Bool(
		argstr='-p', desc="Append protocol name to output filename.")
	output_filename = traits.Str(
		argstr="-o %s", desc="Output filename ('.nii' will be appended)", genfile=True)


class Bru2OutputSpec(TraitedSpec):
	nii_file = File(exists=True)


class Bru2(CommandLine):

	"""Uses bru2nii's Bru2 to convert Bruker files

	Examples
	========

	>>> from nipype.interfaces.bru2nii import Bru2
	>>> converter = Bru2()
	>>> converter.inputs.input_dir = "brukerdir"
	>>> converter.cmdline  # doctest: +ELLIPSIS +IGNORE_UNICODE
	'Bru2 -o .../nipype/nipype/testing/data/brukerdir brukerdir'
	"""
	input_spec = Bru2InputSpec
	output_spec = Bru2OutputSpec
	_cmd = "Bru2"

	# def _run_interface(self, runtime, correct_return_codes=(0,)):
	# 	#Bru2 appends the directory name to input_dir if it does not end in a slash
	# 	self.inputs.input_dir = os.path.join(self.inputs.input_dir, '')
	# 	super(CommandLine, self)._run_interface(self, runtime, correct_return_codes=correct_return_codes)

	def _list_outputs(self):
		outputs = self._outputs().get()
		if isdefined(self.inputs.output_filename):
			output_filename1 = os.path.abspath(self.inputs.output_filename)
		else:
			output_filename1 = self._gen_filename('output_filename')
		outputs["nii_file"] = output_filename1+".nii"
		return outputs

	def _gen_filename(self, name):
		if name == 'output_filename':
			outfile = os.path.join(
				os.getcwd(), os.path.basename(os.path.normpath(self.inputs.input_dir)))
			return outfile

STIM_PROTOCOL_DICTIONARY={
	"EPI_CBV_jin6":"jin6",
	"EPI_CBV_jin10":"jin10",
	"EPI_CBV_jin20":"jin20",
	"EPI_CBV_jin40":"jin40",
	"EPI_CBV_jin60":"jin60",
	"EPI_CBV_alej":"alej",
	"7_EPI_CBV_jin6":"jin6",
	"7_EPI_CBV_jin10":"jin10",
	"7_EPI_CBV_jin20":"jin20",
	"7_EPI_CBV_jin40":"jin40",
	"7_EPI_CBV_jin60":"jin60",
	"7_EPI_CBV_alej":"alej",
	"7_EPI_CBV":"6_20_jb",
	"EPI_CBV":"chr_longSOA",
	}

def fslmaths_invert_values(img_path):
	"""Calculates the op_string required to make an fsl.ImageMaths() node invert an image"""
	op_string = "-sub {0} -sub {0}".format(img_path)
	return op_string

def iterfield_selector(iterfields, selector, action):
	"""Include or exclude entries from iterfields based on a selector dictionary

	Parameters
	----------

	iterfields : list
	A list of lists (or tuples) containing entries fromatted at (subject_id,session_id,trial_id)

	selector : dict
	A dictionary with any combination of "sessions", "subjects", "trials" as keys and corresponding identifiers as values.

	action : "exclude" or "include"
	Whether to exclude or include (and exclude all the other) matching entries from the output.
	"""
	name_map = {"subjects": 0, "sessions": 1, "trials":2}
	keep = []
	for ix, iterfield in enumerate(iterfields):
		for key in selector:
			selector[key] = [str(i) for i in selector[key]]
			if iterfield[name_map[key]] in selector[key]:
				keep.append(ix)
				break
	if action == "exclude":
		iterfields = [iterfields[i] for i in range(len(iterfields)) if i not in keep]
	elif action == "include":
		iterfields = [iterfields[i] for i in keep]
	return iterfields

def datasource_exclude(in_files, excludes, output="files"):
	"""Exclude file names from a list that match a BIDS-style specifications from a dictionary.

	Parameters
	----------

	in_files : list
	A list of flie names.

	excludes : dictionary
	A dictionary with keys which are "subjects", "sessions", or "scans", and values which are lists giving the subject, session, or scan identifier respectively.

	output : string
	Either "files" or "len". The former outputs the filtered file names, the latter the length of the resulting list.
	"""

	if not excludes:
		out_files = in_files
	else:
		exclude_criteria=[]
		for key in excludes:
			if key in "subjects":
				for i in excludes[key]:
					exclude_criteria.append("sub-"+str(i))
			if key in "sessions":
				for i in excludes[key]:
					exclude_criteria.append("ses-"+str(i))
			if key in "scans":
				for i in excludes[key]:
					exclude_criteria.append("trial-"+str(i))
		out_files = [in_file for in_file in in_files if not any(criterion in in_file for criterion in exclude_criteria)]
	if output == "files":
		return out_files
	elif output == "len":
		return len(out_files)


def ss_to_path(subject_session):
	"""Concatenate a (subject, session) or (subject, session, scan) tuple to a BIDS-style path"""
	subject = "sub-" + subject_session[0]
	session = "ses-" + subject_session[1]
	return "/".join([subject,session])

def sss_to_source(source_format, subject=False, session=False, scan=False, subject_session_scan=False, base_directory=False, groupby=False):
	import os

	if any(a is False for a in [subject,session,scan]):
		(subject,session,scan) = subject_session_scan

	if groupby == "session":
		source = source_format.format("*", session, "*")
	else:
		source = source_format.format(subject, session, scan)
	if base_directory:
		source = os.path.join(base_directory, source)
	return source

def sss_filename(subject_session, scan, scan_prefix="trial", suffix="", extension=".nii.gz"):
	"""Concatenate subject-condition and scan inputs to a BIDS-style filename

	Parameters
	----------

	subject_session : list
	Length-2 list of subject and session identifiers

	scan : string
	Scan identifier

	suffix : string, optional
	Measurement type suffix (commonly "bold" or "cbv")
	"""
	# we do not want to modify the subject_session iterator entry
	from copy import deepcopy
	subject_session = deepcopy(subject_session)

	subject_session[0] = "sub-" + subject_session[0]
	subject_session[1] = "ses-" + subject_session[1]
	if suffix:
		suffix = "_"+suffix
	if scan_prefix:
		scan = "".join([scan_prefix,"-",scan,suffix,extension])
	else:
		scan = "".join([scan,suffix,extension])
	subject_session.append(scan)
	return "_".join(subject_session)
