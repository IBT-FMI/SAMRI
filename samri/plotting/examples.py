import matplotlib.pyplot as plt

from samri.utilities import bids_substitution_iterator
import maps, timeseries, summary, network

def overview(workflow, identifiers,
	cut_coords=[None],
	threshold=2.5,
	template="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	):
	"""Plot the statistical maps per-factor from a 2nd level GLM workflow result directory."""
	stat_maps = ["/home/chymera/ni_data/ofM.dr/l2/{0}/{1}/tstat1.nii.gz".format(workflow, i) for i in identifiers]
	if isinstance(cut_coords[0], int):
		cut_coords = [cut_coords]
	maps.stat(stat_maps, template=template, threshold=threshold, interpolation="gaussian", figure_title=workflow, subplot_titles=identifiers, cut_coords=cut_coords)

def blur_kernel_compare_dr(conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], parameters=["level2_dgamma","level2_dgamma_blurxy4","level2_dgamma_blurxy5", "level2_dgamma_blurxy6", "level2_dgamma_blurxy7"], threshold=3):
	from matplotlib.backends.backend_pdf import PdfPages
	pp = PdfPages('/home/chymera/DR.pdf')
	for condition in conditions:
		stat_maps = ["~/ni_data/ofM.dr/GLM/"+parameter+"/_category_multi_"+condition+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		maps.stat(stat_maps, cut_coords=(-49,8,43), threshold=threshold, interpolation="none", template="~/ni_data/templates/hires_QBI_chr.nii.gz", save_as=pp, figure_title=condition, subplot_titles=parameters)
	pp.close()

def roi_per_session(l1_dir, roi_mask, color,
	roi_mask_normalize="",
	):
	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		# ["5689","5690","5691"],
		["4005","5687","4007","4011","4012","5689","5690","5691"],
		# ["4007","4011","4012","5689","5690","5691"],
		# ["4009","4011","4012","5689","5690","5691"],
		# ["4008","4009","4011","4012",],
		["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
		"",
		l1_dir=l1_dir,
		)
	fit, anova = summary.roi_per_session(substitutions,
		t_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_tstat.nii.gz",
		legend_loc=2,
		# figure="per-voxel",
		figure="per-participant",
		roi_mask=roi_mask,
		roi_mask_normalize=roi_mask_normalize,
		color=color,
		)
	print(anova)
	plt.show()

def p_clusters(mask):
	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		["4011","4012","5689","5690","5691"],
		# ["4007","4008","4011","4012","5689","5690","5691"],
		["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
		"composite",
		l1_dir="dr",
		)
	timecourses, designs, stat_maps, events_dfs, subplot_titles = summary.p_filtered_ts(substitutions,
		ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		beta_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
		# p_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_pstat.nii.gz",
		p_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_pfstat.nii.gz",
		design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
		event_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
		brain_mask=mask,
		p_level=0.05,
		)
	timeseries.multi(timecourses, designs, stat_maps, events_dfs, subplot_titles, figure="timecourses")
	plt.show()

def roi(roi_path="~/ni_data/templates/roi/f_dr_chr.nii.gz"):
	substitutions = bids_substitution_iterator(["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],[4007,4008,4009,4011,4012],["EPI_CBV_jb_long"],"composite")
	timecourses, designs, stat_maps, subplot_titles = summary.roi_ts(substitutions, roi_path=roi_path,)
	timeseries.multi(timecourses, designs, stat_maps, subplot_titles, figure="timecourses")
	plt.show()

def roi_teaching(roi_path="~/ni_data/templates/roi/f_dr_chr.nii.gz"):
	design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat"
	substitutions = bids_substitution_iterator(["ofM_cF2"],[4008],["EPI_CBV_jb_long"],"composite")
	timeseries.roi_based(substitutions[0], design_file_template=design_file_template, flip=True, plot_design_regressors=[0])
	plt.show()

def check_responders():
	summary.responders("subjectwise_composite")

def qc_regressor_old(mask):
	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		["4011","4012","5689","5690","5691"],
		# ["4007","4008","4011","4012","5689","5690","5691"],
		["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
		"composite")
	timecourses, designs, stat_maps, events_dfs, subplot_titles = summary.ts_overviews(substitutions, mask,
		ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		beta_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
		design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
		event_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
		)
	timeseries.multi(timecourses, designs, stat_maps, events_dfs, subplot_titles, figure="timecourses")
	plt.show()

def qc_regressor(sessions, subjects, scans, workflow_name, mask):
	substitutions = bids_substitution_iterator(sessions,subjects,scans,workflow_name)
	timecourses, designs, stat_maps, events_dfs, subplot_titles = summary.ts_overviews(substitutions, mask,
		ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		beta_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
		design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
		event_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
		)
	timeseries.multi(timecourses, designs, stat_maps, events_dfs, subplot_titles, figure="timecourses")
	plt.show()

if __name__ == '__main__':
	# overview("as_composite_subjects", ["4005","4007","4008","4009","4011","4012","5687","5689","5690","5691","5703","5704","5706"],) #4001 is a negative control (transgene but no injection
	# overview("as_composite_subjects", ["4007","4008","4009","4011","4012","5689","5690","5691"],) #4001 is a negative control (transgene but no injection
	# overview("as_composite_sessions_responders", ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],cut_coords=[0,-4.3,-3.3])
	# overview("as_composite_sessions_best_responders", ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],cut_coords=[0,-4.3,-3.3])
	# overview("composite_subjects", ["4007","4008","4011","4012","5689","5690","5691"], template="~/ni_data/templates/ds_QBI_chr.nii.gz") #4001 is a negative control (transgene but no injection
	# overview("composite_subjects", ["4001","4005","4007","4008","4009","4011","4012"]) #4001 is a negative control (transgene but no injection
	# overview("subjectwise_blur", ["4001","4005","4007","4008","4009","4011","4012"])

	# roi_per_session("as_composite", "~/ni_data/templates/roi/DSURQEc_ctx.nii.gz", "#e66633")
	# roi_per_session("as_composite", "~/ni_data/templates/roi/ctx_chr_bin.nii.gz", "#56B4E9")
	# roi_per_session("as_composite", "~/ni_data/templates/roi/DSURQEc_ctx.nii.gz", "#56B4E9",
	# 	roi_mask_normalize="~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
	# 	)
	# roi_per_session("as_composite", "~/ni_data/templates/roi/DSURQEc_dr.nii.gz", "#E69F00")
	# roi_per_session("as_composite", "~/ni_data/templates/roi/f_dr_chr_bin.nii.gz", "#E69F00")
	# p_clusters("~/ni_data/templates/roi/f_dr_chr.nii.gz")
	# p_clusters("~/ni_data/templates/ds_QBI_chr_bin.nii.gz")
	# roi(roi_path="~/ni_data/templates/roi/f_dr_chr_bin.nii.gz")
	# roi_teaching()
	# check_responders()
	# qc_regressor_old("~/ni_data/templates/roi/f_dr_chr.nii.gz")
	# qc_regressor_old("~/ni_data/templates/roi/ctx_chr.nii.gz")
	# qc_regressor(["ofM_cF1"],["4011"],["EPI_CBV_jb_long"],"as_composite","~/ni_data/templates/roi/DSURQEc_ctx.nii.gz")
	# network.simple_dr(output="~/ntw1.png", graphsize=800, scale=1.8)
