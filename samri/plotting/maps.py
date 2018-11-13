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
from matplotlib import rcParams
from matplotlib.colorbar import ColorbarBase, make_axes
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from samri.fetch.local import roi_from_atlaslabel
from samri.plotting.utilities import QUALITATIVE_COLORSET
from samri.utilities import collapse

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

def scaled_plot(template,
	fig=None,
	ax=None,
	black_bg=False,
	stat_map=None,
	overlay=None,
	title=None,
	threshold=None,
	cut=None,
	draw_cross=True,
	annotate=True,
	interpolation="none",
	dim=1,
	scale=1.,
	cmap=MYMAP,
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
	A path to a NIfTI file, or a nibabel object (e.g. Nifti1Image), giving an image for which to draw the contours on top of the statistic plot.

	"""
	# Make sure that if the variables are paths, they are absolute
	try:
		template = path.abspath(path.expanduser(template))
	except AttributeError:
		pass
	if not stat_map:
		display = nilearn.plotting.plot_img(template,
			threshold=threshold,
			figure=fig,
			axes=ax,
			cmap=cmap,
			cut_coords=cut,
			interpolation=interpolation,
			title=None,
			annotate=False,
			draw_cross=False,
			black_bg=black_bg,
			colorbar=False,
			)
	else:
		try:
			stat_map = path.abspath(path.expanduser(stat_map))
		except AttributeError:
			pass
		display = nilearn.plotting.plot_stat_map(stat_map,
			bg_img=template,
			threshold=threshold,
			figure=fig,
			axes=ax,
			cmap=cmap,
			cut_coords=cut,
			interpolation=interpolation,
			dim=dim,
			title=None,
			annotate=False,
			draw_cross=False,
			black_bg=black_bg,
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
			overlay = path.abspath(path.expanduser(overlay))
		except AttributeError:
			pass
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
	shape="portrait",
	draw_colorbar=True,
	ax=None,
	):

	"""Plot a list of statistical maps.
	This Function acts as a wrapper of nilearn.plotting.plot_stat_map, adding support for multiple axes, using a prettier default and allowing intelligent text and crosshair scaling.

	Parameters
	----------

	stat_maps : list or numpy.array
		A list of strings containing statistical map paths or statistical map objects to be plotted. If a `numpy.array` is provided, the shape and order is used to place the subplots.

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

	subplot_titles : list or numpy.array, optional
		List of titles for sub plots. Must be empty list or strings list of the same length as the stats_maps list.

	shape : {"portrait", "landscape"}
		if the `stat_maps` variable does not have a shape (i.e. if it is simply a list) this variable controls the kind of shape which the function auto-determines.
		Setting this parameter to "portrait" will force a shape with two columns, whereas setting it to "landscape" will force a shape with two rows.

	Notes
	-----

	Identical consequitive statistical maps are auto-detected and share a colorbar.
	To avoid starting a shared colorbar at the end of a column, please ensure that the length of statistical maps to be plotted is divisible both by the group size and the number of columns.
	"""


	if isinstance(stat_maps, str):
		stat_maps=[stat_maps]
	if len(stat_maps) == 1:
		if not ax:
			fig, ax = plt.subplots(facecolor='#eeeeee')
		else:
			fig = None

		if figure_title:
			fig.suptitle(figure_title, fontsize=scale*20, fontweight='bold')

		if subplot_titles:
			title = subplot_titles[0]
		else:
			title=None

		if draw_colorbar:
			cax, kw = _draw_colorbar(stat_maps[0],ax,
				threshold=threshold,
				aspect=30,
				fraction=0.05,
				anchor=(1.,0.5),
				)
		if overlays:
			my_overlay = overlays[0]
		else:
			my_overlay = None
		display = scaled_plot(stat_maps[0], template, fig, ax,
			overlay=my_overlay,
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
		try:
			nrows, ncols = stat_maps.shape
			#scale = scale/float(min(nrows, ncols))
		except AttributeError:
			if shape == "portrait":
				ncols = 2
				#we use inverse floor division to get the ceiling
				nrows = -(-len(stat_maps)//2)
				#scale = scale/float(ncols)
			elif shape == "landscape":
				nrows = 2
				#we use inverse floor division to get the ceiling
				ncols = -(-len(stat_maps)//2)
				#scale = scale/float(nrows)
		fig, ax = plt.subplots(figsize=(6*ncols,2.5*nrows), facecolor='#eeeeee', nrows=nrows, ncols=ncols)
		if figure_title:
			fig.suptitle(figure_title, fontsize=scale*35, fontweight='bold')
		conserve_colorbar_steps = 0
		# We transform the axes array so that we iterate column-first rather than row-first.
		# This is done to better share colorbars between consecutive axes.
		flat_axes = list(ax.T.flatten())
		try:
			stat_maps = list(stat_maps.T.flatten())
		except AttributeError:
			pass
		try:
			subplot_titles = list(subplot_titles.T.flatten())
		except AttributeError:
			pass
		if len(overlays) == 1:
			overlays = overlays*len(stat_maps)
		elif len(overlays) == 0:
			overlays = [None]*len(stat_maps)
		if len(cut_coords) == 1:
			cut_coords = cut_coords*len(stat_maps)
		elif len(cut_coords) == 0:
			cut_coords = [None]*len(stat_maps)
		else:
			try:
				cut_coords = list(cut_coords.T.flatten())
			except AttributeError:
				pass
		cbar_aspect = 30
		if nrows >=2:
			fraction = 0.09
		elif ncols >=2:
			fraction = 0.025
		else:
			fraction = 0.04
		for ix, ax in enumerate(flat_axes):
			draw_colorbar=False
			#create or use conserved colorbar for multiple cnsecutive plots of the same image
			if conserve_colorbar_steps == 0:
				draw_colorbar=True
				while True and conserve_colorbar_steps < len(stat_maps)-ix:
					if stat_maps[ix+conserve_colorbar_steps] == stat_maps[ix]:
						conserve_colorbar_steps+=1
					else:
						break

			if subplot_titles:
				try:
					title = subplot_titles[ix]
				except IndexError:
					title = None
			else:
				title = None
			# Axes are fully populating the grid - this may exceed the available number of statistic maps (`stat_maps`).
			# The missing statistic maps may either be missing (raising an `IndexError`) or `None` (raising an `AttributeError` from `_draw_colorbar` and `TypeError` from `scaled_plot`).
			try:
				if draw_colorbar:
					cax, kw = _draw_colorbar(stat_maps[ix],flat_axes[ix:ix+conserve_colorbar_steps],
						threshold=threshold,
						aspect=cbar_aspect,
						fraction=fraction,
						anchor=(2,0.5),
						)
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
			except (AttributeError, IndexError, TypeError):
				ax.axis('off')
			conserve_colorbar_steps-=1
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
	alpha=0.7,
	anat="/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii",
	ax=None,
	color="#E69F00",
	fig=None,
	label_names=[],
	mapping="",
	annotate=True,
	black_bg=False,
	draw_cross=True,
	threshold=None,
	roi=False,
	subplot_titles=[],
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

	display = nilearn.plotting.plot_roi(roi,
		alpha=alpha,
		annotate=False,
		axes=ax,
		bg_img=anat,
		black_bg=black_bg,
		draw_cross=False,
		cmap=cm,
		dim=dim,
		figure=fig,
		)
	if draw_cross:
		display.draw_cross(linewidth=scale*1.6, alpha=0.4)
	if annotate:
		display.annotate(size=2+scale*18)
	if subplot_titles:
		display.title(title, size=2+scale*26)

	return display

def contour_slices(bg_image, file_template,
	invert=False,
	alpha=[0.9],
	colors=['r','g','b'],
	dimming=0.,
	figure_title='',
	force_reverse_slice_order=True,
	legend_template='',
	levels_percentile=[80],
	linewidths=(),
	ratio='portrait',
	save_as='',
	scale=0.4,
	slice_spacing=0.5,
	substitutions=[{},],
	samri_style='light',
	title_color='#BBBBBB',
	):
	"""
	Plot coronal `bg_image` slices at a given spacing, and overlay contours from a list of NIfTI files.

	Parameters
	----------

	bg_image : str
		Path to the NIfTI image to draw in grayscale as th eplot background.
		This would commonly be some sort of brain template.
	file_template : str
		String template giving the path to the overlay stack.
		To create multiple overlays, this template will iteratively be substituted with each of the substitution dictionaries in the `substitutions` parameter.
	invert : boolean, optional
		Whether to automatically invert data matrix values (useful if the image consists of negative values, e.g. when dealing with negative contrast agent CBV scans).
	alpha : list, optional
		List of floats, specifying with how much alpha to draw each contour.
	colors : list, optional
		List of colors in which to plot the overlays.
	dimming : float, optional
		Dimming factor, generally between -2 and 2 (-2 increases contrast, 2 decreases it).
		This parameter is passed directly to `nilearn.plotting.plot_anat()`
		Set to 'auto', to use nilearn automagick dimming.
	figure_title : str, optional
		Title for the figure.
	force_reverse_slice_order : bool, optional
		Whether to force the reversal of the slice order.
		This can be done to enforce a visual presentation without having to modify the underlying data (i.e. visualize neurological-order slices in radiological order).
		This option should generally be avoided, ideally one would not obfuscate the data orientation when plotting.
	legend_template : string, optional
		String template which can be formatted with the dictionaries contained in the `substitutions` parameter.
		The resulting strings will give the legend text.
	levels_percentile : list, optional
		List of integers, specifying at which percentiles of each overlay to draw contours.
	line_widths : tuple, optional
		Tuple of desired contour line widths (one per substitution).
	ratio : list or {'landscape', 'portrait'}, optional
		Either a list of 2 integers giving the desired number of rows and columns (in this order), or a string, which is either 'landscape' or 'portrait', and which prompts the function to auto-determine the best number of rows and columns given the number of slices and the `scale` attribute.
	save_as : str, optional
		Path under which to save the output figure.
		The string may contain formatting fields from the first dictionary in the `substitutions` variable.
	scale : float, optional
		The expected ratio of the slice height dividrd by the sum of the slice height and width.
		This somewhat complex metric controls the row and column distribution of slices in the 'landscape' and 'portrait' plotting shapes.
	slice_spacing : float
		Slice spacing in mm.
	substitutions : list of dicts, optional
		A list of dictionaried, with keys including all substitution keys found in the `file_template` parameter, and values giving desired substitution values which point the `file_template` string templated to existing filed which are to be included in the overlay stack.
		Such a dictionary is best obtained via `samri.utilities.bids_substitution_iterator()`.
	title_color : string, optional
		String specifying the desired color for the title.
		This needs to be specified in-function, because the matplotlibrc styling standard does not provide for title color specification [matplotlibrc_title]

	References
	----------

	.. [matplotlibrc_title] https://stackoverflow.com/questions/30109465/matplotlib-set-title-color-in-stylesheet
	"""

	if len(substitutions) == 0:
		print('ERROR: You have specified a substitution dictionary of length 0. There needs to be at least one set of substitutions. If your string contains no formatting fields, please pass a list containing an empty dictionary to the `sbstitution parameter` (this is also its default value).')

	plotting_module_path = path.dirname(path.realpath(__file__))
	if samri_style=='light':
		black_bg=False
		anatomical_cmap = 'binary'
		style_path = path.join(plotting_module_path,'contour_slices.conf')
		plt.style.use([style_path])
	elif samri_style=='dark':
		black_bg=True
		anatomical_cmap = 'binary_r'
		style_path = path.join(plotting_module_path,'contour_slices_dark.conf')
		plt.style.use([style_path])

	bg_image = path.abspath(path.expanduser(bg_image))
	bg_img = nib.load(bg_image)
	if bg_img.header['dim'][0] > 3:
		bg_data = bg_img.get_data()
		ndim = 0
		for i in range(len(bg_img.header['dim'])-1):
			current_dim = bg_img.header['dim'][i+1]
			if current_dim == 1:
				break
			ndim += 1
		bg_img.header['dim'][0] = ndim
		bg_img.header['pixdim'][ndim+1:] = 0
		bg_data = bg_data.T[0].T
		bg_img = nib.nifti1.Nifti1Image(bg_data, bg_img.affine, bg_img.header)

	imgs = []
	bounds = []
	levels = []
	slice_order_is_reversed = 0
	for substitution in substitutions:
		filename = file_template.format(**substitution)
		filename = path.abspath(path.expanduser(filename))
		img = nib.load(filename)
		data = img.get_data()
		if img.header['dim'][0] > 3:
			img = collapse(img)
		if invert:
			data = -data
			img = nib.nifti1.Nifti1Image(data, img.affine, img.header)
		#we should only be looking at the percentile of the entire data matrix, rather than just the active slice
		for level_percentile in levels_percentile:
			level = np.percentile(data,level_percentile)
			levels.append(level)
		slice_row = img.affine[1]
		subthreshold_start_slices = 0
		while True:
			for i in np.arange(data.shape[1]):
				my_slice = data[:,i,:]
				if my_slice.max() < min(levels):
					subthreshold_start_slices += 1
				else:
					break
			break
		subthreshold_end_slices = 0
		while True:
			for i in np.arange(data.shape[1])[::-1]:
				my_slice = data[:,i,:]
				if my_slice.max() < min(levels):
					subthreshold_end_slices += 1
				else:
					break
			break
		img_min_slice = slice_row[3] + subthreshold_start_slices*slice_row[1]
		img_max_slice = slice_row[3] + (data.shape[1]-subthreshold_end_slices)*slice_row[1]
		bounds.extend([img_min_slice,img_max_slice])
		if slice_row[1] < 0:
			slice_order_is_reversed += 1
		else:
			slice_order_is_reversed -= 1
		imgs.append(img)

	if len(alpha) == 1:
		alpha = alpha * len(imgs)

	min_slice = min(bounds)
	max_slice = max(bounds)
	cut_coords = np.arange(min_slice, max_slice, slice_spacing)
	if slice_order_is_reversed > 0:
		cut_coords = cut_coords[::-1]
	if force_reverse_slice_order:
		cut_coords = cut_coords[::-1]

	if not linewidths:
		linewidths = (rcParams['axes.linewidth'],)*len(imgs)

	if len(cut_coords) > 3:
		cut_coord_length = len(cut_coords)
		if legend_template:
			cut_coord_length += 1
		try:
			nrows, ncols = ratio
		except ValueError:
			if ratio == "portrait":
				ncols = np.floor(cut_coord_length**(scale))
				nrows = np.ceil(cut_coord_length/float(ncols))
			elif ratio == "landscape":
				nrows = np.floor(cut_coord_length**(scale))
				ncols = np.ceil(cut_coord_length/float(nrows))
		# we adjust the respective rc.Param here, because it needs to be set before drawing to take effect
		if legend_template and cut_coord_length == ncols*(nrows-1)+1:
			rcParams['figure.subplot.bottom'] = np.max([rcParams['figure.subplot.bottom']-0.05,0.])

		figsize = np.array(rcParams['figure.figsize'])
		figsize_scales = figsize/np.array([float(ncols),float(nrows)])
		figsize_scale = figsize_scales.min()
		fig, ax = plt.subplots(figsize=(ncols*figsize_scale,nrows*figsize_scale),
				nrows=int(nrows), ncols=int(ncols),
				)
		flat_axes = list(ax.flatten())
		for ix, ax_i in enumerate(flat_axes):
			try:
				display = nilearn.plotting.plot_anat(bg_img,
					axes=ax_i,
					display_mode='y',
					cut_coords=[cut_coords[ix]],
					annotate=False,
					black_bg=black_bg,
					dim=dimming,
					cmap=anatomical_cmap,
					)
			except IndexError:
				ax_i.axis('off')
			else:
				for img_ix, img in enumerate(imgs):
					color = colors[img_ix]
					display.add_contours(img,
							alpha=alpha[img_ix],
							colors=[color],
							levels=levels[img_ix],
							linewidths=(linewidths[img_ix],),
							)

		if legend_template:
			for ix, img in enumerate(imgs):
				insertion_legend, = plt.plot([],[], color=colors[ix], label=legend_template.format(**substitutions[ix]))
			if cut_coord_length == ncols*(nrows-1)+1:
				plt.legend(loc='upper left',bbox_to_anchor=(-0.1, -0.3))
			else:
				plt.legend(loc='lower left',bbox_to_anchor=(1.1, 0.))
	else:
		display = nilearn.plotting.plot_anat(bg_img,
			display_mode='y',
			cut_coords=cut_coords,
			black_bg=black_bg,
			)
		for ix, img in enumerate(imgs):
			color = colors[ix]
			display.add_contours(img, levels=levels, colors=[color])

	if figure_title:
		fig.suptitle(figure_title, color=title_color)

	if save_as:
		save_as = save_as.format(**substitutions[0])
		save_as = path.abspath(path.expanduser(save_as))
		plt.savefig(save_as,
			#facecolor=fig.get_facecolor(),
			)
