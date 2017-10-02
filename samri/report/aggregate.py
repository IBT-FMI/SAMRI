# -*- coding: utf-8 -*-
import multiprocessing as mp
import numpy as np
import errno
from copy import deepcopy
from joblib import Parallel, delayed
from os import path, makedirs
from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker, NiftiMasker
from samri.utilities import add_roi_data, add_pattern_data
from samri.pipelines import fc

def add_fc_roi_data(data_path, seed_masker, brain_masker,
	substitution=False,
	smoothing_fwhm=.3,
	detrend=True,
	standardize=True,
	low_pass=0.25,
	high_pass=0.004,
	tr=1.,
	save_as="",
	):
	"""Return a per-subject and a per-voxel dataframe containing the mean and voxelwise ROI t-scores"""
	if substitution:
		data_path = data_path.format(**substitution)
	data_path = path.abspath(path.expanduser(data_path))

	results = deepcopy(substitution)

	if not path.isfile(data_path):
		print("WARNING: File \"{}\" does not exist.".format(data_path))
		results["result"] = None
		return results

	seed_time_series = seed_masker.fit_transform(data_path,).T
	seed_time_series = np.mean(seed_time_series, axis=0)
	brain_time_series = brain_masker.fit_transform(data_path,)
	seed_based_correlations = np.dot(brain_time_series.T, seed_time_series) / seed_time_series.shape[0]
	seed_based_correlations_fisher_z = np.arctanh(seed_based_correlations)
	seed_based_correlation_img = brain_masker.inverse_transform(seed_based_correlations_fisher_z.T)

	if save_as:
		save_as = save_as.format(**substitution)
		save_as = path.abspath(path.expanduser(save_as))
		save_as_dir = path.dirname(save_as)
		try:
			makedirs(save_as_dir)
		except OSError as exc:  # Python >2.5
			if exc.errno == errno.EEXIST and path.isdir(save_as_dir):
				pass
			else:
				raise
		seed_based_correlation_img.to_filename(save_as)
		results["result"] = save_as
	else:
		results["result"] = seed_based_correlation_img

	return results

def seed_fc(substitutions, seed, roi,
	ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{trial}.nii.gz",
	smoothing_fwhm=.3,
	detrend=True,
	standardize=True,
	low_pass=0.25,
	high_pass=0.004,
	tr=1.,
	save_results="",
	):
	"""Plot a ROI t-values over the session timecourse

	roi_mask : str
	Path to the ROI mask for which to select the t-values.

	figure : {"per-participant", "per-voxel", "both"}
	At what level to resolve the t-values. Per-participant compares participant means, per-voxel compares all voxel values, both creates two plots covering the aforementioned cases.

	roi_mask_normalize : str
	Path to a ROI mask by the mean of whose t-values to normalite the t-values in roi_mask.
	"""

	if isinstance(roi,str):
		roi_mask = path.abspath(path.expanduser(roi))
	if isinstance(seed,str):
		seed_mask = path.abspath(path.expanduser(seed))

	seed_masker = NiftiMasker(
			mask_img=seed_mask,
			smoothing_fwhm=smoothing_fwhm,
			detrend=detrend,
			standardize=standardize,
			low_pass=low_pass,
			high_pass=high_pass,
			t_r=tr,
			memory='nilearn_cache', memory_level=1, verbose=0
			)
	brain_masker = NiftiMasker(
			mask_img=roi_mask,
			smoothing_fwhm=smoothing_fwhm,
			detrend=detrend,
			standardize=standardize,
			low_pass=low_pass,
			high_pass=high_pass,
			t_r=tr,
			memory='nilearn_cache', memory_level=1, verbose=0
			)


	n_jobs = mp.cpu_count()-2
	fc_maps = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_fc_roi_data),
		[ts_file_template]*len(substitutions),
		[seed_masker]*len(substitutions),
		[brain_masker]*len(substitutions),
		substitutions,
		[smoothing_fwhm]*len(substitutions),
		[detrend]*len(substitutions),
		[standardize]*len(substitutions),
		[low_pass]*len(substitutions),
		[high_pass]*len(substitutions),
		[tr]*len(substitutions),
		[save_results]*len(substitutions),
		))

	return fc_maps
