import matplotlib.pyplot as plt
import pandas as pd
from os import path

def registration_qc(df,
	samri_style=True,
	show=True,
	value={"similarity":"Similarity"},
	group={"sub":"Subject"},
	repeat={"ses":"Session"},
	print_model=False,
	print_anova=False,
	save_as=False,
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
		plt.style.use('ggplot')

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
	df = df.rename(columns=column_renames)

	value = list(value.values())[0]
	group = list(group.values())[0]
	repeat = list(repeat.values())[0]

	model = "{value} ~ C({group}) + C({repeat}) -1".format(value=value, group=group, repeat=repeat)
	regression_model = smf.ols(model, data=df).fit()
	if print_model:
		print(regression_model.summary())

	anova_summary = sm.stats.anova_lm(regression_model, typ=2) # Type 2 ANOVA DataFrame
	if print_anova:
		print(anova_summary)

	myplot = sns.swarmplot(x=group, y=value, hue=repeat, data=df)

	if show:
		sns.plt.show()
	if save_as:
		plt.savefig(path.abspath(path.expanduser(save_as)), bbox_inches='tight')

	return anova_summary
