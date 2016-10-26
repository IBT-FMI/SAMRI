import maps, timeseries, dcm

def responder_overview(workflow="subjectwise"):
	"""Test te per-animal signal across sessions. 4001 is a negative control (transgene but no injection)"""
	subjects = ["4001","4007","4008","4009","4012"]
	stat_maps = ["/home/chymera/NIdata/ofM.dr/l2/{0}/{1}/tstat1.nii.gz".format(workflow, i) for i in subjects]
	maps.stat(stat_maps, cbv=True, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=2.5, interpolation="gaussian", figure_title="Non/Responders", subplot_titles=subjects)

def session_overview(subset="all", cut_coords=None):
	"""Test te per-animal signal across sessions. 4001 is a negative control (transgene but no injection)"""
	sessions = ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]
	stat_maps = ["/home/chymera/NIdata/ofM.dr/l2/{0}/{1}/tstat1.nii.gz".format(subset,i) for i in sessions]
	maps.stat(stat_maps, cbv=True, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=2, interpolation="gaussian", figure_title="Sessions", subplot_titles=sessions, cut_coords=cut_coords)

def old_session_overview():
	"""Test te per-animal signal across sessions. 4001 is a negative control (transgene but no injection)"""
	sessions = ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]
	stat_maps = ["/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma/_category_multi_{}/flameo/mapflow/_flameo0/stats/tstat1.nii.gz".format(i) for i in sessions]
	maps.stat(stat_maps, cbv=True, template="~/NIdata/templates/ds_QBI_chr.nii.gz", threshold=2.5, interpolation="gaussian", figure_title="Non/Responders", subplot_titles=sessions)

def blur_kernel_compare_dr(conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], parameters=["level2_dgamma","level2_dgamma_blurxy4","level2_dgamma_blurxy5", "level2_dgamma_blurxy6", "level2_dgamma_blurxy7"], threshold=3):
	from matplotlib.backends.backend_pdf import PdfPages
	pp = PdfPages('/home/chymera/DR.pdf')
	for condition in conditions:
		stat_maps = ["~/NIdata/ofM.dr/GLM/"+parameter+"/_category_multi_"+condition+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		maps.stat(stat_maps, cbv=True, cut_coords=(-49,8,43), threshold=threshold, interpolation="none", template="~/NIdata/templates/hires_QBI_chr.nii.gz", save_as=pp, figure_title=condition, subplot_titles=parameters)
	pp.close()

if __name__ == '__main__':
	# old_session_overview()
	# blur_kernel_compare_dr()
	# session_overview("sessionwise_norealign")
	session_overview("sessionwise_norealign", cut_coords=(-50,12,46))
	# responder_overview("subjectwise")
	# session_overview("responders")
	# session_overview("all")
