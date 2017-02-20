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

qualitative_colorset = ["#000000", "#E69F00", "#56B4E9", "#009E73","#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass

def add_roi_data(l1_dir,subject,session,masker):
	session_participant_format = "/home/chymera/NIdata/ofM.dr/l1/{0}/sub-{1}/ses-{2}/sub-{1}_ses-{2}_trial-7_EPI_CBV_tstat.nii.gz"
	subject_data={}
	try:
		session_participant_file = session_participant_format.format(l1_dir,subject,session)
		img = nib.load(session_participant_file)
		img = masker.fit_transform(img)
		img = img.flatten()
		mean = np.nanmean(img)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		subject_data["session"]=session
		subject_data["subject"]=subject
		for i in img:
			voxel_data = deepcopy(subject_data)
			voxel_data["t"]=i
			vdf = pd.DataFrame(voxel_data, index=[None])
		subject_data["t"]=mean
		sdf = pd.DataFrame(subject_data, index=[None])
		return sdf, vdf

def roi_per_session(l1_dir, subjects, sessions,
	legend_loc="best",
	roi="f_dr",
	figure="per-participant",
	tabref="tab",
	xy_label=[],
	obfuscate=False,
	color="#E69F00",
	):

	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	masker = NiftiMasker(mask_img=roi_path)

	iter_product = product(subjects, sessions)
	iter_subjects = []
	iter_sessions = []
	for i in iter_product:
		iter_subjects.append(i[0])
		iter_sessions.append(i[1])
	iter_len = len(iter_sessions)
	n_jobs = mp.cpu_count()-2
	roi_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(add_roi_data),
		[l1_dir]*iter_len,
		iter_subjects,
		iter_sessions,
		[masker]*iter_len,
		))
	subject_dfs, voxel_dfs = zip(*roi_data)
	subjectdf = pd.concat(subject_dfs)
	voxeldf = pd.concat(voxel_dfs)

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
		ax = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject")
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

def responders(l2_dir,
	roi="ctx_chr",
	data_root="~/NIdata/ofM.dr",
	roi_root="~/NIdata/templates/roi"
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

def bids_substitution_iterator(sessions, subjects, scans, preprocessing_dir,
	l1_dir=None,
	l1_workdir=None,
	):
	"""A convenience layer to the SAMRI data structure"""
	if not l1_dir:
		l1_dir = preprocessing_dir
	if not l1_workdir:
		l1_workdir = l1_dir+"_work"
	substitutions=[]
	for subject, session, scan in product(subjects, sessions, scans):
		substitution={}
		substitution["subject"] = subject
		substitution["session"] = session
		substitution["scan"] = scan
		substitution["preprocessing_dir"] = preprocessing_dir
		substitution["l1_dir"] = l1_dir
		substitution["l1_workdir"] = l1_workdir
		substitutions.append(substitution)
	return substitutions

def p_filtering(substitution, ts_file_template, beta_file_template, p_file_template, design_file_template, p_level):
	ts_file = os.path.expanduser(ts_file_template.format(**substitution))
	beta_file = os.path.expanduser(beta_file_template.format(**substitution))
	p_file = os.path.expanduser(p_file_template.format(**substitution))
	design_file = os.path.expanduser(design_file_template.format(**substitution))
	try:
		img = nib.load(p_file)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return None,None,None,None
	data = img.get_data()
	header = img.header
	affine = img.affine
	shape = data.shape
	data = data.flatten()
	# print(np.count_nonzero(data))
	nonzeros = np.nonzero(data)
	_, nonzero_data, _, _ = multipletests(data[nonzeros], p_level, method="fdr_bh")
	nonzero_mask = deepcopy(nonzero_data)
	nonzero_mask[nonzero_data <= p_level] = 1
	nonzero_mask[nonzero_data > p_level] = 0
	data[nonzeros] = nonzero_mask
	data = data.reshape(shape)
	# print(np.count_nonzero(data))
	mask_map = nib.Nifti1Image(data, affine, header)
	p_masker = NiftiMasker(mask_img=mask_map)
	try:
		timecourse = p_masker.fit_transform(ts_file).T
		betas = p_masker.fit_transform(beta_file).T
	except ValueError:
		return None,None,None,None
	subplot_title = "\n ".join([str(substitution["subject"]),str(substitution["session"])])
	timecourse = np.mean(timecourse, axis=0)
	design = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
	design = design*np.mean(betas)
	return timecourse, design, mask_map, subplot_title

def roi_masking(substitution, ts_file_template, beta_file_template, design_file_template, roi_path):
	ts_file = os.path.expanduser(ts_file_template.format(**substitution))
	beta_file = os.path.expanduser(beta_file_template.format(**substitution))
	design_file = os.path.expanduser(design_file_template.format(**substitution))

	masker = NiftiMasker(mask_img=roi_path)
	mask_map = nib.load(roi_path)
	try:
		timecourse = masker.fit_transform(ts_file).T
		betas = masker.fit_transform(beta_file).T
	except ValueError:
		return None,None,None,None
	subplot_title = "\n ".join([str(substitution["subject"]),str(substitution["session"])])
	timecourse = np.mean(timecourse, axis=0)
	design = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
	design = design*np.mean(betas)
	return timecourse, design, mask_map, subplot_title

def roi_ts(substitutions,roi_path,
	ts_file_template="~/NIdata/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	beta_file_template="~/NIdata/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
	design_file_template="~/NIdata/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
	):

	df = pd.DataFrame({})
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
		[roi_path]*len(substitutions),
		))
	timecourses, designs, stat_maps, subplot_titles = zip(*substitutions_data)

	timecourses = [x for x in timecourses if x is not None]
	designs = [x for x in designs if x is not None]
	stat_maps = [x for x in stat_maps if x is not None]
	subplot_titles = [x for x in subplot_titles if x is not None]

	return timecourses, designs, stat_maps, subplot_titles

def p_filtered_ts(substitutions,
	legend_loc="best",
	ts_file_template="~/NIdata/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	beta_file_template="~/NIdata/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
	p_file_template="~/NIdata/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_pstat.nii.gz",
	design_file_template="~/NIdata/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
	p_level=0.1,
	):

	df = pd.DataFrame({})
	timecourses = []
	stat_maps = []
	subplot_titles = []
	designs = []

	n_jobs = mp.cpu_count()-2
	substitutions_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(p_filtering),
		substitutions,
		[ts_file_template]*len(substitutions),
		[beta_file_template]*len(substitutions),
		[p_file_template]*len(substitutions),
		[design_file_template]*len(substitutions),
		[p_level]*len(substitutions),
		))
	timecourses, designs, stat_maps, subplot_titles = zip(*substitutions_data)

	timecourses = [x for x in timecourses if x is not None]
	designs = [x for x in designs if x is not None]
	stat_maps = [x for x in stat_maps if x is not None]
	subplot_titles = [x for x in subplot_titles if x is not None]

	return timecourses, designs, stat_maps, subplot_titles
