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

def voxels_for_comparison(img1_path, img2_path,
	mask_path='/usr/share/mouse-brain-templates/dsurqec_200micron_mask.nii',
	resample_voxel_size=[],
	replace_nan_with=0.,
	):
	"""Return (optionally resampled) voxelwise values from two images, constrained to a mask region and voxels which are not NaN in any of the images.

	Parameters
	----------
	img1_path : str
		Path to NIfTI file.
	img2_path : str
		Path to NIfTI file co-registered with `img1_path`.
	mask_path : str
		Path to NIfTI file co-registered with `mask_path`.
	resample_voxel_site : list, optional
		Length-3 list with the desired voxel dimensions.
	replace_nan_with : float, optional
		Value with which to replace NaN values in `img1_path` and `img2_path`.
		This is only an internal operation, and should in no way modify the output, since voxels with NaN values in either `img1_path` and `img2_path` will always be masked.

	"""

	import numpy as np
	from scipy import stats
	from nibabel import processing

	img1_path = path.abspath(path.expanduser(img1_path))
	img2_path = path.abspath(path.expanduser(img2_path))
	mask_path = path.abspath(path.expanduser(mask_path))

	img1 = nib.load(img1_path)
	img2 = nib.load(img2_path)
	mask = nib.load(mask_path)

	img1_data = img1.get_data()
	img2_data = img2.get_data()
	mask_data = mask.get_data()

	# Query NaN voxels in input images
	img1_nans = np.isnan(img1_data)
	img2_nans = np.isnan(img2_data)
	mask_data = np.array(mask_data, dtype=bool)

	mask_data = np.all([~img1_nans ,~img2_nans, mask_data], axis=0)

	if resample_voxel_size:
		# Set NaN values to numeric (this is just to permit resampling, as all NaN voxels will already be masked for the actual correlation measurement).
		img1_data[img1_nans] = replace_nan_with
		img2_data[img2_nans] = replace_nan_with

		img1 = nib.Nifti1Image(img1_data, img1.affine, img1.header)
		img2 = nib.Nifti2Image(img2_data, img2.affine, img2.header)
		mask = nib.Nifti2Image(mask_data, mask.affine, mask.header)

		img1 = processing.resample_to_output(img1, voxel_sizes=resample_voxel_size)
		img2 = processing.resample_to_output(img2, voxel_sizes=resample_voxel_size)
		mask = processing.resample_to_output(mask, voxel_sizes=resample_voxel_size)

		img1_data = img1.get_data()
		img2_data = img2.get_data()
		mask_data = mask.get_data()

		mask_data = np.array(mask_data, dtype=bool)

	img1_masked = img1_data[mask_data]
	img2_masked = img2_data[mask_data]

	return img1_masked, img2_masked


def rois_for_comparison(img1_path, img2_path):
	"""Return ROI-wise mean values from two images, constrained to ROIs computable in both images, the names of which are also defined.

	Parameters
	----------
	img1_path : str
		Path to NIfTI file.
	img2_path : str
		Path to NIfTI file co-registered with `img1_path`.
	"""

	from samri.report.roi import atlasassignment

	value_label='t Values'
	df1 = atlasassignment(img1_path,
		lateralized=True,
		value_label=value_label,
		)
	df1[value_label] = df1[value_label].apply(lambda x: np.mean([float(i) for i in x.split(', ')]))
	df1['Structure Unique'] = df1['Structure'] + ', ' + df1['Side']

	df2 = atlasassignment(img2_path,
		lateralized=True,
		value_label=value_label,
		)
	df2[value_label] = df2[value_label].apply(lambda x: np.mean([float(i) for i in x.split(', ')]))
	df2['Structure Unique'] = df2['Structure'] + ', ' + df2['Side']

	if len(df1[value_label].values) < len(df2[value_label].values):
		roi_names = df1['Structure Unique'].unique()
		df2 = df2.loc[df2['Structure Unique'].isin(roi_names)]
	elif len(df2[value_label].values) < len(df1[value_label].values):
		roi_names = df2['Structure Unique'].unique()
		df1 = df1.loc[df1['Structure Unique'].isin(roi_names)]
	else:
		roi_names = df2['Structure Unique'].unique()

	img1_rois = df1[value_label].values
	img2_rois = df2[value_label].values

	return img1_rois, img2_rois, roi_names
