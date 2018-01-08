import multiprocessing
import nipype.interfaces.io as nio
from itertools import product
from os import path

N_PROCS=max(multiprocessing.cpu_count()-2,2)

def bids_autofind(bids_dir,modality):
	"""Automatically generate a BIDS path template and a substitution iterator (list of dicts, as produced by `samri.utilities.bids_substitution_iterator`, and used as a standard input SAMRI function input) from a BIDS-respecting directory.

	Parameters
	----------
	bids_dir : str
		Path to BIDS-formatted directory
	modality : {"func", "anat"}
		Which modality to source data for (corrently only supports "func", and "anat" - ideally we could extend this to include "dwi").

	Returns
	-------
	path_template : str
		String which can be formatted with any of the dictionaries in `substitutions`
	substitutions : list of dicti
		A substitution iterator usable as a standard SAMRI function input, which (together with `path_template`) unambiguoulsy identifies input files for analysis.
	"""

	bids_dir = path.abspath(path.expanduser(bids_dir))

	allowed_modalities = ("func","anat")
	if modality not in allowed_modalities:
	       raise ValueError("modality parameter needs to be one of "+", ".join(allowed_modalities)+".")

	if modality in ("func","dwi"):
	       match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/'+modality+'/.*?_trial-(?P<trial>.+)\.nii.gz'
	elif modality == "anat":
	       match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/anat/.*?_(?P<trial>.+)\.nii.gz'

	path_template = bids_dir+"/sub-{subject}/ses-{session}/"+modality+"/sub-{subject}_ses-{session}_trial-{trial}.nii.gz"

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = bids_dir
	datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()

	substitutions = []
	for ix, i in enumerate(datafind_res.outputs.out_paths):
		substitution = {}
		substitution["subject"] = datafind_res.outputs.sub[ix]
		substitution["session"] = datafind_res.outputs.ses[ix]
		substitution["trial"] = datafind_res.outputs.trial[ix]
		if path_template.format(**substitution) != i:
			print("Original DataFinder path: "+i)
			print("Reconstructed path: "+path_template.format(**substitution))
			raise ValueError("The reconstructed file path based on the substitution dictionary and the path template, is not identical to the corresponding path, found by `nipype.interfaces.io.DataFinder`. See string values above.")
		substitutions.append(substitution)

	return path_template, substitutions

def bids_substitution_iterator(sessions, subjects,
	trials=[''],
	data_dir='',
	preprocessing_dir='',
	acquisitions=[''],
	modalities=[''],
	l1_dir=None,
	l1_workdir=None,
	preprocessing_workdir=None,
	validate_for_template=None,
	):
	"""Returns a list of dictionaries, which can be used together with a template string to identify large sets of input data files for SAMRI functions.

	Parameters
	----------

	sessions : list
		A list of session identifiers to include in the iterator.
	subjects : list
		A list of subject identifiers to include in the iterator.
	trials : list, optional
		A list of scan types to include in the iterator.
	data_dir : str, optional
		Path to the data root (this is where SAMRI creates e.g. `preprocessing`, `l1`, or `l2` directories.
	preprocessing_dir : str, optional
		String identifying the preprocessing pipeline name from which to provide an iterator.
	l1_dir : str, optional
		String identifying the level 1 pipeline name from which to provide an iterator. If `None` the level 1 pipeline name is assumed to correspond to the preprocessing pipeline name (`preprocessing_dir`)
	l1_workdir : str, optional
		String identifying the level 1 work directory name from which to provide an iterator. If `None` the level 1 work directory name is assumed to be the level 1 pipeline name (`l1_dir`) suffixed with the string `"_work"`.
	preprocessing_workdir : str, optional
		String identifying the preprocessing work directory name from which to provide an iterator. If `None` the preprocessing work directory name is assumed to be the preprocessing pipeline name (`preprocessing_dir`) suffixed with the string `"_work"`.
	validate_for_template : str, optional
		Template string for which to check whether a file exists.
		If no file exists given a substitution dictionary, that dictionary will not be added to the retuned list.
		If this variable is an empty string (or otherwise evaluates as False) no check is performed, and all dictionaries (i.e. all input value permutations) are returned.

	Returns
	-------
	list of dictionaries
		With the keys being `"data_dir"`, `"l1_dir"`, `"l1_workdir"`, `"preprocessing_dir"`, `"preprocessing_workdir"`, `"scan"`, `"session"`, and `"subject"`.
	"""
	if not l1_dir:
		l1_dir = preprocessing_dir
	if not l1_workdir:
		l1_workdir = l1_dir+"_work"
	if not preprocessing_workdir:
		preprocessing_workdir = preprocessing_dir+"_work"
	substitutions=[]
	for subject, session, trial, acquisition, modality in product(subjects, sessions, trials, acquisitions, modalities):
		substitution={}
		substitution["data_dir"] = data_dir
		substitution["l1_dir"] = l1_dir
		substitution["l1_workdir"] = l1_workdir
		substitution["preprocessing_dir"] = preprocessing_dir
		substitution["preprocessing_workdir"] = preprocessing_workdir
		substitution["trial"] = trial
		substitution["session"] = session
		substitution["subject"] = subject
		substitution["acquisition"] = acquisition
		substitution["modality"] = modality
		if validate_for_template:
			check_file = validate_for_template.format(**substitution)
			check_file = path.abspath(path.expanduser(check_file))
			if path.isfile(check_file):
				substitutions.append(substitution)
		else:
			substitutions.append(substitution)
	return substitutions
