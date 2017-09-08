import matplotlib.pyplot as plt
import pandas as pd
from os import path
from matplotlib import rcParams

EXTRA_COLORSET = ["#797979","#000000","#505050","#FFFFFF","#B0B0B0",]

def registration_qc(df,
	samri_style=True,
	show=True,
	value={"similarity":"Similarity"},
	group={"sub":"Subject"},
	repeat={"ses":"Session"},
	extra=False,
	model="{value} ~ C({extra_factor}) + C({group}) + C({repeat}) -1",
	print_model=False,
	print_anova=False,
	save_as=False,
	cmap="Set3",
	extra_cmap=EXTRA_COLORSET,
	):
	"""Aggregate plot of similarity metrics for registration quality control

	Parameters
	----------

	df : pandas.DataFrame or str
		Pandas Dataframe or CSV file containing similarity scores.
	show : bool
		Whether to show the plot in an interactive window.
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

	column_renames={}
	column_renames.update(value)
	column_renames.update(group)
	column_renames.update(repeat)
	value = list(value.values())[0]
	group = list(group.values())[0]
	repeat = list(repeat.values())[0]
	if extra:
		column_renames.update(extra)
		extra = list(extra.values())[0]
	df = df.rename(columns=column_renames)

	model = model.format(value=value, group=group, repeat=repeat, extra=extra)
	regression_model = smf.ols(model, data=df).fit()
	if print_model:
		print(regression_model.summary())

	anova_summary = sm.stats.anova_lm(regression_model, typ=2) # Type 2 ANOVA DataFrame
	if print_anova:
		print(anova_summary)

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

	if show:
		sns.plt.show()
	if save_as:
		plt.savefig(path.abspath(path.expanduser(save_as)), bbox_inches='tight')

	return anova_summary
