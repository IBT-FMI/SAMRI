import multiprocessing as mp
import numpy as np
import nibabel as nib
import pandas as pd
from copy import deepcopy
from joblib import Parallel, delayed
from nilearn.input_data import NiftiMasker
from os import path

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass
def roi_df(img_path, masker,
	substitution=False,
	feature=[],
	atlas='',
	mapping='',
	):
	"""
	Return a dataframe containing the mean of a Region of Interest (ROI).

	Parameters
	----------

	img_path : str
		Path to NIfTI file from which the ROI is to be extracted.
	makser : nilearn.NiftiMasker
		Nilearn `nifti1.Nifti1Image` object to use for masking the desired ROI.
	substitution : dict, optional
		A dictionary with keys which include 'subject' and 'session'.
	feature : list, optional
		A list with labels which were used to dynalically generate the masker ROI.
		This parameter will be ignored if a path can be established for the masker - via `masker.mask_img.get_filename()`.
	"""
	subject_data={}
	if substitution:
		img_path = img_path.format(**substitution)
	img_path = path.abspath(path.expanduser(img_path))
	try:
		img = nib.load(img_path)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({})
	else:
		img = masker.fit_transform(img)
		img = img.flatten()
		mean = np.nanmean(img)
		subject_data['session'] = substitution['session']
		subject_data['subject'] = substitution['subject']
		subject_data['t'] = mean
		mask_path = masker.mask_img.get_filename()
		if mask_path:
			feature = path.abspath(mask_path)
		subject_data['feature'] = feature
		subject_data['atlas'] = atlas
		subject_data['mapping'] = mapping
		df = pd.DataFrame(subject_data, index=[None])
		return df

def roi_data(img_path, masker,
	substitution={},
	exclude_zero=False,
	zero_threshold=0.1,
	):
	"""
	Return the mean of a Region of Interest (ROI) score.

	Parameters
	----------

	img_path : str
		Path to NIfTI file from which the ROI is to be extracted.
	makser : nilearn.NiftiMasker
		Nilearn `nifti1.Nifti1Image` object to use for masking the desired ROI.
	exclude_zero : bool, optional
		Whether to filter out zero values.
	substitution : dict, optional
		A dictionary with keys which include 'subject' and 'session'.
	zero_threshold : float, optional
		Absolute value below which values are to be considered zero.
	"""
	if substitution:
		img_path = img_path.format(**substitution)
	img_path = path.abspath(path.expanduser(img_path))
	img = nib.load(img_path)
	try:
		masked_data = masker.fit_transform(img)
	except:
		masker = path.abspath(path.expanduser(masker))
		masker = NiftiMasker(mask_img=masker)
		masked_data = masker.fit_transform(img)
	masked_data = masked_data.flatten()
	masked_data = masked_data[~np.isnan(masked_data)]
	if exclude_zero:
		masked_data = masked_data[np.abs(masked_data)>=zero_threshold]
	masked_mean = np.mean(masked_data)
	masked_median = np.median(masked_data)
	return masked_mean, masked_median

def pattern_df(img_path, pattern,
	substitution=False,
	):
	"""
	Return a dataframe containing the `patern` score of `img_path` (i.e. the mean of the multiplication product).

	Parameters
	----------

	img_path : str
		Path to NIfTI file from which the ROI is to be extracted.
	pattern : nilearn.NiftiMasker
		Nilearn `nifti1.Nifti1Image` object to use for masking the desired ROI.
	substitution : dict, optional
		A dictionary with keys which include 'subject' and 'session'.

	"""

	subject_data={}
	if substitution:
		img_path = img_path.format(**substitution)
	img_path = path.abspath(path.expanduser(img_path))
	try:
		img = nib.load(img_path)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		img_data = img.get_data()
		pattern_data = pattern.get_data()
		pattern_evaluation = img_data*pattern_data
		pattern_evaluation = pattern_evaluation.flatten()
		pattern_score = np.nanmean(pattern_evaluation)
		subject_data["session"]=substitution["session"]
		subject_data["subject"]=substitution["subject"]
		subject_data["t"]=pattern_score
		subject_data['feature'] = pattern.get_filename()
		df = pd.DataFrame(subject_data, index=[None])
		return df

