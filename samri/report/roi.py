import nibabel as nib
import numpy as np
from os import path

from nilearn.input_data import NiftiMasker
from scipy.io import loadmat
from samri.report.utilities import roi_df, pattern_df
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
	atlas='',
	mapping='',
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
	dfs = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(roi_df),
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
	else:
		masker = NiftiMasker(mask_img=mask)
		roi_df(img_path,masker)

def atlasassignment(data_path='~/ni_data/ofM.dr/bids/l2/anova/anova_zfstat.nii.gz',
	null_label=0.0,
	verbose=False,
	lateralized=False,
	):
	'''
	Create CSV file containing a tabular summary of mean image intensity per DSURQE region of interest.
	'''

	from copy import deepcopy

	atlas_filename = '/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii'
	mapping = '/usr/share/mouse-brain-atlases/dsurqec_labels.csv'
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
	dfs = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(pattern_df),
		[t_file_template]*len(substitutions),
		[pattern]*len(substitutions),
		substitutions,
		))
	df = pd.concat(dfs)

	return df

def drs_activity(roi,
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii',
	mapping='/usr/share/mouse-brain-atlases/dsurqe_labels.csv',
	):
	"""
	TODO : make more generalizable, too many hardcoded values
	TODO : Make more elegant, atlas/split could be (partly) relegated to masking function instead of being done here.
	Create a DataFrame containing the per-session per-subject mean values for an autogenerated ROI based on the given label.
	Other parameter customizations are hard-coded below.
	"""
	import pandas as pd
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel
	from os.path import basename, splitext

	if mapping and atlas:
		mapping = path.abspath(path.expanduser(mapping))
		atlas = path.abspath(path.expanduser(atlas))
		my_roi = roi_from_atlaslabel(atlas,
			mapping=mapping,
			label_names=[roi],
			)
		roi_name = roi
	else:
		roi = path.abspath(path.expanduser(roi))
		roi_name = splitext(basename(roi))[0]
		if roi_name[-4:] == '.nii':
			roi_name = roi_name[:-4]

	source_workflow = 'generic'
	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
                ["CogB",],
                "~/ni_data/ofM.dr",
                source_workflow,
                acquisitions=["EPI",],
                validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	if mapping and atlas:
		df = roi.per_session(substitutions,
			filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
			roi_mask=my_roi,
			feature=[roi],
			atlas=atlas,
			mapping=mapping,
			)
	else:
		df = roi.per_session(substitutions,
			filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
			roi_mask=roi,
			)
	df['treatment']='Fluoxetine'
	substitutions_ = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		["6262","6255","5694","5706",'5704','6455','6459'],
                ["CogB",],
                "~/ni_data/ofM.dr",
                source_workflow,
                acquisitions=["EPI",],
		validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	if mapping and atlas:
		df_ = roi.per_session(substitutions_,
			filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
			roi_mask=my_roi,
			feature=[roi],
			atlas=atlas,
			mapping=mapping,
			)
	else:
		df_ = roi.per_session(substitutions_,
			filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
			roi_mask=roi,
			)
	df_['treatment']='Vehicle'

	df=pd.concat([df_,df])
	df=df.rename(columns={'session': 'Session',})

	df.to_csv('~/ni_data/ofM.dr/l1/{}/{}.csv'.format(source_workflow, roi_name))
