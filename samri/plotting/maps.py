import nibabel as nib
import nilearn
import numpy as np
import pandas as pd
from os import path

#Here we import internal nilearn functions, YOLO!
from nilearn._utils.niimg import _safe_get_data
from nilearn.plotting.img_plotting import _get_colorbar_and_data_ranges

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.colorbar import ColorbarBase, make_axes

from samri.fetch.local import roi_from_atlaslabel
from samri.plotting.utilities import QUALITATIVE_COLORSET

COLORS_PLUS = plt.cm.autumn(np.linspace(0., 1, 128))
COLORS_MINUS = plt.cm.winter(np.linspace(0, 1, 128))
COLORS = np.vstack((COLORS_MINUS, COLORS_PLUS[::-1]))
MYMAP = mcolors.LinearSegmentedColormap.from_list('my_colormap', COLORS)

def _draw_colorbar(stat_map_img, axes,
	threshold=.1,
	nb_ticks=5,
	edge_color="0.5",
	edge_alpha=1,
	aspect=40,
	fraction=0.025,
	anchor=(10.0,0.5),
	):
	if isinstance(stat_map_img, str):
		stat_map_img = path.abspath(path.expanduser(stat_map_img))
		stat_map_img = nib.load(stat_map_img)
	_,_,vmin, vmax, = _get_colorbar_and_data_ranges(_safe_get_data(stat_map_img, ensure_finite=True),None,"auto","")
	cbar_ax, p_ax = make_axes(axes,
		aspect=aspect,
		fraction=fraction,
		# pad=-0.5,
		anchor=anchor,
		# panchor=(-110.0, 0.5),
		)
	ticks = np.linspace(vmin, vmax, nb_ticks)
	bounds = np.linspace(vmin, vmax, MYMAP.N)
	norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
	# some colormap hacking
	cmaplist = [MYMAP(i) for i in range(MYMAP.N)]
	istart = int(norm(-threshold, clip=True) * (MYMAP.N - 1))
	istop = int(norm(threshold, clip=True) * (MYMAP.N - 1))
	for i in range(istart, istop):
		cmaplist[i] = (0.5, 0.5, 0.5, 1.)  # just an average gray color
	our_cmap = MYMAP.from_list('Custom cmap', cmaplist, MYMAP.N)

	cbar = ColorbarBase(
		cbar_ax,
		ticks=ticks,
		norm=norm,
		orientation="vertical",
		cmap=our_cmap,
		boundaries=bounds,
		spacing="proportional",
		format="%.2g",
		)

	cbar.outline.set_edgecolor(edge_color)
	cbar.outline.set_alpha(edge_alpha)

	cbar_ax.yaxis.tick_left()
	tick_color = 'k'
	for tick in cbar_ax.yaxis.get_ticklabels():
		tick.set_color(tick_color)
	cbar_ax.yaxis.set_tick_params(width=0)

	return cbar_ax, p_ax

def scaled_plot(stat_map, template, fig, ax,
		overlay=None,
		title=None,
		threshold=None,
		cut=None,
		draw_cross=True,
		annotate=True,
		interpolation="none",
		dim=1,
		scale=1.,
		):
	"""A wrapper for nilearn's plot_stat_map which allows scaling of crosshairs, titles and annotations.

	Parameters
	----------

	stat_map : string or array_like
	A path to a NIfTI file, or a nibabel object (e.g. Nifti1Image), giving the statistic image to plot.

	template : string or array_like
	A path to a NIfTI file, or a nibabel object (e.g. Nifti1Image), to use as a backdrop when plotting the statistic image.

	fig : matplotlib figure object
	Figure to draw to.

	ax : matplotlib axis object
	Axis to draw to.

	overlay: string or array_like
	A path to a NIfTI file, or a nibabel object (e.g. Nifti1Image), giving an image fr which to draw the contours on top of the statistic plot.

	"""
	# Make sure that if the variables are paths, they are absolute
	try:
		stat_map = path.abspath(path.expanduser(stat_map))
	except AttributeError:
		pass
	try:
		template = path.abspath(path.expanduser(template))
	except AttributeError:
		pass
	try:
		overlay = path.abspath(path.expanduser(overlay))
	except AttributeError:
		pass
	display = nilearn.plotting.plot_stat_map(stat_map,
		bg_img=template,
		threshold=threshold,
		figure=fig,
		axes=ax,
		cmap=MYMAP,
		cut_coords=cut,
		interpolation=interpolation,
		dim=dim,
		title=title,
		annotate=False,
		draw_cross=False,
		black_bg=False,
		colorbar=False,
		)
	if draw_cross:
		display.draw_cross(linewidth=scale*1.6, alpha=0.3)
	if annotate:
		display.annotate(size=2+scale*18)
	if title:
		display.title(title, size=2+scale*26)
	if overlay:
		try:
			display.add_contours(overlay, threshold=.5)
		except ValueError:
			pass

	return display

def stat(stat_maps,
	overlays=[],
	figure_title="",
	interpolation="hermite",
	template="~/ni_data/templates/ds_QBI_chr.nii.gz",
	save_as="",
	scale=1.,
	subplot_titles=[],
	cut_coords=[None],
	threshold=3,
	black_bg=False,
	annotate=True,
	draw_cross=True,
	show_plot=True,
	dim=0,
	vmax=None,
	orientation="portrait",
	):

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

	vmax : int or None, optional
	Allows explicit specificaion of the maximum range of the color bar (the color bar will span +vmax to -vmax).

	subplot_titles : list, optional
	List of titles for sub plots. Must be empty list or strings list of the same length as the stats_maps list.

	Notes
	-----

	Identical consequitive statistical maps are auto-detected and share a colorbar.
	To avoid starting a shared colorbar at the end of a column, please ensure that the length of statistical maps to be plotted is divisible both by the group size and the number of columns.
	"""

	if len(stat_maps) == 1:
		fig, axes = plt.subplots(figsize=(14,5), facecolor='#eeeeee')

		if figure_title:
			fig.suptitle(figure_title, fontsize=scale*20, fontweight='bold')

		if subplot_titles:
			title = subplot_titles[0]
		else:
			title=None

		cax, kw = _draw_colorbar(stat_maps[0],axes,
			aspect=30,
			fraction=0.05,
			anchor=(1.,0.5),
			)
		display = scaled_plot(stat_maps[0], template, fig, axes,
			overlay= overlays[0],
			title=title,
			threshold=threshold,
			cut=cut_coords[0],
			interpolation=interpolation,
			dim=dim,
			draw_cross=draw_cross,
			annotate=annotate,
			scale=scale,
			)
	else:
		if len(overlays) == 1:
			overlays = overlays*len(stat_maps)
		elif len(overlays) == 0:
			overlays = [None]*len(stat_maps)
		if len(cut_coords) == 1:
			cut_coords = cut_coords*len(stat_maps)
		elif len(cut_coords) == 0:
			cut_coords = [None]*len(stat_maps)
		if orientation == "portrait":
			ncols = 2
			#we use inverse floor division to get the ceiling
			nrows = -(-len(stat_maps)//2)
			scale = scale/float(ncols)
		if orientation == "landscape":
			nrows = 2
			#we use inverse floor division to get the ceiling
			ncols = -(-len(stat_maps)//2)
			scale = scale/float(nrows)
		fig, axes = plt.subplots(figsize=(6*ncols,2.5*nrows), facecolor='#eeeeee', nrows=nrows, ncols=ncols)
		if figure_title:
			fig.suptitle(figure_title, fontsize=scale*30, fontweight='bold')
		conserve_colorbar_steps = 0
		# We transform the axes array so that we iterate column-first rather than row-first.
		# This is done to better share colorbars between consecutive axes.
		flat_axes = list(axes.T.flatten())
		cbar_aspect = 30
		if nrows >=2:
			fraction = 0.09
		elif ncols >=2:
			fraction = 0.025
		else:
			fraction = 0.04
		for ix, ax in enumerate(flat_axes):
			#create or use conserved colorbar for multiple cnsecutive plots of the same image
			if conserve_colorbar_steps == 0:
				while True and conserve_colorbar_steps < len(stat_maps)-ix:
					if stat_maps[ix+conserve_colorbar_steps] == stat_maps[ix]:
						conserve_colorbar_steps+=1
					else:
						break
				cax, kw = _draw_colorbar(stat_maps[ix],flat_axes[ix:ix+conserve_colorbar_steps],
					aspect=cbar_aspect,
					fraction=fraction,
					anchor=(2,0.5),
					)
			conserve_colorbar_steps-=1

			if subplot_titles:
				try:
					title = subplot_titles[ix]
				except IndexError:
					title = None
			else:
				title = None
			#enough axes are created to fully populate a grid. This may be more than the available number of subplots.
			try:
				display = scaled_plot(stat_maps[ix], template, fig, ax,
					overlay = overlays[ix],
					title=title,
					threshold=threshold,
					cut=cut_coords[ix],
					interpolation=interpolation,
					dim=dim,
					draw_cross=draw_cross,
					annotate=annotate,
					scale=scale,
					)
			except IndexError:
				ax.axis('off')

	if save_as:
		if isinstance(save_as, str):
			plt.savefig(path.abspath(path.expanduser(save_as)), dpi=400, bbox_inches='tight')
		else:
			from matplotlib.backends.backend_pdf import PdfPages
			if isinstance(save_as, PdfPages):
				save_as.savefig()
	else:
		if show_plot:
			plt.show()

	return display

def atlas_label(atlas,
	mapping="",
	label_names=[],
	anat="~/ni_data/templates/DSURQEc_40micron_masked.nii.gz",
	annotate=True,
	black_bg=False,
	draw_cross=True,
	threshold=None,
	roi=False,
	subplot_titles=[],
	color="#E69F00",
	scale=1.,
	dim=0,
	**kwargs
	):
	"""Plot a region of interest based on an atlas and a label."""

	from matplotlib.colors import LinearSegmentedColormap, ListedColormap

	anat = path.abspath(path.expanduser(anat))

	if mapping and label_names:
		roi = roi_from_atlaslabel(atlas, mapping=mapping, label_names=label_names, **kwargs)
	elif isinstance(atlas, str):
		atlas = path.abspath(path.expanduser(atlas))
		roi = nib.load(atlas)
	else:
		roi = atlas

	cm = ListedColormap([color], name="my_atlas_label_cmap", N=None)

	display = nilearn.plotting.plot_roi(roi, bg_img=anat, black_bg=black_bg, annotate=False, draw_cross=False, cmap=cm, dim=dim)
	if draw_cross:
		display.draw_cross(linewidth=scale*1.6, alpha=0.4)
	if annotate:
		display.annotate(size=2+scale*18)
	if subplot_titles:
		display.title(title, size=2+scale*26)


def plot_myanat(anat="~/ni_data/templates/hires_QBI_chr.nii.gz"):
	nilearn.plotting.plot_anat(anat, cut_coords=[0, 0, 0],title='Anatomy image')

def plot_nii(file_path, slices):
	nilearn.plotting.plot_anat(file_path, cut_coords=slices, display_mode="y", annotate=False, draw_cross=False)

def from_multi_contrast(session_participant_file, template="~/ni_data/templates/ds_QBI_chr.nii.gz", threshold="2"):
	img = nib.load(session_participant_file)
	print(img.__dict__)
	nilearn.plotting.plot_stat_map(img, bg_img=template,threshold=threshold, black_bg=False, vmax=40)
