# -*- coding: utf-8 -*-
import errno
import multiprocessing as mp
import nibabel
import numpy as np
from copy import deepcopy
from joblib import Parallel, delayed
from nilearn.connectome import ConnectivityMeasure
from nilearn.input_data import NiftiLabelsMasker, NiftiMasker
from nipype.interfaces import fsl
from os import path, makedirs
import scipy
import scipy.cluster.hierarchy as hier_clustering
import pylab
from numpy import genfromtxt

def add_fc_roi_data(data_path, seed_masker, brain_masker,
	dictionary_return=False,
	save_as="",
	substitution={},
	):
	"""Return a volumetric image of the seed-based functional connectivity (FC) with respect to the `seed_masker` inside the `brain_masker`.

	Parameters
	----------

	data_path : str
		Path to 4D data for which to estimate functional connectivity.
		It can be a formattable string containing key references from the `substitutions` dictionary.
	seed_masker : nilearn.input_data.NiftiMasker
		A `nilearn.input_data.NiftiMasker` object delineating the seed region.
	brain_masker : nilearn.input_data.NiftiMasker
		A `nilearn.input_data.NiftiMasker` object delineating the region in which to calculate voxelwise FC scores.
	dictionary_return : bool, optional
		Whether to return the resulting FC NIfTI image as the value of the "result" key of a dictionary
		(whose other keys are those provided inside the `substitution` dictionary).
	save_as : str, optional
		Path under which to save the resultind NIfTI.
		It can be a formattable string containing key references from the `substitutions` dictionary.
	substitution : dict, optional
		Dictionary containig keys corresponding to the formattable fields in `data_path` and/or `save_as`. If `dictionary_return` is `True`, the resulting FC NIfTI will be appended to this dictionary under the `'result'` key.

	Returns
	-------

	str or nibabel.nifti1.Nifti1Image or dict
		Either a path to the produced FC NIfTI file on disk (if `save_as` is defined, but not `dictionary_retutn`), or a `nibabel.nifti1.Nifti1Image` object (if `save_as` and `dictionary_return` are both undefined), or a dictionary which is a copy of `substitutions` and contains a path to the produced FC NIfTI file on disk under the `'result'` key (if `save_as` and `return_dictionary` are both defined), or a dictionary which is a copy of `substitutions` and contains a `nibabel.nifti1.Nifti1Image` object under the `'result'` key (if `save_as` is not defined, but `dictonary_return` is).
	"""

	if dictionary_return and not substitution:
		print('WARNING: If you want a dictionary returned (as selected via the `dictionary_return` parameter), you should provide a `substitution` dictionary.')

	result = deepcopy(substitution)

	if 'path' in substitution:
		data_path = substitution['path']
	elif substitution:
		data_path = data_path.format(**substitution)
	data_path = path.abspath(path.expanduser(data_path))

	if not path.isfile(data_path):
		print("WARNING: File \"{}\" does not exist.".format(data_path))
		if dictionary_return:
			result["result"] = None
			return result

	seed_time_series = seed_masker.fit_transform(data_path,).T
	seed_time_series = np.mean(seed_time_series, axis=0)
	brain_time_series = brain_masker.fit_transform(data_path,)
	seed_based_correlations = np.dot(brain_time_series.T, seed_time_series) / seed_time_series.shape[0]
	seed_based_correlations_fisher_z = np.arctanh(seed_based_correlations)
	seed_based_correlation_img = brain_masker.inverse_transform(seed_based_correlations_fisher_z.T)

	if save_as:
		if substitution:
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
		if dictionary_return:
			result["result"] = save_as
		else:
			result = save_as
	elif dictionary_return:
		result["result"] = seed_based_correlation_img
	else:
		result = seed_based_correlation_img

	return result

def seed_based(substitutions, seed, roi,
	ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_task-{task}.nii.gz",
	smoothing_fwhm=.3,
	detrend=True,
	standardize=True,
	low_pass=0.25,
	high_pass=0.004,
	tr=1.,
	save_results="",
	n_procs=2,
	cachedir='',
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
			memory=cachedir, memory_level=1, verbose=0
			)
	brain_masker = NiftiMasker(
			mask_img=roi_mask,
			smoothing_fwhm=smoothing_fwhm,
			detrend=detrend,
			standardize=standardize,
			low_pass=low_pass,
			high_pass=high_pass,
			t_r=tr,
			memory=cachedir, memory_level=1, verbose=0
			)


	fc_maps = Parallel(n_jobs=n_procs, verbose=0, backend="threading")(map(delayed(add_fc_roi_data),
		[ts_file_template]*len(substitutions),
		[seed_masker]*len(substitutions),
		[brain_masker]*len(substitutions),
		[True]*len(substitutions),
		[save_results]*len(substitutions),
		substitutions,
		))

	return fc_maps

def dual_regression(substitutions_a, substitutions_b,
	all_merged_path="~/all_merged.nii.gz",
	components=9,
	group_level="concat",
	tr=1,
	ts_file_template="{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_task-{scan}.nii.gz",
	):

	all_merged_path = path.abspath(path.expanduser(all_merged_path))

	ts_a = []
	for substitution in substitutions_a:
		ts_a.append(path.abspath(path.expanduser(ts_file_template.format(**substitution))))
	ts_b = []
	for substitution in substitutions_b:
		ts_b.append(path.abspath(path.expanduser(ts_file_template.format(**substitution))))

	ts_all = ts_a + ts_b
	if group_level == "concat" and not path.isfile(all_merged_path):
		ts_all_merged = nibabel.concat_images(ts_all, axis=3)
		ts_all_merged.to_filename(all_merged_path)

	ica = fsl.model.MELODIC()
	ica.inputs.report = True
	ica.inputs.tr_sec = tr
	ica.inputs.no_bet = True
	ica.inputs.no_mask = True
	ica.inputs.sep_vn = True
	if components:
		ica.inputs.dim = int(components)
	if group_level == "migp":
		ica.inputs.in_files = ts_all
		ica._cmd = 'melodic --migp'
	elif group_level == "concat":
		ica.inputs.approach = "concat"
		ica.inputs.in_files = all_merged_path
	print(ica.cmdline)
	ica_run = ica.run()

def get_signal(substitutions_a, substitutions_b,
	functional_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_task-{scan}.nii.gz",
	mask="~/ni_data/templates/DSURQEc_200micron_bin.nii.gz",
	):

	mask = path.abspath(path.expanduser(mask))

	out_t_names = []
	out_cope_names = []
	out_varcb_names = []
	for substitution in substitutions_a+substitutions_b:
		ts_name = path.abspath(path.expanduser("{subject}_{session}.mat".format(**substitution)))
		out_t_name = path.abspath(path.expanduser("{subject}_{session}_tstat.nii.gz".format(**substitution)))
		out_cope_name = path.abspath(path.expanduser("{subject}_{session}_cope.nii.gz".format(**substitution)))
		out_varcb_name = path.abspath(path.expanduser("{subject}_{session}_varcb.nii.gz".format(**substitution)))
		out_t_names.append(out_t_name)
		out_cope_names.append(out_cope_name)
		out_varcb_names.append(out_varcb_name)
		functional_file = path.abspath(path.expanduser(functional_file_template.format(**substitution)))
		if not path.isfile(ts_name):
			masker = NiftiMasker(mask_img=mask)
			ts = masker.fit_transform(functional_file).T
			ts = np.mean(ts, axis=0)
			header = "/NumWaves 1\n/NumPoints 1490\n/PPheights 1.308540e+01 4.579890e+00\n\n/Matrix"
			np.savetxt(ts_name, ts, delimiter="\n", header=header, comments="")
		glm = fsl.GLM(in_file=functional_file, design=ts_name, output_type='NIFTI_GZ')
		glm.inputs.contrasts = path.abspath(path.expanduser("run0.con"))
		glm.inputs.out_t_name = out_t_name
		glm.inputs.out_cope = out_cope_name
		glm.inputs.out_varcb_name = out_varcb_name
		print(glm.cmdline)
		glm_run=glm.run()

	copemerge = fsl.Merge(dimension='t')
	varcopemerge = fsl.Merge(dimension='t')

def seed_based_connectivity(ts, seed_mask,
	brain_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	smoothing_fwhm=.3,
	detrend=True,
	standardize=True,
	low_pass=0.25,
	high_pass=0.004,
	tr=1.,
	save_as="",
	):
	"""Return a NIfTI containing z scores for connectivity to a defined seed region

	Parameters
	----------

	ts : string
	Path to the 4D NIfTI timeseries file on which to perform the connectivity analysis.

	seed_mask : string
	Path to a 3D NIfTI-like binary mask file designating the seed region.

	smoothing_fwhm : float, optional
	Spatial smoothing kernel, passed to the NiftiMasker.

	detrend : bool, optional
	Whether to detrend the data, passed to the NiftiMasker.

	standardize : bool, optional
	Whether to standardize the data (make mean 0. and variance 1.), passed to the NiftiMasker.

	low_pass : float, optional
	Low-pass cut-off, passed to the NiftiMasker.

	high_pass : float, optional
	High-pass cut-off, passed to the NiftiMasker.

	tr : float, optional
	Repetition time, passed to the NiftiMasker.

	save_as : string, optional
	Path to save a NIfTI of the functional connectivity zstatistic to.

	Notes
	-----

	Contains sections of code copied from the nilearn examples:
	http://nilearn.github.io/auto_examples/03_connectivity/plot_seed_to_voxel_correlation.html#sphx-glr-auto-examples-03-connectivity-plot-seed-to-voxel-correlation-py
	"""

	brain_mask = path.abspath(path.expanduser(brain_mask))
	seed_mask = path.abspath(path.expanduser(seed_mask))
	save_as = path.abspath(path.expanduser(save_as))
	ts = path.abspath(path.expanduser(ts))

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
		mask_img=brain_mask,
		smoothing_fwhm=smoothing_fwhm,
		detrend=detrend,
		standardize=standardize,
		low_pass=low_pass,
		high_pass=high_pass,
		t_r=tr,
		memory='nilearn_cache', memory_level=1, verbose=0
		)
	seed_time_series = seed_masker.fit_transform(ts,).T
	seed_time_series = np.mean(seed_time_series, axis=0)
	brain_time_series = brain_masker.fit_transform(ts,)

	seed_based_correlations = np.dot(brain_time_series.T, seed_time_series) / seed_time_series.shape[0]
	try:
		print("seed-based correlation shape: (%s, %s)" % seed_based_correlations.shape)
	except TypeError:
		print("seed-based correlation shape: (%s, )" % seed_based_correlations.shape)
	print("seed-based correlation: min = %.3f; max = %.3f" % (seed_based_correlations.min(), seed_based_correlations.max()))

	seed_based_correlations_fisher_z = np.arctanh(seed_based_correlations)
	print("seed-based correlation Fisher-z transformed: min = %.3f; max = %.3f" % (seed_based_correlations_fisher_z.min(),seed_based_correlations_fisher_z.max()))

	seed_based_correlation_img = brain_masker.inverse_transform(seed_based_correlations_fisher_z.T)

	if save_as:
		seed_based_correlation_img.to_filename(save_as)

	return seed_based_correlation_img

def correlation_matrix(ts,atlas,
	confounds=None,
	mask='',
	loud=False,
	structure_names=[],
	save_as='',
	low_pass=0.25,
	high_pass=0.004,
	smoothing_fwhm=.3,
	):
	"""Return a CSV file containing correlations between ROIs.

	Parameters
	----------
	ts : str
		Path to the 4D NIfTI timeseries file on which to perform the connectivity analysis.
	confounds : 2D array OR path to CSV file
		Array/CSV file containing confounding time-series to be regressed out before FC analysis.
	atlas : str, optional
		Path to a 3D NIfTI-like binary label file designating ROIs.
	structure_names : list, optional
		Ordered list of all structure names in atlas (length N).
	save_as : str
		Path under which to save the Pandas DataFrame conttaining the NxN correlation matrix.
	"""
	ts = path.abspath(path.expanduser(ts))
	atlas = path.abspath(path.expanduser(atlas))
	if mask:
		mask = path.abspath(path.expanduser(mask))
	tr = nib.load(ts).header['pixdim'][0]
	labels_masker = NiftiLabelsMasker(
		labels_img=atlas,
		mask_img=mask,
		standardize=True,
		memory='nilearn_cache',
		verbose=5,
		low_pass=low_pass,
		high_pass = high_pass,
		smoothing_fwhm=smoothing_fwhm,
		t_r=tr,
		)
	#TODO: test confounds with physiological signals
	if(confounds):
		confounds = path.abspath(path.expanduser(confounds))
		timeseries = labels_masker.fit_transform(ts, confounds=confounds)
	else:
		timeseries = labels_masker.fit_transform(ts)
	correlation_measure = ConnectivityMeasure(kind='correlation')
	correlation_matrix = correlation_measure.fit_transform([timeseries])[0]
	if structure_names:
		df = pd.DataFrame(columns=structure_names, index=structure_names, data=correlation_matrix)
	else:
		df = pd.DataFrame(data=correlation_matrix)
	if save_as:
		save_dir = path.dirname(save_as)
		if not path.exists(save_dir):
			makedirs(save_dir)
		df.to_csv(save_as)


def dendogram(correlation_matrix,
	save_as = '',
	figsize=(50,50),
	):

	correlation_matrix = path.abspath(path.expanduser(correlation_matrix))

	y = hier_clustering(correlation_matrix, method='centroid')
	z = hier_clustering(y, orientation='right')

	fig = pylab.figure(figsize=figsize)
	ax_1 = fig.add_axes([0.1,0.1,0.2,0.8])
	ax_1.set_xticks([])
	ax_1.set_yticks([])

	ax_2 = fig.add_axes([0.3,0.1,0.6,0.8])
	index = z['leaves']
	correlation_matrix = correlation_matrix[index,:]
	correlation_matrix = correlation_matrix[:,index]
	im = ax_2.matshow(correlation_matrix, aspect='auto', origin='lower')
	ax_2.set_xticks([])
	ax_2.set_yticks([])

	ax_color = fig.add_axes([0.91,0.1,0.02,0.8])
	colorbar = pylab.colorbar(im, cax=ax_color)
	colorbar.ax.tick_params(labelsize=75)

	# Display and save figure.
	if(save_as):
		fig.savefig(path.abspath(path.expanduser(save_as)))
