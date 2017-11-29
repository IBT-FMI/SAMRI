import matplotlib.pyplot as plt
import pandas as pd
from os import path
from matplotlib import rcParams

EXTRA_COLORSET = ["#797979","#000000","#505050","#FFFFFF","#B0B0B0",]

def registration_qc(df,
	cmap="Set3",
	extra=False,
	extra_cmap=EXTRA_COLORSET,
	group={"sub":"Subject"},
	print_model=False,
	print_anova=False,
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
	anova_type : int, optional
		Type of the ANOVA to use for model analysis. Consult [1]_ for a theoretical overview, and `statsmodels.stats.anova.anova_lm` for the implementation we use.
	cmap : str or list, optional
		If a string, the variable specifies the matplotlib colormap [2]_ (qualitative colormaps are recommended) to use for `repeat` highlighting. If a List, the variable should be a list of colors (e.g. `["#00FF00","#2222FF"]`).
	extra_cmap : str or list, optional
		If a string, the variable specifies the matplotlib colormap [2]_ (qualitative colormaps are recommended) to use for `extra` highlighting,  which is applied as a contour to the `repeat`-colored pacthes. If a List, the variable should be a list of colors (e.g. `["#00FF00","#2222FF"]`).
	group : str or dict, optional
		Column of `df` to use as the group factor (values of this factor will represent the x-axis). If a dictionary is passed, the column named for the key of the dictionary is renamed to the value, and the value name is then used as the group factor. This is useful for the input of longer but clearer names for plotting.
	model : string, optional
		A string specifying the ANOVA formula as a statsmodels function [3]_. It may contain string substitutions (e.g. `"{value} ~ C({group})"`).
	print_model : bool, optional
		Whether to print the model output table.
	print_anova : bool, optional
		Whether to print the ANOVA output table.
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
	import seaborn.apionly as sns
	import statsmodels.api as sm
	import statsmodels.formula.api as smf

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
			)

	plt.legend(loc=rcParams["legend.loc"])

	if show:
		sns.plt.show()
	if save_as:
		plt.savefig(path.abspath(path.expanduser(save_as)), bbox_inches='tight')
