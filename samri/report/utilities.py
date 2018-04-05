import numpy as np
import nibabel as nib
import pandas as pd
from copy import deepcopy
from os import path

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass
def add_roi_data(img_path, masker,
	substitution=False,
	feature=[],
	atlas='',
	mapping='',
	):
	"""
	Return a dataframe containing the subject- and session-wise mean of a Region of Interest (ROI) score.

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
		img = masker.fit_transform(img)
		img = img.flatten()
		mean = np.nanmean(img)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({})
	else:
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

def add_pattern_data(substitution,img_path,pattern):
	"""Return a dataframe containing the subject- and session-wise mean of a patern score."""
	subject_data={}
	if substitution:
		img_path = img_path.format(**substitution)
	img_path = path.abspath(path.expanduser(img_path))
	try:
		img = nib.load(img_path)
		img_data = img.get_data()
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		pattern_evaluation = img_data*pattern
		pattern_evaluation = pattern_evaluation.flatten()
		pattern_score = np.nanmean(pattern_evaluation)
		subject_data["session"]=substitution["session"]
		subject_data["subject"]=substitution["subject"]
		subject_data["t"]=pattern_score
		df = pd.DataFrame(subject_data, index=[None])
		return df

