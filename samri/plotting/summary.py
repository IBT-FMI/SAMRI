#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from itertools import product
from copy import deepcopy

import nibabel as nib
import numpy as np
import multiprocessing as mp
import pandas as pd
import matplotlib.pyplot as plt
import seaborn.apionly as sns
import statsmodels.formula.api as smf
from joblib import Parallel, delayed
from nilearn.input_data import NiftiMasker
from nipype.interfaces.io import DataFinder
from statsmodels.sandbox.stats.multicomp import multipletests

try:
	import maps, timeseries
except ImportError:
	from ..plotting import maps, timeseries

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass

def add_roi_data(substitution,t_file_format,masker):
	"""Return a per-subject and a per-voxel dataframe containing the mean and voxelwise ROI t-scores"""
	subject_data={}
	try:
		t_file = t_file_format.format(**substitution)
		t_file = os.path.abspath(os.path.expanduser(t_file))
		img = nib.load(t_file)
		img = masker.fit_transform(img)
		img = img.flatten()
		mean = np.nanmean(img)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		subject_data["session"]=substitution["session"]
		subject_data["subject"]=substitution["subject"]
		voxel_datas=[]
		for ix, i in enumerate(img):
			voxel_data = deepcopy(subject_data)
			voxel_data["voxel"]=ix
			voxel_data["t"]=i
			voxel_data = pd.DataFrame(voxel_data, index=[None])
			voxel_datas.append(voxel_data)
		vdf = pd.concat(voxel_datas)
		subject_data["t"]=mean
		sdf = pd.DataFrame(subject_data, index=[None])
		return sdf, vdf

def add_pattern_data(substitution,t_file_format,pattern,
	voxels=False,
	):
	"""Return a per-subject and a per-voxel dataframe containing the mean and voxelwise multivariate patern scores"""
	subject_data={}
	try:
		t_file = t_file_format.format(**substitution)
		t_file = os.path.abspath(os.path.expanduser(t_file))
		img = nib.load(t_file)
		img_data = img.get_data()
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		pattern_evaluation = img_data*pattern
		pattern_evaluation = pattern_evaluation.flatten()
		pattern_score = np.nanmean(pattern_evaluation)
		subject_data["session"]=substitution["session"]
		subject_data["subject"]=substitution["subject"]
		if voxels:
			voxel_datas=[]
			for ix, i in enumerate(pattern_evaluation):
				voxel_data = deepcopy(subject_data)
				voxel_data["voxel"]=ix
				voxel_data["t"]=i
				voxel_data = pd.DataFrame(voxel_data, index=[None])
				voxel_datas.append(voxel_data)
			vdf = pd.concat(voxel_datas)
		else:
			vdf = False
		subject_data["t"]=pattern_score
		sdf = pd.DataFrame(subject_data, index=[None])
		return sdf, vdf

def roi_per_session(substitutions, roi_mask,
	legend_loc="best",
	t_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_tstat.nii.gz",
	roi_mask_normalize="",
	figure="per-participant",
	tabref="tab",
	xy_label=[],
	obfuscate=False,
	color="#E69F00",
	):
	"""Plot a ROI t-values over the session timecourse

	roi_mask : str
	Path to the ROI mask for which to select the t-values.

	figure : {"per-participant", "per-voxel", "both"}
	At what level to resolve the t-values. Per-participant compares participant means, per-voxel compares all voxel values, both creates two plots covering the aforementioned cases.

	roi_mask_normalize : str
	Path to a ROI mask by the mean of whose t-values to normalite the t-values in roi_mask.
	"""

	if isinstance(roi_mask,str):
		roi_mask = os.path.abspath(os.path.expanduser(roi_mask))
	masker = NiftiMasker(mask_img=roi_mask)

	n_jobs = mp.cpu_count()-2
	roi_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_roi_data),
		substitutions,
		[t_file_template]*len(substitutions),
		[masker]*len(substitutions),
		))
	subject_dfs, voxel_dfs = zip(*roi_data)
	subjectdf = pd.concat(subject_dfs)
	voxeldf = pd.concat(voxel_dfs)
	if roi_mask_normalize:
		figure="per-participant"
		if isinstance(roi_mask_normalize,str):
			mask_normalize = os.path.abspath(os.path.expanduser(roi_mask_normalize))
		masker_normalize = NiftiMasker(mask_img=mask_normalize)
		roi_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_roi_data),
			substitutions,
			[t_file_template]*len(substitutions),
			[masker_normalize]*len(substitutions),
			))
		subject_dfs_normalize, _ = zip(*roi_data)
		subjectdf_normalize = pd.concat(subject_dfs_normalize)

		subjectdf['t'] = subjectdf['t']/subjectdf_normalize['t']
		#this is a nasty hack to mitigate +/-inf values appearing if the normalization ROI mean is close to 0
		subjectdf_ = deepcopy(subjectdf)
		subjectdf_= subjectdf_.replace([np.inf, -np.inf], np.nan).dropna(subset=["t"], how="all")
		subjectdf=subjectdf.replace([-np.inf], subjectdf_[['t']].min(axis=0)[0])
		subjectdf=subjectdf.replace([np.inf], subjectdf_[['t']].max(axis=0)[0])

	if obfuscate:
		obf_session = {"ofM":"_pre","ofM_aF":"t1","ofM_cF1":"t2","ofM_cF2":"t3","ofM_pF":"post"}
		subjectdf = subjectdf.replace({"session": obf_session})
		subjectdf.to_csv("~/MixedLM_data.csv")

	model = smf.mixedlm("t ~ session", subjectdf, groups=subjectdf["subject"])
	fit = model.fit()
	report = fit.summary()

	# create a restriction for every regressor - except intercept (first) and random effects (last)
	omnibus_tests = np.eye(len(fit.params))[1:-1]
	anova = fit.f_test(omnibus_tests)

	names_for_plotting = {"ofM":u"naïve", "ofM_aF":"acute", "ofM_cF1":"chronic (2w)", "ofM_cF2":"chronic (4w)", "ofM_pF":"post"}
	voxeldf = voxeldf.replace({"session": names_for_plotting})
	subjectdf = subjectdf.replace({"session": names_for_plotting})

	if figure == "per-voxel":
		ax = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=90, dodge=True, jitter=True, legend_out=False, units="voxel")
		if xy_label:
			ax.set(xlabel=xy_label[0], ylabel=xy_label[1])
	elif figure == "per-participant":
		ax = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject", color=color)
		if xy_label:
			ax.set(xlabel=xy_label[0], ylabel=xy_label[1])
	elif figure == "both":
		f, (ax1, ax2) = plt.subplots(1,2)
		ax1 = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject", ax=ax1)
		ax2 = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject",ax=ax2, color=color)
		if xy_label:
			ax1.set(xlabel=xy_label[0], ylabel=xy_label[1])
			ax2.set(xlabel=xy_label[0], ylabel=xy_label[1])

	return fit, anova

def analytic_pattern_per_session(substitutions, analytic_pattern,
	legend_loc="best",
	t_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_tstat.nii.gz",
	roi_mask_normalize="",
	figure="per-participant",
	tabref="tab",
	xy_label=[],
	obfuscate=False,
	color="#E69F00",
	):
	"""Plot a ROI t-values over the session timecourse

	analytic_pattern : str
	Path to the analytic pattern by which to multiply the per-participant per-session t-statistic maps.

		roi_mask_normalize : str
	Path to a ROI mask by the mean of whose t-values to normalite the t-values in roi_mask.
	"""

	if isinstance(analytic_pattern,str):
		analytic_pattern = os.path.abspath(os.path.expanduser(analytic_pattern))
	analytic_pattern = nib.load(analytic_pattern)
	pattern_data = analytic_pattern.get_data()

	if figure == "per-participant":
		voxels = False
	else:
		voxels = True

	n_jobs = mp.cpu_count()-2
	roi_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_pattern_data),
		substitutions,
		[t_file_template]*len(substitutions),
		[pattern_data]*len(substitutions),
		[voxels]*len(substitutions),
		))
	subject_dfs, voxel_dfs = zip(*roi_data)
	subjectdf = pd.concat(subject_dfs)

	if obfuscate:
		obf_session = {"ofM":"_pre","ofM_aF":"t1","ofM_cF1":"t2","ofM_cF2":"t3","ofM_pF":"post"}
		subjectdf = subjectdf.replace({"session": obf_session})
		subjectdf.to_csv("~/MixedLM_data.csv")

	print(subjectdf)

	model = smf.mixedlm("t ~ session", subjectdf, groups=subjectdf["subject"])
	fit = model.fit()
	report = fit.summary()

	# create a restriction for every regressor - except intercept (first) and random effects (last)
	omnibus_tests = np.eye(len(fit.params))[1:-1]
	anova = fit.f_test(omnibus_tests)

	names_for_plotting = {"ofM":u"naïve", "ofM_aF":"acute", "ofM_cF1":"chronic (2w)", "ofM_cF2":"chronic (4w)", "ofM_pF":"post"}
	if voxels:
		voxeldf = pd.concat(voxel_dfs)
		voxeldf = voxeldf.replace({"session": names_for_plotting})
	subjectdf = subjectdf.replace({"session": names_for_plotting})

	ax = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject", color=color)
	if xy_label:
		ax.set(xlabel=xy_label[0], ylabel=xy_label[1])

	return fit, anova

def responders(l2_dir,
	roi="ctx_chr",
	data_root="~/ni_data/ofM.dr",
	roi_root="~/ni_data/templates/roi"
	):

	data_regex = "(?P<subject>.+)/tstat1.nii.gz"
	data_path = "{data_root}/l2/{l2_dir}/".format(data_root=data_root, l2_dir=l2_dir)
	data_path = os.path.expanduser(data_path)
	roi_path = "{roi_root}/{roi}.nii.gz".format(roi_root=roi_root, roi=roi)
	roi_path = os.path.expanduser(roi_path)

	data_find = DataFinder()
	data_find.inputs.root_paths = data_path
	data_find.inputs.match_regex = os.path.join(data_path,data_regex)
	found_data = data_find.run().outputs

	masker = NiftiMasker(mask_img=roi_path)
	voxeldf = pd.DataFrame({})
	for subject, data_file in zip(found_data.subject, found_data.out_paths):
		subject_data = {}
		print(subject, data_file)
		img = nib.load(data_file)
		img = masker.fit_transform(img)
		img = img.flatten()
		subject_data["subject"]=subject
		for i in img:
			voxel_data = deepcopy(subject_data)
			voxel_data["t"]=i
			df_ = pd.DataFrame(voxel_data, index=[None])
			voxeldf = pd.concat([voxeldf,df_])

def p_roi_masking(substitution, ts_file_template, beta_file_template, p_file_template, design_file_template, event_file_template, p_level, brain_mask):
	"""Apply a substitution pattern to timecourse, beta, and design file templates - and mask the data of the former two according to a roi. Subsequently scale the design by the mean beta.

	Parameters
	----------

	substitution : dict
	A dictionary containing the template replacement fields as keys and identifiers as values.

	ts_file_template : string
	Timecourse file template with replacement fields. The file should be in NIfTI format.

	beta_file_template : string
	Beta file template with replacement fields. The file should be in NIfTI format.

	design_file_template : string
	Design file template with replacement fields. The file should be in CSV format.

	roi_path : string
	Path to the region of interest file based on which to create a mask for the time course and beta files. The file should be in NIfTI format.

	brain_mask : string
	Path to the a mask file in the *exact same* coordinate space as the input image. This is very important, as the mask is needed to crop out artefactual p=0 values. These cannot just be filtered out nummerically, since it is possible that the GLM resturns p=0 for the most significant results.

	Returns
	-------

	timecourse : array_like
	Numpy array containing the mean timecourse in the region of interest.

	design : array_like
	Numpy array containing the regressor scaled by the mean beta value of the region of interest..

	mask_map : data
	Nibabel image of the mask

	subplot_title : string
	Title for the subplot, computed from the substitution fields.
	"""

	ts_file = os.path.abspath(os.path.expanduser(ts_file_template.format(**substitution)))
	beta_file = os.path.abspath(os.path.expanduser(beta_file_template.format(**substitution)))
	p_file = os.path.abspath(os.path.expanduser(p_file_template.format(**substitution)))
	design_file = os.path.abspath(os.path.expanduser(design_file_template.format(**substitution)))
	event_file = os.path.abspath(os.path.expanduser(event_file_template.format(**substitution)))
	brain_mask = os.path.abspath(os.path.expanduser(brain_mask))
	try:
		img = nib.load(p_file)
		brain_mask = nib.load(brain_mask)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return None,None,None,None,None
	data = img.get_data()
	brain_mask = brain_mask.get_data()
	header = img.header
	affine = img.affine
	shape = data.shape
	data = data.flatten()
	brain_mask = brain_mask.flatten()
	brain_mask = brain_mask.astype(bool)
	brain_data = data[brain_mask]
	reject, nonzero_data, _, _ = multipletests(brain_data, p_level, method="fdr_bh")
	brain_mask[brain_mask]=reject
	brain_mask = brain_mask.astype(int)
	mask = brain_mask.reshape(shape)
	mask_map = nib.Nifti1Image(mask, affine, header)
	masker = NiftiMasker(mask_img=mask_map)
	try:
		timecourse = masker.fit_transform(ts_file).T
		betas = masker.fit_transform(beta_file).T
	except ValueError:
		return None,None,None,None,None
	subplot_title = "\n ".join([str(substitution["subject"]),str(substitution["session"])])
	timecourse = np.mean(timecourse, axis=0)
	design = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
	design = design*np.mean(betas)
	event_df = pd.read_csv(event_file, sep="\t")

	return timecourse, design, mask_map, event_df, subplot_title

def roi_masking(substitution, ts_file_template, beta_file_template, design_file_template, event_file_template, roi_path):
	"""Apply a substitution pattern to timecourse, beta, and design file templates - and mask the data of the former two according to a roi. Subsequently scale the design by the mean beta.

	Parameters
	----------

	substitution : dict
	A dictionary containing the template replacement fields as keys and identifiers as values.

	ts_file_template : string
	Timecourse file template with replacement fields. The file should be in NIfTI format.

	beta_file_template : string
	Beta file template with replacement fields. The file should be in NIfTI format.

	design_file_template : string
	Design file template with replacement fields. The file should be in CSV format.

	roi_path : string
	Path to the region of interest file based on which to create a mask for the time course and beta files. The file should be in NIfTI format.

	Returns
	-------

	timecourse : array_like
	Numpy array containing the mean timecourse in the region of interest.

	design : array_like
	Numpy array containing the regressor scaled by the mean beta value of the region of interest..

	mask_map : data
	Nibabel image of the mask

	subplot_title : string
	Title for the subplot, computed from the substitution fields.
	"""

	ts_file = os.path.expanduser(ts_file_template.format(**substitution))
	beta_file = os.path.expanduser(beta_file_template.format(**substitution))
	design_file = os.path.expanduser(design_file_template.format(**substitution))
	event_file = os.path.expanduser(event_file_template.format(**substitution))

	masker = NiftiMasker(mask_img=roi_path)
	mask_map = nib.load(roi_path)
	try:
		timecourse = masker.fit_transform(ts_file).T
		betas = masker.fit_transform(beta_file).T
		design = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
		event_df = pd.read_csv(event_file, sep="\t")
	except ValueError:
		return None,None,None,None,None
	subplot_title = "\n ".join([str(substitution["subject"]),str(substitution["session"])])
	timecourse = np.mean(timecourse, axis=0)
	design = design*np.mean(betas)

	return timecourse, design, mask_map, event_df, subplot_title

def ts_overviews(substitutions, roi_path,
	ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	beta_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
	design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
	event_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
	):

	timecourses = []
	stat_maps = []
	subplot_titles = []
	designs = []
	roi_path = os.path.expanduser(roi_path)

	n_jobs = mp.cpu_count()-2
	substitutions_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(roi_masking),
		substitutions,
		[ts_file_template]*len(substitutions),
		[beta_file_template]*len(substitutions),
		[design_file_template]*len(substitutions),
		[event_file_template]*len(substitutions),
		[roi_path]*len(substitutions),
		))
	timecourses, designs, stat_maps, event_dfs, subplot_titles = zip(*substitutions_data)

	#The following is safe because either all are None at a given position, or none of them is None
	timecourses = [x for x in timecourses if x is not None]
	designs = [x for x in designs if x is not None]
	stat_maps = [x for x in stat_maps if x is not None]
	events_dfs = [x for x in event_dfs if x is not None]
	subplot_titles = [x for x in subplot_titles if x is not None]

	return timecourses, designs, stat_maps, events_dfs, subplot_titles

def p_filtered_ts(substitutions,
	ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	beta_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
	p_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_pstat.nii.gz",
	design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
	event_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
	p_level=0.1,
	brain_mask="~/ni_data/templates/DSURQEc_200micron_average.niis"
	):

	timecourses = []
	stat_maps = []
	subplot_titles = []
	designs = []

	n_jobs = mp.cpu_count()-2
	substitutions_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(p_roi_masking),
		substitutions,
		[ts_file_template]*len(substitutions),
		[beta_file_template]*len(substitutions),
		[p_file_template]*len(substitutions),
		[design_file_template]*len(substitutions),
		[event_file_template]*len(substitutions),
		[p_level]*len(substitutions),
		[brain_mask]*len(substitutions),
		))
	timecourses, designs, stat_maps, event_dfs, subplot_titles = zip(*substitutions_data)

	timecourses = [x for x in timecourses if x is not None]
	designs = [x for x in designs if x is not None]
	stat_maps = [x for x in stat_maps if x is not None]
	events_dfs = [x for x in event_dfs if x is not None]
	subplot_titles = [x for x in subplot_titles if x is not None]

	return timecourses, designs, stat_maps, events_dfs, subplot_titles
