#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker
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
from statsmodels.stats.anova import anova_lm
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

def roi_per_session(sessions, subjects,
	legend_loc="best",
	roi="f_dr",
	figure="groups",
	tabref="tab",
	xy_label=[],
	):

	voxeldf = pd.DataFrame({})
	subjectdf = pd.DataFrame({})
	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	masker = NiftiMasker(mask_img=roi_path)
	for subject, session in product(subjects, sessions):
		subject_data={}
		try:
			session_participant_file = "/home/chymera/NIdata/ofM.dr/l1/blur_dr/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_tstat.nii.gz".format(subject,session)
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


def fc_per_session(sessions, subjects,
	legend_loc="best",
	roi="f_dr",
	):

	df = pd.DataFrame({})
	stat_maps=[]
	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	masker = NiftiMasker(mask_img=roi_path, standardize=True)
	for subject, session in product(subjects, sessions):
		data={}
		session_participant_file = "/home/chymera/NIdata/ofM.dr/l1/blur_dr/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_pstat.nii.gz".format(subject,session)
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
			_, nonzero_data, _, _ = multipletests(data[nonzeros], 0.01, method="fdr_bh")
			nonzero_mask = deepcopy(nonzero_data)
			nonzero_mask[nonzero_data <= 0.01] = 1
			nonzero_mask[nonzero_data > 0.01] = 0
			data[nonzeros] = nonzero_mask
			data = data.reshape(shape)
			print(np.count_nonzero(data))
			img = nib.Nifti1Image(data, affine, header=header)
		stat_maps.append(img)
	maps.stat(stat_maps, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=0.1, interpolation="gaussian")
