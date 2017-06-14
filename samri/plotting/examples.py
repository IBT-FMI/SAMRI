import matplotlib.pyplot as plt

from samri.pipelines import fc
from samri.utilities import bids_substitution_iterator
from samri.fetch.local import roi_from_atlaslabel
from samri.plotting import maps, timeseries, summary, network
from samri.report import aggregate


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

def roi_per_session(l1_dir, roi, color,
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
	if isinstance(roi, list) and not "/" in roi[0]:
		roi = roi_from_atlaslabel("~/ni_data/templates/roi/DSURQEc_200micron_labels.nii",
			mapping="~/ni_data/templates/roi/DSURQE_mapping.csv",
			label_names=roi,
			)
	fit, anova = summary.roi_per_session(substitutions,
		t_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_tstat.nii.gz",
		legend_loc=2,
		# figure="per-voxel",
		figure="per-participant",
		roi_mask=roi,
		roi_mask_normalize=roi_mask_normalize,
		color=color,
		)
	print(anova)

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

def plot_my_roi():
	maps.atlas_label("~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
		)
	plt.show()

def plot_roi_by_label(label_names,
	save_as="",
	):
	roi = roi_from_atlaslabel("~/ni_data/templates/roi/DSURQEc_200micron_labels.nii",
		mapping="~/ni_data/templates/roi/DSURQE_mapping.csv",
		label_names=label_names,
		save_as=save_as
		)
	maps.atlas_label(roi)
	plt.show()
	# roi_per_session("as_composite", roi, "#e66633")

def single_ts_seed_connectivity(
	template="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	):
	connectivity_img = fc.seed_based_connectivity(
		"~/ni_data/ofM.dr/preprocessing/as_composite/sub-5689/ses-ofM/func/sub-5689_ses-ofM_trial-EPI_CBV_chr_longSOA.nii.gz",
		# "~/ni_data/ofM.dr/preprocessing/as_composite/sub-5706/ses-ofM_aF/func/sub-5706_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz",
		# "~/ni_data/ofM.dr/preprocessing/as_composite/sub-5690/ses-ofM/func/sub-5690_ses-ofM_trial-EPI_CBV_chr_longSOA.nii.gz",
		# "~/ni_data/ofM.dr/preprocessing/as_composite/sub-4011/ses-ofM_aF/func/sub-4011_ses-ofM_aF_trial-EPI_CBV_jb_long.nii.gz",
		"~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
	)
	stat_maps=[connectivity_img,connectivity_img]
	maps.stat(stat_maps,
		template=template,
		threshold=0.1,
		orientation="portrait",
		cut_coords=[None,[0,-4.5,-3.3]],
		overlays=["~/ni_data/templates/roi/DSURQEc_dr.nii.gz",],
		)

def seed_connectivity_overview(
	template="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	):
	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		# ["5689","5690","5691"],
		["4005","5687","4007","4011","4012","5689","5690","5691"],
		# ["4007","4011","4012","5689","5690","5691"],
		# ["4009","4011","4012","5689","5690","5691"],
		# ["4008","4009","4011","4012",],
		["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
		"as_composite",
		l1_dir=l1_dir,
		)
	subjectdf, voxeldf = aggregate.fc_rois(substitutions,
		ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		roi="~/ni_data/templates/roi/DSURQEc_ctx.nii.gz",
		seed="~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
		)

	# connectivity_img = fc.seed_based_connectivity(
	# 	"~/ni_data/ofM.dr/preprocessing/as_composite/sub-5706/ses-ofM_aF/func/sub-5706_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz",
	# 	# "~/ni_data/ofM.dr/preprocessing/as_composite/sub-5690/ses-ofM_aF/func/sub-5690_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz",
	# 	# "~/ni_data/ofM.dr/preprocessing/as_composite/sub-4011/ses-ofM_aF/func/sub-4011_ses-ofM_aF_trial-EPI_CBV_jb_long.nii.gz",
	# 	"~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
	# )
	# stat_maps=[connectivity_img,connectivity_img]
	# maps.stat(stat_maps,
	# 	template=template,
	# 	threshold=0.1,
	# 	orientation="portrait",
	# 	cut_coords=[None,[0,-4.5,-3.3]],
	# 	overlays=["~/ni_data/templates/roi/DSURQEc_dr.nii.gz",],
	# 	)


if __name__ == '__main__':
	# overview("as_composite_subjects", ["4005","4007","4008","4009","4011","4012","5687","5689","5690","5691","5703","5704","5706"],) #4001 is a negative control (transgene but no injection
	# overview("as_composite_subjects", ["4007","4008","4009","4011","4012","5689","5690","5691"],) #4001 is a negative control (transgene but no injection
	# overview("as_composite_sessions_responders", ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],cut_coords=[0,-4.3,-3.3])
	# overview("as_composite_sessions_best_responders", ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],cut_coords=[0,-4.3,-3.3])
	# overview("composite_subjects", ["4007","4008","4011","4012","5689","5690","5691"], template="~/ni_data/templates/ds_QBI_chr.nii.gz") #4001 is a negative control (transgene but no injection
	# overview("composite_subjects", ["4001","4005","4007","4008","4009","4011","4012"]) #4001 is a negative control (transgene but no injection
	# overview("subjectwise_blur", ["4001","4005","4007","4008","4009","4011","4012"])

	seed_connectivity_overview()
	# single_ts_seed_connectivity()

	# plot_roi_by_label(["medulla","midbrain","pons"],"chr_brainstem")
	# plot_my_roi()

	# roi_per_session("composite", "~/ni_data/templates/roi/ctx_chr_bin.nii.gz", "#56B4E9")
	# roi_per_session("as_composite", ["cortex"], "#e66633")
	# roi_per_session("as_composite", ["frontal","Frontal","orbital","Orbital"], "#e66633")
	# roi_per_session("as_composite", "~/ni_data/templates/roi/DSURQEc_ctx.nii.gz", "#56B4E9",
	# 	roi_mask_normalize="~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
	# 	)
	# roi_per_session("as_composite", "~/ni_data/templates/roi/DSURQEc_dr.nii.gz", "#E69F00")
	# roi_per_session("as_composite", "~/ni_data/templates/roi/f_dr_chr_bin.nii.gz", "#E69F00")
	# p_clusters("~/ni_data/templates/ds_QBI_chr_bin.nii.gz")
	# roi(roi_path="~/ni_data/templates/roi/f_dr_chr_bin.nii.gz")
	# roi_teaching()
	# check_responders()
	# qc_regressor_old("~/ni_data/templates/roi/f_dr_chr.nii.gz")
	# qc_regressor_old("~/ni_data/templates/roi/ctx_chr.nii.gz")
	# qc_regressor(
	# 	["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
	# 	["4005","5687","4007","4011","4012","5689","5690","5691"],
	# 	["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
	# 	"as_composite",
	# 	"~/ni_data/templates/roi/DSURQEc_ctx.nii.gz",
	# 	)
	# qc_regressor(["ofM_cF1"],["4011"],["EPI_CBV_jb_long"],"as_composite","~/ni_data/templates/roi/DSURQEc_ctx.nii.gz")
	# network.simple_dr(output="~/ntw1.png", graphsize=800, scale=1.8)

	# substitutions = bids_substitution_iterator(
	# 	["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
	# 	["4005","5687","4007","4011","4012","5689","5690","5691"],
	# 	["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
	# 	"",
	# 	l1_dir="as_composite",
	# 	)
	#
	#
	# fit, anova = summary.analytic_pattern_per_session(substitutions, '~/ni_data/ofM.dr/l2/as_composite_sessions_responders/ofM/tstat1.nii.gz',
	# 	t_file_template="~/ni_data/ofM.dr/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_tstat.nii.gz",
	# 	legend_loc=2,
	# 	figure="per-participant",
	# 	color="#e66633",
	# 	xy_label=["Session","t-statistic"],
	# 	)
	# print(anova)
	plt.show()
