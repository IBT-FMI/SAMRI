import nibabel
import numpy as np
from os import path


from nilearn.input_data import NiftiMasker, NiftiLabelsMasker
from nilearn.connectome import ConnectivityMeasure
from nipype.interfaces import fsl

def dual_regression(substitutions_a, substitutions_b,
	all_merged_path="~/all_merged.nii.gz",
	components=9,
	group_level="concat",
	tr=1,
	ts_file_template="{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
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
	functional_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
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
	brain_mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
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

def correlation_matrix(ts,
	confounds=None,
	labels_img='',
	loud = False,
	save_as = '',
	):
	"""Return a csv containing correlations between ROIs.

	Parameters
	----------

	ts : string
	Path to the 4D NIfTI timeseries file on which to perform the connectivity analysis.

	labels_img: string
	Path to a 3D NIfTI-like binary label file designating ROIs.

	safe_as : str

	confounds : 2D array OR path to CSV file
	Array/CSV file containing confounding time-series to be regressed out before FC analysis.

	"""
	ts = path.abspath(path.expanduser(ts))
	labels_img = path.abspath(path.expanduser(labels_img))

	labels_masker = NiftiLabelsMasker(
		labels_img=labels_img,
		standardize=True,
		memory='nilearn_cache',
		verbose=5
		)

	#TODO: test confounds with physiological signals
	if(confounds):
		confounds = path.abspath(path.expanduser(confounds))
		timeseries = labels_masker.fit_transform(ts, confounds=confounds)
	else:
		timeseries = labels_masker.fit_transform(ts)

	correlation_measure = ConnectivityMeasure(kind='correlation')
	correlation_matrix = correlation_measure.fit_transform([timeseries])[0]

	if save_as:
		np.savetxt(path.abspath(path.expanduser(save_as)), correlation_matrix, delimiter=',')

	return correlation_matrix
