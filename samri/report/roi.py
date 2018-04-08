import nibabel as nib
import numpy as np
from os import path

from nilearn.input_data import NiftiMasker
from scipy.io import loadmat
from samri.report.utilities import add_roi_data, add_pattern_data
from joblib import Parallel, delayed

import statsmodels.formula.api as smf
import multiprocessing as mp
import pandas as pd

def from_img_threshold(image, threshold,
	two_tailed=False,
	save_as='',
	):
	"""Create an ROI based on an input volumetric image and a threshold value (absolute).

	Parameters
	----------
	image : str or nibabel.nifti1.Nifti1Image
		Either the path to a NIfTI image, or a NiBabel object containing the image data. Image can have any dimensionality.
	threshold : int or float
		Numeric value to use as threshold
	two_tailed : bool, optional
		Whether to include voxels with values below the negative of `threshold` in the ROI.
	save_as : str, optional
		Path to which to save the otput.

	Returns
	-------
	str or nibabel.nifti.Nifti1Image
		Path to generated ROI file (if `save_as` is specified), or `nibabel.nifti.Nifti1Image` object of the ROI (if `save_as` evaluates to `False`).

	Notes
	-----

	Percentile support is planned, but not currently implemented.
	"""

	if isinstance(image,str):
		image = path.abspath(path.expanduser(image))
		image = nib.load(image)
	data = image.get_data()
	header = image.header
	affine = image.affine
	roi_pos = np.where(data>threshold,[True],[False])
	if two_tailed:
		roi_neg = np.where(data<-threshold,[True],[False])
		roi = np.logical_or(roi_pos, roi_neg)
	else:
		roi = roi_pos
	roi = 1*roi
	roi = nib.Nifti1Image(roi, affine, header)

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		nib.save(roi, save_as)

	return roi

def per_session(substitutions, roi_mask,
	filename_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{scan}_tstat.nii.gz",
	feature=[],
	atlas=[],
	mapping=[],
	):

	"""
	roi_mask : str
	Path to the ROI mask for which to select the t-values.

	roi_mask_normalize : str
	Path to a ROI mask by the mean of whose t-values to normalite the t-values in roi_mask.
	"""

	if isinstance(roi_mask,str):
		roi_mask = path.abspath(path.expanduser(roi_mask))
		roi_mask = nib.load(roi_mask)

	masker = NiftiMasker(mask_img=roi_mask)

	n_jobs = mp.cpu_count()-2
	dfs = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_roi_data),
		[filename_template]*len(substitutions),
		[masker]*len(substitutions),
		substitutions,
		feature*len(substitutions),
		[atlas]*len(substitutions),
		[mapping]*len(substitutions),
		))
	df = pd.concat(dfs)

	return df


def mean(img_path, mask_path):
	"""Return the mean of the masked region of an image.
	"""
	mask = path.abspath(path.expanduser(mask_path))
	if mask_path.endswith("roi"):
		mask = loadmat(mask)["ROI"]
		while mask.ndim != 3:
			mask=mask[0]
		img_path = path.abspath(path.expanduser(img_path))
		img = nib.load(img_path)
		print(mask)
		print(np.shape(mask))
		print(np.shape(img))
		print(img[mask])
	else:
		masker = NiftiMasker(mask_img=mask)
		add_roi_data(img_path,masker)

def atlasassignment(data_path='~/ni_data/ofM.dr/bids/l2/anova/anova_zfstat.nii.gz',
	null_label=0.0,
	verbose=False,
	lateralized=False,
	):
	from copy import deepcopy

	atlas_filename = '~/ni_data/templates/roi/DSURQEc_200micron_labels.nii'
	mapping = '~/ni_data/templates/roi/DSURQE_mapping.csv'
	atlas_filename = path.abspath(path.expanduser(atlas_filename))
	mapping = path.abspath(path.expanduser(mapping))
	data_path = path.abspath(path.expanduser(data_path))

	data = nib.load(data_path)
	atlas = nib.load(atlas_filename)
	if not np.array_equal(data.affine,atlas.affine):
		print('The affines of these atlas and data file are not identical. In order to perform this sensitive operation we need to know that there is perfect correspondence between the voxels of input data and atlas.')
		return
	mapping = pd.read_csv(mapping)
	data = data.get_data().flatten()
	atlas = atlas.get_data().flatten()
	slices = []
	for d, a in zip(data, atlas):
		if a == null_label:
			continue
		if lateralized:
			pass
			#!!!this still needs to be implemented
		else:
			my_slice = mapping[mapping['right label']==a]
			if my_slice.empty:
				my_slice = mapping[mapping['left label']==a]
			if my_slice.empty:
				continue
			my_slice = deepcopy(my_slice)
			my_slice['value'] = d
			if verbose:
				print(my_slice)
			slices.append(my_slice)
	df = pd.concat(slices)
	save_as = path.splitext(data_path)[0]
	if save_as[-4:] == '.nii':
		save_as = save_as[:-4]
	save_as += '_atlasassignment.csv'
	df.to_csv(save_as)
	return

def analytic_pattern_per_session(substitutions, analytic_pattern,
	t_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{scan}_tstat.nii.gz",
	):
	"""Return a Pandas DataFrame (organized in long-format) containing the per-subject per-session scores of an analytic pattern.

	Parameters
	----------

	sustitutions : list of dicts
		A list of dictionaries countaining formatting strings as keys and strings as values.
	analytic_pattern : str
		Path to a NIfTI file to score the per-subject and per-session NIfTI files on.
		Commonly this file is unthresholded.
	t_file_template : str, optional
		A formattable string containing as format fields keys present in the dictionaries passed to the `substitutions` variable.
	"""

	if isinstance(analytic_pattern,str):
		analytic_pattern = path.abspath(path.expanduser(analytic_pattern))
	pattern = nib.load(analytic_pattern)

	n_jobs = mp.cpu_count()-2
	dfs = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_pattern_data),
		[t_file_template]*len(substitutions),
		[pattern]*len(substitutions),
		substitutions,
		))
	df = pd.concat(dfs)

	return df
