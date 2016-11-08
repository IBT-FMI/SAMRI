#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker
from nipype.interfaces.io import DataFinder
import nibabel as nib
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from nilearn.input_data import NiftiMasker
sns.set_style("white", {'legend.frameon': True})
plt.style.use('ggplot')

import statsmodels.api as sm
import statsmodels.formula.api as smf
try:
	import maps, timeseries, dcm
except ImportError:
	from ..plotting import maps, timeseries, dcm

from statsmodels.sandbox.stats.multicomp import multipletests

import inspect

from itertools import product
from copy import deepcopy

qualitative_colorset = ["#000000", "#E69F00", "#56B4E9", "#009E73","#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass

def roi_per_session(l1_dir, sessions, subjects,
	legend_loc="best",
	roi="f_dr",
	figure="groups",
	tabref="tab",
	xy_label=[],
	):

	session_participant_format = "/home/chymera/NIdata/ofM.dr/l1/{0}/sub-{1}/ses-{2}/sub-{1}_ses-{2}_trial-7_EPI_CBV_tstat.nii.gz"

	voxeldf = pd.DataFrame({})
	subjectdf = pd.DataFrame({})
	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	masker = NiftiMasker(mask_img=roi_path)
	for subject, session in product(subjects, sessions):
		subject_data={}
		try:
			session_participant_file = session_participant_format.format(l1_dir,subject,session)
			img = nib.load(session_participant_file)
			img = masker.fit_transform(img)
			img = img.flatten()
			mean = np.nanmean(img)
		except (FileNotFoundError, nib.py3k.FileNotFoundError):
			img=[None]
		subject_data["session"]=session
		subject_data["subject"]=subject
		for i in img:
			voxel_data = deepcopy(subject_data)
			voxel_data["t"]=i
			df_ = pd.DataFrame(voxel_data, index=[None])
			voxeldf = pd.concat([voxeldf,df_])
		subject_data["t"]=mean
		df_ = pd.DataFrame(subject_data, index=[None])
		subjectdf = pd.concat([subjectdf,df_])

	obf_session={"ofM":"_pre","ofM_aF":"t1","ofM_cF1":"t2","ofM_cF2":"t3","ofM_pF":"post"}
	subjectdf = subjectdf.replace({"session": obf_session})
	subjectdf.to_csv("~/MixedLM_data.csv")

	model = smf.mixedlm("t ~ session", subjectdf, groups=subjectdf["subject"])
	fit = model.fit()
	report = fit.summary()
	latex_rep = report.as_latex()

	latex_conversion = {"Intercept":u"Intercept (Naïve)", "session[T.ofM_aF]":"Acute", "session[T.ofM_cF1]":"Chronic (2w)", "session[T.ofM_cF2]":"Phronic (4w)", "session[T.ofM_pF]":"Post"}
	latex_prepared = []
	for line in latex_rep.split("\n"):
		try:
			elements = line.split(" ")
		except AttributeError:
			pass
		else:
			if elements[0] in latex_conversion:
				if elements[1] != "RE":
					elements[0] = latex_conversion[elements[0]]
			line = " ".join(elements)
		latex_prepared.append(line)
		if "\\caption{" in line:
			latex_prepared.append("\\label{tab:"+tabref+"}")
	latex_prepared = "\n".join(latex_prepared)

	names_for_plotting = {"ofM":u"naïve", "ofM_aF":"acute", "ofM_cF1":"chronic (2w)", "ofM_cF2":"chronic (4w)", "ofM_pF":"post"}
	voxeldf = voxeldf.replace({"session": names_for_plotting})
	subjectdf = subjectdf.replace({"session": names_for_plotting})
	if figure == "per-voxel":
		ax = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject")
		# sns.violinplot(x="session", y="value", hue="subject", data=df, inner=None)
		if xy_label:
			ax.set(xlabel=xy_label[0], ylabel=xy_label[1])
	elif figure == "per-participant":
		ax = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject")
		if xy_label:
			ax.set(xlabel=xy_label[0], ylabel=xy_label[1])
	elif figure == "both":
		f, (ax1, ax2) = plt.subplots(1,2)
		ax1 = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject", ax=ax1)
		ax2 = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject",ax=ax2)
		if xy_label:
			ax1.set(xlabel=xy_label[0], ylabel=xy_label[1])
			ax2.set(xlabel=xy_label[0], ylabel=xy_label[1])

	return fit, report, latex_prepared

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

def fc_per_session(sessions, subjects, preprocessing_dir,
	l1_dir = None,
	l1_workdir = None,
	legend_loc="best",
	roi="f_dr",
	figure="maps",
	p_level=0.1,
	):

	if not l1_dir:
		l1_dir = preprocessing_dir
	if not l1_workdir:
		l1_workdir = l1_dir+"_work"

	df = pd.DataFrame({})
	timecourses = []
	stat_maps = []
	subplot_titles = []
	designs = []
	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	# masker = NiftiMasker(mask_img=roi_path, standardize=True)
	for subject, session in product(subjects, sessions):
		data={}
		timecourse_file = "/home/chymera/NIdata/ofM.dr/preprocessing/{2}/sub-{0}/ses-{1}/func/sub-{0}_ses-{1}_trial-7_EPI_CBV.nii.gz".format(subject,session,preprocessing_dir)
		cope_file = "/home/chymera/NIdata/ofM.dr/l1/{2}/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_cope.nii.gz".format(subject,session,l1_dir)
		session_participant_file = "/home/chymera/NIdata/ofM.dr/l1/{2}/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_pstat.nii.gz".format(subject,session,l1_dir)
		design_file = "/home/chymera/NIdata/ofM.dr/l1/{0}/_subject_session_scan_{1}.{2}.7_EPI_CBV/modelgen/run0.mat".format(l1_workdir,subject,session)
		try:
			img = nib.load(session_participant_file)
		except (FileNotFoundError, nib.py3k.FileNotFoundError):
			break
		else:
			data = img.get_data()
			header = img.header
			affine = img.affine
			shape = data.shape
			data = data.flatten()
			print(np.count_nonzero(data))
			nonzeros = np.nonzero(data)
			_, nonzero_data, _, _ = multipletests(data[nonzeros], p_level, method="fdr_bh")
			nonzero_mask = deepcopy(nonzero_data)
			nonzero_mask[nonzero_data <= p_level] = 1
			nonzero_mask[nonzero_data > p_level] = 0
			data[nonzeros] = nonzero_mask
			data = data.reshape(shape)
			print(np.count_nonzero(data))
			img = nib.Nifti1Image(data, affine, header)
		p_masker = NiftiMasker(mask_img=img)
		try:
			timecourse = p_masker.fit_transform(timecourse_file).T
			betas = p_masker.fit_transform(cope_file).T
		except ValueError:
			continue
		subplot_titles.append(" ".join([str(subject),str(session)]))
		timecourses.append(timecourse)
		design = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
		design = design*np.mean(betas)
		designs.append(design)
		stat_maps.append(img)

	if figure == "maps":
		maps.stat(stat_maps, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=0.1, interpolation="gaussian", subplot_titles=subplot_titles)
	elif figure == "timecourses":
		ncols = 2
		#we use inverse floor division to get the ceiling
		nrows = -(-len(timecourses)//2)
		fig, axes = plt.subplots(figsize=(8*nrows,7*ncols), facecolor='#eeeeee', nrows=nrows, ncols=ncols)
		for ix, timecourse in enumerate(timecourses):
			row = -(-(ix+1) // 2)
			col = (ix+1) // row
			ax = axes[row-1][col-1]
			ax.plot(np.mean(timecourses[ix], axis=0))
			ax.plot(designs[ix][[0]])
