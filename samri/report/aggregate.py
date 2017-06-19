# -*- coding: utf-8 -*-

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
		[t_file_template]*len(substitutions),
		[masker]*len(substitutions),
		substitutions,
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
			[t_file_template]*len(substitutions),
			[masker_normalize]*len(substitutions),
			substitutions,
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
