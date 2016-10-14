import maps, timeseries, dcm

def blur_kernel_compare_dr(conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], parameters=["level2_dgamma","level2_dgamma_blurxy4","level2_dgamma_blurxy5", "level2_dgamma_blurxy6", "level2_dgamma_blurxy7"], threshold=3):
	from matplotlib.backends.backend_pdf import PdfPages
	pp = PdfPages('/home/chymera/DR.pdf')
	for condition in conditions:
		stat_maps = ["~/NIdata/ofM.dr/GLM/"+parameter+"/_category_multi_"+condition+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		maps.stat(stat_maps, cbv=True, cut_coords=(-49,8,43), threshold=threshold, interpolation="none", template="~/NIdata/templates/hires_QBI_chr.nii.gz", save_as=pp, figure_title=condition, subplot_titles=parameters)
	pp.close()

def blur_kernel_compare_erc(scan_types=["jin6","jin10","jin20","jin40","jin60","alej"], parameters=["dgamma","dgamma_blurxy4","dgamma_blurxy5", "dgamma_blurxy6", "dgamma_blurxy7"], threshold=3):
	for scan_type in scan_types:
		stat_maps = ["~/NIdata/ofM.erc/GLM/level2_"+parameter+"/_scan_type_multi_EPI_CBV_"+scan_type+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [parameter for parameter in parameters]
		maps.stat(stat_maps, cbv=True, threshold=threshold, interpolation="none", template="~/NIdata/templates/hires_QBI_chr.nii.gz", save_as="~/"+scan_type+".pdf", figure_title=scan_type, subplot_titles=parameters)

if __name__ == '__main__':
	blur_kernel_compare_dr()
