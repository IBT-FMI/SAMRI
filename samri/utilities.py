import multiprocessing as mp
import nibabel as nib
import nipype.interfaces.io as nio
import numpy as np
import os
import pandas as pd
from itertools import product
from joblib import Parallel, delayed
from os import path
from bids.grabbids import BIDSLayout
from bids.grabbids import BIDSValidator

N_PROCS=max(mp.cpu_count()-2,2)

def bids_autofind_df(bids_dir,
	**kwargs
	):
	"""Automatically generate a BIDS-like Pandas Dataframe index based on the more flexible `samri.utilities.bids_autofind` function.

	Parameters
	----------
	bids_dir : str
		Path to BIDS-formatted directory
	type : {"func", "anat"}
		Which type to source data for (currently only supports "func", and "anat" - ideally we could extend this to include "dwi").

	Returns
	-------
	path_template : str
		String which can be formatted with any of the dictionaries in `substitutions`
	substitutions : list of dicti
		A substitution iterator usable as a standard SAMRI function input, which (together with `path_template`) unambiguoulsy identifies input files for analysis.
	"""
	if not os.path.exists(os.path.expanduser(bids_dir)):
		raise Exception('path {} not found'.format(os.path.expanduser(bids_dir)))

	path_template, substitutions = bids_autofind(bids_dir, **kwargs)

	for i in substitutions:
		i['path'] = path_template.format(**i)
	df = pd.DataFrame.from_records(substitutions)

	return df

def bids_autofind(bids_dir,
	typ='',
	path_template="sub-{{subject}}/ses-{{session}}/{typ}/sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_run-{{run}}.nii.gz",
	match_regex='',
	):
	"""Automatically generate a BIDS path template and a substitution iterator (list of dicts, as produced by `samri.utilities.bids_substitution_iterator`, and used as a standard input SAMRI function input) from a BIDS-respecting directory.

	Parameters
	----------
	bids_dir : str
		Path to BIDS-formatted directory
	type : {"func", "anat"}
		Which type to source data for (currently only supports "func", and "anat" - ideally we could extend this to include "dwi").

	Returns
	-------
	path_template : str
		String which can be formatted with any of the dictionaries in `substitutions`
	substitutions : list of dicti
		A substitution iterator usable as a standard SAMRI function input, which (together with `path_template`) unambiguoulsy identifies input files for analysis.
	"""

	bids_dir = path.abspath(path.expanduser(bids_dir))

	if match_regex:
		pass
	elif typ in ("func","dwi"):
		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/'+typ+'/.*?_task-(?P<task>.+).*?_acq-(?P<acquisition>.+)\.nii.gz'
	elif typ == "":
		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_task-(?P<task>.+).*?_acq-(?P<acquisition>.+).*?_run-(?P<run>[0-9]+).*?\.nii.gz'
	elif typ == "anat":
		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/anat/.*?_(?P<task>.+).*?_acq-(?P<acquisition>.+)\.nii.gz'

	if path_template[:1] != '/' and 'bids_dir' not in path_template:
		path_template = '{bids_dir}/'+path_template
	path_template = path_template.format(bids_dir=bids_dir, typ=typ)

	datafind = nio.DataFinder()
	datafind.inputs.root_paths = bids_dir
	datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()

	substitutions = []
	for ix, i in enumerate(datafind_res.outputs.out_paths):
		substitution = {}
		try:
			substitution["acquisition"] = datafind_res.outputs.acquisition[ix]
		except AttributeError: pass
		try:
			substitution["subject"] = datafind_res.outputs.sub[ix]
		except AttributeError: pass
		try:
			substitution["session"] = datafind_res.outputs.ses[ix]
		except AttributeError: pass
		try:
			substitution["task"] = datafind_res.outputs.task[ix]
		except AttributeError: pass
		try:
			substitution["run"] = datafind_res.outputs.run[ix]
		except AttributeError: pass
		try:
			substitution["modality"] = datafind_res.outputs.modality[ix]
		except AttributeError: pass
		reconstructed_path = path.abspath(path.expanduser(path_template.format(**substitution)))
		original_path = path.abspath(path.expanduser(i))
		if reconstructed_path != original_path:
			print("Original DataFinder path: "+original_path)
			print("Reconstructed path:       "+reconstructed_path)
			raise ValueError("The reconstructed file path based on the substitution dictionary and the path template, is not identical to the corresponding path, found by `nipype.interfaces.io.DataFinder`. See string values above.")
		substitutions.append(substitution)

	return path_template, substitutions

def bids_substitution_iterator(sessions, subjects,
	tasks=[''],
	runs=[''],
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
	TASKS : list, optional
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
		With the keys being `"data_dir"`, `"subject"`, `"session"`, `"task"`!!!.
	"""
	substitutions=[]
	subjects = list(dict.fromkeys(subjects))
	sessions = list(dict.fromkeys(sessions))
	tasks = list(dict.fromkeys(tasks))
	runs = list(dict.fromkeys(runs))
	acquisitions = list(dict.fromkeys(acquisitions))
	modalities = list(dict.fromkeys(modalities))

	for subject, session, task, run, acquisition, modality in product(subjects, sessions, tasks, runs, acquisitions, modalities):
		substitution={}
		substitution["data_dir"] = data_dir
		substitution["task"] = task
		substitution["run"] = run
		substitution["session"] = session
		substitution["subject"] = subject
		substitution["acquisition"] = acquisition
		substitution["modality"] = modality
		if validate_for_template:
			check_file = validate_for_template.format(**substitution)
			check_file = path.abspath(path.expanduser(check_file))
			if path.isfile(check_file):
				substitutions.append(substitution)
			else: print('no file under path {}'.format(check_file))
		else:
			substitutions.append(substitution)
	return substitutions

def iter_collapse_by_path(in_files, out_files,
	n_jobs=None,
	n_jobs_percentage=0.75,
	):
	"""Patalellized iteration of `samri.utilities.collapse_by_path`."""
	if not n_jobs:
		n_jobs = max(int(round(mp.cpu_count()*n_jobs_percentage)),2)
	out_files = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(collapse_by_path),
		in_files,
		out_files,
		))
	return out_files

def collapse_by_path(in_path, out_path):
	"""Wrapper for `samri.utilities.collapse`, supporting an input path and saving object to an output path."""
	in_path = os.path.abspath(os.path.expanduser(in_path))
	out_path = os.path.abspath(os.path.expanduser(out_path))
	img = nib.load(in_path)
	img = collapse(img)
	out_dir = os.path.dirname(out_path)
	if not os.path.exists(out_dir):
		#race-condition safe:
		try:
			os.makedirs(out_dir)
		except OSError:
			pass
	nib.save(img, out_path)
	return out_path

def collapse(img,
	min_dim=3,
	):
	"""
	Collapse a nibabel image allong its last axis

	Parameters
	----------
	img : nibabel.nifti1.Nifti1Image
		Nibabel image to be collapsed.
	min_dim : int
		Bimensionality beyond which not to collapse.
	"""

	ndim = 0
	data = img.get_data()
	for i in range(len(img.header['dim'])-1):
		current_dim = img.header['dim'][i+1]
		if current_dim == 1:
			break
		ndim += 1
	if ndim <= min_dim:
		return img
	img.header['dim'][0] = ndim
	img.header['pixdim'][ndim+1:] = 0
	data = np.mean(data,axis=(ndim-1))
	img = nib.nifti1.Nifti1Image(data, img.affine, img.header)
	return img

def session_irregularity_filter(bids_path, exclude_irregularities):
	"""
	Create a Pandas Dataframe recording which session-animal combinations should be excluded, based on an irregularity criterion.

	Parameters
	----------

	bids_path: str
		Path to the root of the BIDS directory containing `_sessions.tsv` files.
	exclude_irregularities: list of str
		Irregularity strings which will disqualify a scan.
		The logic for the exclusion is "any", if even one of the irregularities is present, the scan will be disqualified.
	"""

	bids_path = os.path.abspath(os.path.expanduser(bids_path))

	sessions = []
	for sub_dir in os.listdir(bids_path):
		sub_path = os.path.join(bids_path,sub_dir)
		if os.path.isdir(sub_path) and sub_dir[:4] == 'sub-':
			session_file = os.path.join(sub_path,'{}_sessions.tsv'.format(sub_dir))
			if os.path.isfile(session_file):
				_df = pd.read_csv(session_file, sep='\t')
				subject = sub_dir[4:]
				for ix, row in _df.iterrows():
					ses_entry = {}
					session = row['session_id'][4:]
					irregularities = row['irregularities']
					ses_entry['subject'] = subject
					ses_entry['session'] = session
					ses_entry['irregularities'] = irregularities
					try:
						ses_entry['exclude'] = any(i in irregularities for i in exclude_irregularities)
					except TypeError:
						ses_entry['exclude'] = False
					sessions.append(ses_entry)
	return pd.DataFrame(sessions)


def ordered_structures(
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii',
	mapping='/usr/share/mouse-brain-atlases/dsurqe_labels.csv',
	label_columns=['right label','left label'],
	structure_column='Structure',
	remove_zero_label=True,
	):
	"""Return a list of structure names corresponding to the ascending order of numerical labels in the atlas image.

	Parameters
	----------

	atlas : str or nibabel.Nifti1Image, optional
		Path to a NIfTI atlas file.
	mapping : str or pandas.DataFrame, optional
		Path to a CSV mapping file containing columns which include the string specified under `structure_column` and the strings specified under `label_columns`.
		The latter of these columns need to include the numerical values found in the data matrix of the file whose path is assigned to `atlas`.
	label_columns : list, optional
		Names of columns in the `mapping` file under which numerical labels are specified.
		This can be a length-2 list if separate columns exist for left and right labels; in this case the function will perform the differentiation implicitly.
	structure_column : str, optional
		The name of the column, which in the `mapping` file records the structure names.
	remove_zero_label : bool, optional
		Whether to disconsider the zero label in the atlas image.
	"""
	if isinstance(atlas, str):
		atlas = path.abspath(path.expanduser(atlas))
		atlas = nib.load(atlas)
	if isinstance(mapping, str):
		mapping = path.abspath(path.expanduser(mapping))
		mapping = pd.read_csv(mapping)
	atlas_data = atlas.get_data()
	atlas_data_unique = np.unique(atlas_data)
	if remove_zero_label:
		atlas_data_unique = atlas_data_unique[atlas_data_unique != 0]
	structure_names = []
	for label in atlas_data_unique:
		structure_name = []
		for label_column in label_columns:
			try:
				structure = mapping.loc[mapping[label_column]==label,structure_column].values[0]
			except IndexError:
				pass
			else:
				if any(i in label_column for i in ['right','Right','RIGHT']):
					lateralized_structure = '{} (R)'.format(structure)
					structure_name.append(lateralized_structure)
				elif any(i in label_column for i in ['left','Left','LEFT']):
					lateralized_structure = '{} (L)'.format(structure)
					structure_name.append(lateralized_structure)
				else:
					structure_name.append(structure)
		if len(structure_name) != 1:
			structure_name = structure
		else:
			structure_name = structure_name[0]
		structure_names.append(structure_name)

	return structure_names
