import os
import nibabel
import pandas as pd
import numpy as np
import nipype.interfaces.io as nio
from nilearn import image, plotting
from nilearn.input_data import NiftiLabelsMasker

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
plt.style.use('ggplot')

colors_plus = plt.cm.autumn(np.linspace(0., 1, 128))
colors_minus = plt.cm.winter(np.linspace(0, 1, 128))

def stat(stat_maps, figure_title="", interpolation="hermite", template="~/NIdata/templates/ds_QBI_chr.nii.gz", save_as="", scale=1., subplot_titles=[], cut_coords=None, threshold=3, black_bg=False, annotate=True, draw_cross=True, show_plot=True):
	"""Plot a list of statistical maps.
	This Function acts as a wrapper of nilearn.plotting.plot_stat_map, adding support for multiple axes, using a prettier default and allowing intelligent text and crosshair scaling.

	Parameters
	----------

	stat_maps : list
	A list of strings giving the paths to the statistical maps to be plotted.

	figure_title : string, optional
	Title for the entire figure.

	interpolation : string, optional
	Interpolation to use for plot. Possible values according to matplotlib http://matplotlib.org/examples/images_contours_and_fields/interpolation_methods.html .

	template : string, optional
	Path to template onto which to plot the statistical maps.

	save_as : string, optional
	Path under which to save the figure. If None or equivalent, the plot will be shown (via `plt.show()`).

	scale : float, optional
	Allows intelligent scaling of annotation, crosshairs, and title.

	subplot_titles : list, optional
	List of titles for sub plots. Must be empty list or strings list of the same length as the stats_maps list.
	"""

	#make sure paths are absolute
	stat_maps = [os.path.abspath(os.path.expanduser(stat_map)) for stat_map in stat_maps]
	template = os.path.abspath(os.path.expanduser(template))

	colors = np.vstack((colors_minus, colors_plus[::-1]))
	mymap = mcolors.LinearSegmentedColormap.from_list('my_colormap', colors)

	if len(stat_maps) == 1:
		fig, axes = plt.subplots(figsize=(14,5), facecolor='#eeeeee')
		if figure_title:
			fig.suptitle(figure_title, fontsize=scale*20, fontweight='bold')
		if subplot_titles:
			title = subplot_titles[0]
		display = plotting.plot_stat_map(stat_maps[0], bg_img=template,threshold=threshold, figure=fig, axes=axes, black_bg=black_bg, vmax=40, cmap=mymap, cut_coords=cut_coords, annotate=False, title=None, draw_cross=False, interpolation=interpolation)
		if draw_cross:
			display.draw_cross(linewidth=scale*1.6, alpha=0.4)
		if annotate:
			display.annotate(size=2+scale*18)
		if subplot_titles:
			display.title(title, size=2+scale*26)
	else:
		ncols = 2
		#we use inverse floor division to get the ceiling
		nrows = -(-len(stat_maps)//2)
		scale = scale/float(ncols)
		fig, axes = plt.subplots(figsize=(8*nrows,7*ncols), facecolor='#eeeeee', nrows=nrows, ncols=ncols)
		if figure_title:
			fig.suptitle(figure_title, fontsize=scale*30, fontweight='bold')
		for ix, ax in enumerate(axes.flat):
			try:
				if subplot_titles:
					title = subplot_titles[ix]
				display = plotting.plot_stat_map(stat_maps[ix], bg_img=template,threshold=threshold, figure=fig, axes=ax, black_bg=black_bg, vmax=40, cmap=mymap, cut_coords=cut_coords, annotate=False, title=None, draw_cross=False, interpolation=interpolation)
				if draw_cross:
					display.draw_cross(linewidth=scale*1.6, alpha=0.4)
				if annotate:
					display.annotate(size=2+scale*18)
				if subplot_titles:
					display.title(title, size=2+scale*26)
			except IndexError:
				ax.axis('off')

	if save_as:
		if isinstance(save_as, str):
			plt.savefig(os.path.abspath(os.path.expanduser(save_as)), dpi=400, bbox_inches='tight')
		else:
			from matplotlib.backends.backend_pdf import PdfPages
			if isinstance(save_as, PdfPages):
				save_as.savefig()
	else:
		if show_plot:
			plt.show()

	return display

def plot_myanat(anat="/home/chymera/NIdata/templates/hires_QBI_chr.nii.gz"):
	plotting.plot_anat(anat, cut_coords=[0, 0, 0],title='Anatomy image')

def plot_nii(file_path, slices):
	plotting.plot_anat(file_path, cut_coords=slices, display_mode="y", annotate=False, draw_cross=False)
