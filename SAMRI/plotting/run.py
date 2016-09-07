import maps, timeseries

def blur_kernel_compare(conditions=["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"], parameters=["level2_dgamma","level2_dgamma_blurxy4","level2_dgamma_blurxy5", "level2_dgamma_blurxy6", "level2_dgamma_blurxy7"], threshold=3):
	for condition in conditions:
		stat_maps = ["~/NIdata/ofM.dr/GLM/"+parameter+"/_category_multi_"+condition+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz" for parameter in parameters]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		maps.stat(stat_maps, cbv=True, cut_coords=(-49,8,43), threshold=threshold, interpolation="gaussian", save_as="~/"+condition+".pdf", figure_title=condition, subplot_titles=parameters)

if __name__ == '__main__':
	blur_kernel_compare()
