import matplotlib.pyplot as plt

import maps, timeseries, summary

def overview(workflow, identifiers,
	cut_coords=[None],
	threshold=2,
	):
	"""Plot the statistical maps per-factor from a 2nd level GLM workflow result directory."""
	stat_maps = ["/home/chymera/NIdata/ofM.dr/l2/{0}/{1}/tstat1.nii.gz".format(workflow, i) for i in identifiers]
	if isinstance(cut_coords[0], int):
		cut_coords = [cut_coords]
	maps.stat(stat_maps, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=threshold, interpolation="gaussian", figure_title="Non/Responders", subplot_titles=identifiers, cut_coords=cut_coords)

def blur_kernel_compare_dr(conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], parameters=["level2_dgamma","level2_dgamma_blurxy4","level2_dgamma_blurxy5", "level2_dgamma_blurxy6", "level2_dgamma_blurxy7"], threshold=3):
	from matplotlib.backends.backend_pdf import PdfPages
	pp = PdfPages('/home/chymera/DR.pdf')
	for condition in conditions:
		stat_maps = ["~/NIdata/ofM.dr/GLM/"+parameter+"/_category_multi_"+condition+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		maps.stat(stat_maps, cut_coords=(-49,8,43), threshold=threshold, interpolation="none", template="~/NIdata/templates/hires_QBI_chr.nii.gz", save_as=pp, figure_title=condition, subplot_titles=parameters)
	pp.close()

def roi_per_session(l1_dir, roi, color):
	fit, anova = summary.roi_per_session(l1_dir, [4007,4008,4009,4011,4012], ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], legend_loc=2, figure="per-participant",roi=roi, color=color)
	plt.show()

def p_clusters():
	substitutions = summary.bids_substitution_iterator(["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],[4007,4008,4009,4011,4012],["7_EPI_CBV"],"composite", l1_dir="composite_dr", l1_workdir="composite_work")
	timecourses, designs, stat_maps, subplot_titles = summary.p_filtered_ts(substitutions, p_level=0.05)
	timeseries.multi(timecourses, designs, stat_maps, subplot_titles, figure="timecourses")
	plt.show()

def roi(roi_path="~/NIdata/templates/roi/f_dr_chr.nii.gz"):
	substitutions = summary.bids_substitution_iterator(["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"],[4007,4008,4009,4011,4012],["7_EPI_CBV"],"composite")
	timecourses, designs, stat_maps, subplot_titles = summary.roi_ts(substitutions, roi_path=roi_path,)
	timeseries.multi(timecourses, designs, stat_maps, subplot_titles, figure="timecourses")
	plt.show()

def roi_teaching(roi_path="~/NIdata/templates/roi/f_dr_chr.nii.gz"):
	design_file_template="~/NIdata/ofM.dr/l1/{l1_workdir}/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat"
	substitutions = summary.bids_substitution_iterator(["ofM_cF2"],[4008],["7_EPI_CBV"],"composite")
	timeseries.roi_based(substitutions[0], design_file_template=design_file_template, flip=True, plot_design_regressors=[0])
	plt.show()

def check_responders():
	summary.responders("subjectwise_composite")

if __name__ == '__main__':
	# responder_overview("composite_sessions", ["4001","4005","4007","4008","4009","4011","4012","5689","5690","5691","5703","5704","5706"])
	overview("composite_sessions", ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"])
	# overview("composite_subjects", ["4001","4005","4007","4008","4009","4011","4012"]) #4001 is a negative control (transgene but no injection
	# overview("subjectwise_blur", ["4001","4005","4007","4008","4009","4011","4012"])

	# network.simple_dr(output="~/ntw1.png", graphsize=800)
	# roi_per_session("composite", "ctx", "#56B4E9")
	# roi_per_session("composite", "f_dr", "#E69F00")
	# p_clusters()
	# roi(roi_path="~/NIdata/templates/roi/ctx_chr.nii.gz")
	# roi_teaching()
	# check_responders()
