import os
import nibabel
from nilearn import image, plotting
import pandas as pd
import numpy as np
from nilearn.input_data import NiftiLabelsMasker
import nipype.interfaces.io as nio

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
plt.style.use('ggplot')

colors_plus = plt.cm.autumn(np.linspace(0., 1, 128))
colors_minus = plt.cm.winter(np.linspace(0, 1, 128))

def plot_stat_map(stat_maps ,template="/home/chymera/NIdata/templates/hires_QBI_chr.nii.gz", cbv=True, cut_coords=None, black_bg=False, annotate=True, titles=[], threshold=2.5, scale=1, draw_cross=True, save_as="", interpolation="hermite"):
	"""Wrapper for the nilearn.plotting.plot_stat_map, provides better control over element scaling and uses a prettier default style

	Keyword Arguments:
	scale -- allows intelligent scaling of annotation, crosshairs, and title
	"""

	if cbv:
		colors = np.vstack((colors_plus, colors_minus[::-1]))
	else:
		colors = np.vstack((colors_minus, colors_plus[::-1]))
	mymap = mcolors.LinearSegmentedColormap.from_list('my_colormap', colors)

	if len(stat_maps) == 1:
		fig, axes = plt.subplots(figsize=(14,5), facecolor='#eeeeee')
		title = titles[0]
		display = plotting.plot_stat_map(stat_maps[0], bg_img=template,threshold=threshold, figure=fig, axes=axes, black_bg=black_bg, vmax=40, cmap=mymap, cut_coords=cut_coords, annotate=False, title=None, draw_cross=False, interpolation=interpolation)
		if draw_cross:
			display.draw_cross(linewidth=scale*1.6, alpha=0.4)
		if annotate:
			display.annotate(size=2+scale*18)
		if title:
			display.title(title, size=2+scale*26)
	else:
		ncols = 2
		#we use inverse floor division to get the ceiling
		nrows = -(-len(stat_maps)//2)
		scale = scale/float(ncols)
		fig, axes = plt.subplots(figsize=(8*nrows,7*ncols), facecolor='#eeeeee', nrows=nrows, ncols=ncols)
		for ix, ax in enumerate(axes.flat):
			try:
				title = titles[ix]
				display = plotting.plot_stat_map(stat_maps[ix], bg_img=template,threshold=threshold, figure=fig, axes=ax, black_bg=black_bg, vmax=40, cmap=mymap, cut_coords=cut_coords, annotate=False, title=None, draw_cross=False, interpolation=interpolation)
				if draw_cross:
					display.draw_cross(linewidth=scale*1.6, alpha=0.4)
				if annotate:
					display.annotate(size=2+scale*18)
				if title:
					display.title(title, size=2+scale*26)
			except IndexError:
				ax.axis('off')

	if save_as:
		plt.savefig(os.path.abspath(os.path.expanduser(save_as)), dpi=400, bbox_inches='tight')
	else:
		plt.show()

	return display

def plot_myanat(anat="/home/chymera/NIdata/templates/hires_QBI_chr.nii.gz"):
	plotting.plot_anat(anat, cut_coords=[0, 0, 0],title='Anatomy image')

def plot_nii(file_path, slices):
	plotting.plot_anat(file_path, cut_coords=slices, display_mode="y", annotate=False, draw_cross=False)

if __name__ == '__main__':
	# stat_maps = [
	# 	"/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy4/_category_multi_ofM_cF2/flameo/mapflow/_flameo0/stats/tstat1.nii.gz",
	# 	]
	for i in ["","_aF","_cF1","_cF2","_pF"]:
		stat_maps = [
			"/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma/_category_multi_ofM"+i+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz",
			"/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy4/_category_multi_ofM"+i+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz",
			"/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy5/_category_multi_ofM"+i+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz",
			"/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy6/_category_multi_ofM"+i+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz",
			"/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy7/_category_multi_ofM"+i+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz",
			]
		titles = [stat_map[32:-43] for stat_map in stat_maps]
		plot_stat_map(stat_maps, cbv=True, cut_coords=(-49,8,43), threshold=2.5, interpolation="gaussian", save_as="~/ofM"+i+".pdf", titles=titles)
