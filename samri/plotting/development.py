import matplotlib.pyplot as plt
from os import path

from samri.analysis import fc
from samri.utilities import bids_substitution_iterator
from samri.fetch.local import roi_from_atlaslabel
from samri.plotting import maps, connectivity
from samri.report import aggregate

def overview(workflow, identifiers,
	cut_coords=[None, [0,-4.5,-3.3]],
	threshold=2.5,
	template="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	orientation="portrait",
	save_as="",
	):
	"""Plot the statistical maps per-factor from a 2nd level GLM workflow result directory."""
	plt.style.use('samri.conf')

	stat_maps_ = ["~/ni_data/ofM.dr/l2/{0}/{1}/tstat1.nii.gz".format(workflow, i) for i in identifiers]
	stat_maps_ = [i for i in stat_maps_ if path.isfile(i)]
	identifiers = [[i]*len(cut_coords) for i in identifiers]
	stat_maps = [[i]*len(cut_coords) for i in stat_maps_]
	stat_maps = [item for sublist in stat_maps for item in sublist]
	identifiers = [item for sublist in identifiers for item in sublist]
	cut_coords = cut_coords*len(stat_maps_)
	maps.stat(stat_maps,
		template=template,
		threshold=threshold,
		interpolation="none",
		figure_title=workflow,
		subplot_titles=identifiers,
		cut_coords=cut_coords,
		orientation=orientation,
		save_as=save_as,
		)

def blur_kernel_compare_dr(conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], parameters=["level2_dgamma","level2_dgamma_blurxy4","level2_dgamma_blurxy5", "level2_dgamma_blurxy6", "level2_dgamma_blurxy7"], threshold=3):
	from matplotlib.backends.backend_pdf import PdfPages
	pp = PdfPages('~/DR.pdf')
	for condition in conditions:
		stat_maps = ["~/ni_data/ofM.dr/GLM/"+parameter+"/_category_multi_"+condition+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		maps.stat(stat_maps, cut_coords=(-49,8,43), threshold=threshold, interpolation="none", template="~/ni_data/templates/hires_QBI_chr.nii.gz", save_as=pp, figure_title=condition, subplot_titles=parameters)
	pp.close()

def plot_roi_per_session(l1_dir, roi_mask, color,
	roi_mask_normalize="",
	):
	from samri.plotting import summary
	from samri.report import roi

	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		# ["5689","5690","5700"],
		["6262","6255","5694","5706",'5704'],
		# ["4007","4011","4012","5689","5690","5691"],
		# ["4009","4011","4012","5689","5690","5691"],
		# ["4008","4009","4011","4012",],
		["EPI_CBV_chr_longSOA"],
		"~/ni_data/ofM.dr/",
		"",
		l1_dir=l1_dir,
		)

	if isinstance(roi, list) and not "/" in roi[0]:
		roi = roi_from_atlaslabel("~/ni_data/templates/roi/DSURQEc_200micron_labels.nii",
			mapping="~/ni_data/templates/roi/DSURQE_mapping.csv",
			label_names=roi,
			)
	fit, anova, subjectdf, voxeldf = roi.per_session(substitutions,
		t_file_template="{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{trial}_tstat.nii.gz",
		roi_mask=roi_mask,
		roi_mask_normalize=roi_mask_normalize,
		)
	summary.plot_roi_per_session(subjectdf, voxeldf, legend_loc=2, figure="per-participant", color=color, save_as="~/test.png")

	print(anova)

def p_clusters(mask):
	from samri.plotting import summary, timeseries

	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		["4011","4012","5689","5690","5691"],
		# ["4007","4008","4011","4012","5689","5690","5691"],
		["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
		"~/ni_data/ofM.dr/",
		"composite",
		l1_dir="dr",
		)
	timecourses, designs, stat_maps, events_dfs, subplot_titles = summary.p_filtered_ts(substitutions,
		ts_file_template="{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		beta_file_template="{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
		# p_file_template="{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_pstat.nii.gz",
		p_file_template="{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_pfstat.nii.gz",
		design_file_template="{data_dir}/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
		event_file_template="{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
		brain_mask=mask,
		p_level=0.05,
		)
	timeseries.multi(timecourses, designs, stat_maps, events_dfs, subplot_titles, figure="timecourses")
	plt.show()

def roi_teaching(roi_path="~/ni_data/templates/roi/f_dr_chr.nii.gz"):
	from samri.plotting import timeseries

	design_file_template="~/ni_data/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat"
	substitutions = bids_substitution_iterator(
		["ofM_cF2"],
		[4008],
		["EPI_CBV_jb_long"],
		"~/ni_data/ofM.dr/"
		"composite",
		)
	timeseries.roi_based(substitutions[0], design_file_template=design_file_template, flip=True, plot_design_regressors=[0])
	plt.show()

def check_responders():
	from samri.plotting import summary

	summary.responders("composite_subjects")

def qc_regressor(sessions, subjects, scans, workflow_name, mask,
	data_dir="~/ni_data/ofM.dr",
	save_as="",
	):
	from samri.plotting import summary, timeseries
	plt.style.use('samri_multiple-ts.conf')

	substitutions = bids_substitution_iterator(sessions,subjects,scans,data_dir,workflow_name)
	timecourses, designs, stat_maps, events_dfs, subplot_titles = summary.ts_overviews(substitutions, mask,
		ts_file_template="{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		beta_file_template="{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
		design_file_template="{data_dir}/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
		event_file_template="{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
		)

	timeseries.multi(timecourses, designs, stat_maps, events_dfs, subplot_titles,
		figure="timecourses",
		quantitative=False,
		save_as=save_as,
		)

def single_ts_seed_connectivity(
	template="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	save_as="fcs.pdf"
	):
	connectivity_img2 = fc.seed_based_connectivity(
		"~/ni_data/ofM.dr/preprocessing/composite/sub-6255/ses-ofM/func/sub-6255_ses-ofM_trial-EPI_CBV_chr_longSOA.nii.gz",
		"~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
		save_as="~/fc.nii.gz"
	)
	stat_maps=[connectivity_img2,connectivity_img2]
	maps.stat(stat_maps,
		template=template,
		threshold=0.1,
		shape="landscape",
		cut_coords=[None,[0,-4.9,-3.3]],
		overlays=["~/ni_data/templates/roi/DSURQEc_dr.nii.gz",],
		save_as=save_as,
		scale=0.6,
		dim=0.8,
		)

def seed_connectivity_overview(
	template="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	cut_coords=[None,[0,-4.9,-3.3]],
	plot=False,
	):
	import numpy as np
	from labbookdb.report.tracking import treatment_group, append_external_identifiers
	from samri.plotting.overview import multiplot_matrix, multipage_plot

	db_path = '~/syncdata/meta.db'
	groups = treatment_group(db_path, ['cFluDW','cFluDW_'], 'cage')
	groups = append_external_identifiers(db_path, groups, ['Genotype_code'])
	all_subjects = groups['ETH/AIC'].unique()
	treatment = groups[
			(groups['Genotype_code']=="eptg")&
			(groups['Cage_TreatmentProtocol_code']=="cFluDW")
			]['ETH/AIC'].tolist()
	no_treatment = groups[
			(groups['Genotype_code']=="eptg")&
			(groups['Cage_TreatmentProtocol_code']=="cFluDW_")
			]['ETH/AIC'].tolist()
	negative_controls = groups[groups['Genotype_code']=="epwt"]['ETH/AIC'].tolist()
	print(treatment, no_treatment, negative_controls)
	substitutions = bids_substitution_iterator(
		["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],
		all_subjects,
		["EPI_CBV_chr_longSOA",],
		"~/ni_data/ofM.dr/",
		"composite",
		)
	fc_results = aggregate.seed_fc(substitutions, "~/ni_data/templates/roi/DSURQEc_dr_xs.nii.gz", "~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{trial}.nii.gz",
		)

	print([i['subject'] for i in fc_results])
	return
	if plot:
		multipage_plot(fc_results, treatment,
			figure_title="Chronic Fluoxetine (drinking water) Treatment Group",
			template=template,
			threshold=0.1,
			base_cut_coords=cut_coords,
			save_as="fc_treatment.pdf",
			overlays=['~/ni_data/templates/roi/DSURQEc_dr_xs.nii.gz'],
			scale=0.4,
			)
		multipage_plot(fc_results, no_treatment,
			figure_title="Chronic Fluoxetine (drinking water) Treatment Group",
			template=template,
			threshold=0.1,
			base_cut_coords=cut_coords,
			save_as="fc_no_treatment.pdf",
			overlays=['~/ni_data/templates/roi/DSURQEc_dr_xs.nii.gz'],
			scale=0.4,
			)
		multipage_plot(fc_results, negative_controls,
			figure_title="Chronic Fluoxetine (drinking water) Treatment Group",
			template=template,
			threshold=0.1,
			base_cut_coords=cut_coords,
			save_as="fc_negative_control.pdf",
			overlays=['~/ni_data/templates/roi/DSURQEc_dr_xs.nii.gz'],
			scale=0.4,
			)

def functional_connectivity(ts="~/ni_data/ofM.dr/preprocessing/as_composite/sub-5690/ses-ofM_aF/func/sub-5690_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz",
	labels_img='~/ni_data/templates/roi/DSURQEc_40micron_labels.nii',
	labels = '~/ni_data/templates/roi/DSURQE_mapping.csv',
	):
	"""
	simple fc example
	"""
	figsize = (50,50)
	# incl. plotting
	correlation_matrix = fc.correlation_matrix(ts, labels_img, save_as = '~/correlation_matrix.csv')
	#TODO: to test with confounds
	#correlation_matrix = fc.correlation_matrix(ts, '~/confounds.csv', labels_img, save_as = '~/correlation_matrix.csv')
	connectivity.plot_connectivity_matrix(correlation_matrix, figsize, labels, save_as = '~/correlation_matrix.png')



if __name__ == '__main__':
	# seed_connectivity_overview()
	# single_ts_seed_connectivity(save_as="~/sbfc.pdf")

	plot_roi_per_session("composite", "~/ni_data/templates/roi/DSURQEc_dr.nii.gz", "#E69F00")
	# p_clusters("~/ni_data/templates/ds_QBI_chr_bin.nii.gz")
	# roi_teaching()
	# check_responders()
	#qc_regressor(
	#	["ofM","ofM_aF","ofM_cF1","ofM_cF2"],
	#	["5687","5689","5690",],
	#	["EPI_CBV_jb_long","EPI_CBV_chr_longSOA"],
	#	"as_composite",
	#	"~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
	#	save_as="qc_regressor.pdf",
	#	)
	# qc_regressor(["ofM_cF1"],["4011"],["EPI_CBV_jb_long"],"as_composite","~/ni_data/templates/roi/DSURQEc_ctx.nii.gz")
	plt.show()
