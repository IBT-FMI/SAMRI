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
import maps, timeseries, dcm
from statsmodels.sandbox.stats.multicomp import multipletests


from itertools import product
from copy import deepcopy

qualitative_colorset = ["#000000", "#E69F00", "#56B4E9", "#009E73","#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass

def roi_per_session(subjects, legend_loc="best", roi="f_dr", figure="groups"):
	sessions = ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]
	voxeldf = pd.DataFrame({})
	subjectdf = pd.DataFrame({})
	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	masker = NiftiMasker(mask_img=roi_path, standardize=True)
	for subject, session in product(subjects, sessions):
		subject_data={}
		try:
			session_participant_file = "/home/chymera/NIdata/ofM.dr/l1/blur_dr/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_tstat.nii.gz".format(subject,session)
			img = nib.load(session_participant_file)
			img = masker.fit_transform(img)
			# img = img[np.where(abs(img) >= 3 )]
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

	# lm = ols('mean ~ session', data=df_means).fit()
	# report = anova_lm(lm)

	model = smf.mixedlm("t ~ session", subjectdf, groups=subjectdf["subject"])
	fit = model.fit()
	report = fit.summary()

	names_for_plotting = {"ofM":u"naïve", "ofM_aF":"acute", "ofM_cF1":"chronic (2w)", "ofM_cF2":"chronic (4w)", "ofM_pF":"post"}
	voxeldf = voxeldf.replace({"session": names_for_plotting})
	subjectdf = subjectdf.replace({"session": names_for_plotting})
	if figure == "per-voxel":
		ax = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject")
		# sns.violinplot(x="session", y="value", hue="subject", data=df, inner=None)
		ax.set(ylabel='Voxel t-values', xlabel='Fluoxetine Treatment Timepoint')
	elif figure == "per-participant":
		ax = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject")
		ax.set(ylabel='Participant t-values', xlabel='Fluoxetine Treatment Timepoint')
	elif figure == "both":
		f, (ax1, ax2) = plt.subplots(1,2)
		ax1 = sns.pointplot(x="session", y="t", hue="subject", data=voxeldf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject", ax=ax1)
		ax1.set(ylabel='Voxel t-values', xlabel='Fluoxetine Treatment Timepoint')
		ax2 = sns.pointplot(x="session", y="t", data=subjectdf, ci=68.3, dodge=True, jitter=True, legend_out=False, units="subject",ax=ax2)
		ax2.set(ylabel='Participant t-values', xlabel='Fluoxetine Treatment Timepoint')

	return report


def fc_per_session(subjects, legend_loc="best", roi="f_dr"):
	sessions = ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]
	sessions = ["ofM","ofM_aF","ofM_cF1"]
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
			_, nonzero_data, _, _ = multipletests(data[nonzeros], 0.05, method="fdr_bh")
			nonzero_mask = deepcopy(nonzero_data)
			nonzero_mask[nonzero_data <= 0.05] = 1
			nonzero_mask[nonzero_data > 0.05] = 0
			data[nonzeros] = nonzero_mask
			data = data.reshape(shape)
			print(np.count_nonzero(data))
			img = nib.Nifti1Image(data, affine, header=header)
		stat_maps.append(img)
	maps.stat(stat_maps, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=0.1, interpolation="gaussian")

if __name__ == '__main__':
	# roi_per_session(subjects=[4007,4008,4009,4011,4012], legend_loc=2, figure="both")
	fc_per_session([4007,4008,4009,4011,4012])
	plt.show()
