import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patheffects as path_effects
import numpy as np
import pandas as pd
import seaborn as sns
from os import path
from matplotlib import rcParams

EXTRA_COLORSET = ["#797979","#000000","#505050","#FFFFFF","#B0B0B0",]

def apply_label(x, color, label,
	text_side='left',
	lw=False,
	x_align=0.0,
	y_align=0.04,
	contour_ratio=1.5,
	text_color=False,
	):
	if text_color:
		color=text_color
	ax = plt.gca()
	if not lw:
		lw = mpl.rcParams['lines.linewidth']
	if text_side == 'left':
		text = ax.text(x_align, y_align, label,
			fontweight="bold",
			color=color,
			horizontalalignment="left",
			va="bottom",
			# For diagnostic purposes, the rasterization workaround should be removed once we can identify why function execution in PythonTeX introduces enlarged bounding boxes.
			#bbox=dict(facecolor='red', alpha=0.5),
			transform=ax.transAxes,
			)
	if text_side == 'right':
		text = ax.text(1.0-x_align, y_align, label,
			fontweight="bold",
			color=color,
			horizontalalignment="right",
			va="bottom",
			# For diagnostic purposes, the rasterization workaround should be removed once we can identify why function execution in PythonTeX introduces enlarged bounding boxes.
			#bbox=dict(facecolor='red', alpha=0.5),
			rasterized=True,
			transform=ax.transAxes,
			)
	text.set_path_effects([path_effects.Stroke(linewidth=lw*contour_ratio, foreground='w'),
	       path_effects.Normal()])

def registration_qc(df,
	cmap="Set3",
	extra=False,
	extra_cmap=EXTRA_COLORSET,
	group={"sub":"Subject"},
	repeat={"ses":"Session"},
	samri_style=True,
	save_as=False,
	show=True,
	value={"similarity":"Similarity"},
	values_rename={},
	):
	"""Aggregate plot of similarity metrics for registration quality control

	Parameters
	----------

	df : pandas.DataFrame or str
		Pandas Dataframe or CSV file containing similarity scores.
	cmap : str or list, optional
		If a string, the variable specifies the matplotlib colormap [2]_ (qualitative colormaps are recommended) to use for `repeat` highlighting. If a List, the variable should be a list of colors (e.g. `["#00FF00","#2222FF"]`).
	extra_cmap : str or list, optional
		If a string, the variable specifies the matplotlib colormap [2]_ (qualitative colormaps are recommended) to use for `extra` highlighting,  which is applied as a contour to the `repeat`-colored pacthes. If a List, the variable should be a list of colors (e.g. `["#00FF00","#2222FF"]`).
	group : str or dict, optional
		Column of `df` to use as the group factor (values of this factor will represent the x-axis). If a dictionary is passed, the column named for the key of the dictionary is renamed to the value, and the value name is then used as the group factor. This is useful for the input of longer but clearer names for plotting.
	samri_style : bool, optional
		Whether to apply a generic SAMRI style to the plot.
	save_as : str, optional
		Path under which to save the generated plot (format is interpreted from provided extension).
	show : bool, optional
		Whether to show the plot in an interactive window.
	repeat : str or dict, optional
		Column of `df` to use as the repeat factor (values of this factor will be represent via different hues, according to `cmap`). If a dictionary is passed, the column named for the key of the dictionary is renamed to the value, and the value name is then used as the group factor. This is useful for the input of longer but clearer names for plotting.
	value : str or dict, optional
		Column of `df` to use as the value (this variable will be represented on the y-axis). If a dictionary is passed, the column named for the key of the dictionary is renamed to the value, and the value name is then used as the group factor. This is useful for the input of longer but clearer names for plotting.
	values_rename : dict, optional
		Dictionary used to rename values in `df`. This is useful for the input of longer but clearer names for plotting (this parameter will not rename column names, for renaming those, see parameters `extra`, `group`, `repeat`, and `value`).

	Returns
	-------
	pandas.DataFrame
		ANOVA summary table in DataFrame format.

	Reference
	----------
	.. [1] http://goanna.cs.rmit.edu.au/~fscholer/anova.php

	.. [2] https://matplotlib.org/examples/color/colormaps_reference.html

	.. [3] http://www.statsmodels.org/dev/example_formulas.html
	"""

	if samri_style:
		this_path = path.dirname(path.realpath(__file__))
		plt.style.use(path.join(this_path,"samri.conf"))

	try:
		if isinstance(df, basestring):
			df = path.abspath(path.expanduser(df))
			df = pd.read_csv(df)
	except NameError:
		if isinstance(df, str):
			df = path.abspath(path.expanduser(df))
			df = pd.read_csv(df)

	for key in values_rename:
		df.replace(to_replace=key, value=values_rename[key], inplace=True)

	column_renames={}
	if isinstance(value, dict):
		column_renames.update(value)
		value = list(value.values())[0]
	if isinstance(group, dict):
		column_renames.update(group)
		group = list(group.values())[0]
	if isinstance(repeat, dict):
		column_renames.update(repeat)
		repeat = list(repeat.values())[0]
	if isinstance(extra, dict):
		column_renames.update(extra)
		extra = list(extra.values())[0]
	df = df.rename(columns=column_renames)

	if extra:
		myplot = sns.swarmplot(x=group, y=value, hue=extra, data=df,
			size=rcParams["lines.markersize"]*1.4,
			palette=sns.color_palette(extra_cmap),
			)
		myplot = sns.swarmplot(x=group, y=value, hue=repeat, data=df,
			edgecolor=(1, 1, 1, 0.0),
			linewidth=rcParams["lines.markersize"]*.4,
			palette=sns.color_palette(cmap),
			)
	else:
		myplot = sns.swarmplot(x=group, y=value, hue=repeat, data=df,
			palette=sns.color_palette(cmap),
			size=rcParams["lines.markersize"]*2,
			)

	plt.legend(loc=rcParams["legend.loc"])

	if show:
		sns.plt.show()
	if save_as:
		plt.savefig(path.abspath(path.expanduser(save_as)), bbox_inches='tight')

def roi_distributions(df,
	ascending=False,
	cmap='viridis',
	exclude_tissue_type=[],
	max_rois=7,
	save_as='',
	small_roi_cutoff=8,
	start=0.0,
	stop=1.0,
	text_side='left',
	value_label='values',
	xlim=None,
	ylim=None,
	bw=0.2,
	hspace=-0.1,
	):
	"""Plot the distributions of values inside 3D image regions of interest.

	Parameters
	----------

	df : str or pandas.DataFrame
		A Pandas Dataframe, or path to one, which contains columns named 'Structure', 'tissue type', and the value of the `value_label` parameter (values by default).
	ascending : boolean, optional
		Whether to plot the ROI distributions from lowest to highest mean
		(if `False` the ROI distributions are plotted from highest to lowest mean).
	bw : float, optional
		Bandwidth scalar factor for the kernel size estimation.
	cmap : string, optional
		Name of matplotlib colormap which to color the plot array with.
	exclude_tissue_type : list, optional
		What tissue types to discount from plotting.
		Values in this list will be ckecked on the 'tissue type' column of `df`.
		This is commonly used to exclude cerebrospinal fluid ROIs from plotting.
	max_rois : int, optional
		How many ROIs to limit the plot to.
	save_as : str, optional
		Path to save the figure to.
	small_roi_cutoff : int, optional
		Minimum number of rows per 'Structure' value required to add the respective 'Structure' value to the plot
		(this corresponds to the minimum number of voxels which a ROI needs to have in order to be included in the plot).
	start : float, optional
		At which fraction of the colormap to start.
	stop : float, optional
		At which fraction of the colormap to stop.
	text_side : {'left', 'right'}, optional
		Which side of the plot to set the `df` 'Structure'-column values on.
	xlim : list, optional
		X-axis limits, passed to `seaborn.FacetGrid()`
	ylim : list, optional
		Y-axis limits, passed to `seaborn.FacetGrid()`
	hspace : float, optional
		How much (in percent of the axis height) to overlap the individual axes.
	"""

	mpl.rcParams["xtick.major.size"] = 0.0
	mpl.rcParams["ytick.major.size"] = 0.0

	if isinstance(df,str):
		df = path.abspath(path.expanduser(df))
		df = pd.read_csv(df)
	if 'Side' in df.columns:
		df.loc[(df['Side']=='left'),'Structure'] = df.loc[(df['Side']=='left'),'Structure'] + ' (L)'
		df.loc[(df['Side']=='right'),'Structure'] = df.loc[(df['Side']=='right'),'Structure'] + ' (R)'
	df = pd.DataFrame({
		'Structure': row['Structure'],
		'tissue type': row['tissue type'],
		value_label: float(value),
		}
		for i, row in df.iterrows() for value in row[value_label].split(', ')
		)
	if small_roi_cutoff:
		for i in list(df['Structure'].unique()):
			if len(df[df['Structure']==i]) < small_roi_cutoff:
				df = df[df['Structure'] != i]
	df['mean'] = df.groupby('Structure')[value_label].transform('mean')
	df = df.sort_values(['mean'],ascending=ascending)
	if exclude_tissue_type:
		df = df[~df['tissue type'].isin(exclude_tissue_type)]
	if max_rois:
		uniques = list(df['Structure'].unique())
		keep = uniques[:max_rois]
		df = df[df['Structure'].isin(keep)]
	structures = list(df['Structure'].unique())

	# Apply FacetGrid limit values to dataframe
	if xlim:
		df = df.loc[
			(df[value_label] >= xlim[0])&
			(df[value_label] <= xlim[1])
			]

	# Define colors
	## The colormap is applied inversely, so we go from stop to start.
	cm_subsection = np.linspace(stop, start, len(structures))
	cmap = plt.get_cmap(cmap)
	pal = [ cmap(x) for x in cm_subsection ]

	# Initialize the FacetGrid object
	aspect = mpl.rcParams['figure.figsize']
	ratio = aspect[0]/aspect[1]
	g = sns.FacetGrid(df,
		row='Structure',
		hue='Structure',
		aspect=max_rois*ratio,
		height=aspect[1]/max_rois,
		palette=pal,
		xlim=xlim,
		ylim=ylim,
		despine=True,
		)

	# Draw the densities in a few steps
	lw = mpl.rcParams['lines.linewidth']
	g.map(sns.kdeplot, value_label, clip_on=False, gridsize=500, shade=True, alpha=1, lw=lw/4.*3, bw=bw)
	g.map(sns.kdeplot, value_label, clip_on=False, gridsize=500, color="w", lw=lw, bw=bw)
	g.map(plt.axhline, y=0, lw=lw, clip_on=False)

	# Define and use a simple function to label the plot in axes coordinates
	g.map(apply_label, value_label, text_side=text_side, lw=lw)

	# Set the subplots to overlap and apply the margins which for some reason otherwise get reset here
	g.fig.subplots_adjust(
		left=mpl.rcParams['figure.subplot.left'],
		bottom=mpl.rcParams['figure.subplot.bottom'],
		right=mpl.rcParams['figure.subplot.right'],
		top=mpl.rcParams['figure.subplot.top'],
		wspace=0.0,
		hspace=hspace,
		)

	# Remove axes details that don't play will with overlap
	g.set_titles("")
	g.set(yticks=[])

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		plt.savefig(save_as)

def roi_sums(df,
	ascending=False,
	palette=['#984ea3'],
	exclude_tissue_type=[],
	max_rois=7,
	save_as=False,
	small_roi_cutoff=8,
	text_side='left',
	value_label='Assignment',
	target_label='Assigned Fraction',
	roi_value=1,
	xlim=None,
	ylim=None,
	hspace=0.0,
	x_align=0.0,
	y_align=0.1,
	contour_ratio=1.5,
	text_color=False,
	):
	"""Plot the percentage of voxels with values equal to `target_value` in atlas regions of interest.

	Parameters
	----------

	df : str or pandas.DataFrame
		A Pandas Dataframe, or path to one, which contains columns named 'Structure', 'tissue type', and the value of the `value_label` parameter (values by default).
	ascending : boolean, optional
		Whether to plot the ROI distributions from lowest to highest mean
		(if `False` the ROI distributions are plotted from highest to lowest mean).
	cmap : string, optional
		Name of matplotlib colormap which to color the plot array with.
	exclude_tissue_type : list, optional
		What tissue types to discount from plotting.
		Values in this list will be ckecked on the 'tissue type' column of `df`.
		This is commonly used to exclude cerebrospinal fluid ROIs from plotting.
	max_rois : int, optional
		How many ROIs to limit the plot to.
	save_as : str, optional
		Path to save the figure to.
	small_roi_cutoff : int, optional
		Minimum number of rows per 'Structure' value required to add the respective 'Structure' value to the plot
		(this corresponds to the minimum number of voxels which a ROI needs to have in order to be included in the plot).
	start : float, optional
		At which fraction of the colormap to start.
	stop : float, optional
		At which fraction of the colormap to stop.
	text_side : {'left', 'right'}, optional
		Which side of the plot to set the `df` 'Structure'-column values on.
	xlim : list, optional
		X-axis limits, passed to `seaborn.FacetGrid()`
	ylim : list, optional
		Y-axis limits, passed to `seaborn.FacetGrid()`
	hspace : float, optional
		How much (in percent of the axis height) to overlap the individual axes.
	"""

	mpl.rcParams["xtick.major.size"] = 0.0
	mpl.rcParams["ytick.major.size"] = 0.0

	if isinstance(df,str):
		df = path.abspath(path.expanduser(df))
		df = pd.read_csv(df)
	if 'side' in df.columns:
		df.loc[(df['side']=='left'),'Structure'] = df.loc[(df['side']=='left'),'Structure'] + ' (L)'
		df.loc[(df['side']=='right'),'Structure'] = df.loc[(df['side']=='right'),'Structure'] + ' (R)'
	df = pd.DataFrame({
	       'Structure': row['Structure'],
	       'tissue type': row['tissue type'],
	       value_label: float(value),
	       }
	       for i, row in df.iterrows() for value in row[value_label].split(', ')
	       )

	new = []
	for i in list(df['Structure'].unique()):
	       d = {}
	       total = len(df[df['Structure']==i])
	       if small_roi_cutoff:
	               if total < small_roi_cutoff:
	                       break
	       assigned = len(df[(df['Structure']==i)&(df[value_label]==roi_value)])
	       d['Total'] = total
	       d['Assigned'] = assigned
	       d[target_label] = assigned / total
	       d['Structure'] = i
	       d['tissue type'] = df.loc[(df['Structure']==i),'tissue type'].unique()[0]
	       new.append(d)

	df = pd.DataFrame(new)

	df = df.sort_values([target_label],ascending=ascending)
	if exclude_tissue_type:
		df = df[~df['tissue type'].isin(exclude_tissue_type)]
	if max_rois:
	       uniques = list(df['Structure'].unique())
	       keep = uniques[:max_rois]
	       df = df[df['Structure'].isin(keep)]

	structures = list(df['Structure'].unique())

	# Initialize the FacetGrid object
	aspect = mpl.rcParams['figure.figsize']
	ratio = aspect[0]/aspect[1]
	g = sns.FacetGrid(df,
		row='Structure',
		hue='Structure',
		aspect=max_rois*ratio,
		height=aspect[1]/max_rois,
		palette=palette,
		xlim=xlim,
		ylim=ylim,
		despine=True,
		)

	# Draw the densities in a few steps
	lw = mpl.rcParams['lines.linewidth']
	g.map(sns.barplot, target_label, clip_on=False)
	#g.map(sns.kdeplot, value_label, clip_on=False, gridsize=500, shade=True, alpha=1, lw=lw/4.*3, bw=bw)
	#g.map(sns.kdeplot, value_label, clip_on=False, gridsize=500, color="w", lw=lw, bw=bw)
	#g.map(plt.axhline, y=0, lw=lw, clip_on=False)

	# Define and use a simple function to label the plot in axes coordinates
	g.map(apply_label, target_label,
		text_side=text_side,
		x_align=x_align,
		y_align=y_align,
		contour_ratio=contour_ratio,
		text_color=text_color,
		)

	# Set the subplots to overlap and apply the margins which for some reason otherwise get reset here
	g.fig.subplots_adjust(
		left=mpl.rcParams['figure.subplot.left'],
		bottom=mpl.rcParams['figure.subplot.bottom'],
		right=mpl.rcParams['figure.subplot.right'],
		top=mpl.rcParams['figure.subplot.top'],
		wspace=0.0,
		hspace=hspace,
		)

	# Remove axes details that don't play will with overlap
	g.set_titles("")
	g.set(yticks=[])

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		plt.savefig(save_as)
