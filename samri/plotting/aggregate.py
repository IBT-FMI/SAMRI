import matplotlib.pyplot as plt
import pandas as pd
from os import path

def inline_anova(df, factor,
	style="python",
	):
	"""Typeset factor summary from statsmodels-style anova DataFrame for inline mention.

	Parameters
	----------
	df : pandas.DataFrame
		Pandas DataFrame object containing an ANOVA summary.
	factor : str
		String indicating the factor of interest from the summary given by `df`.
	style : {"python", "tex"}
		What formatting to apply to the string. A simple Python compatible string is returned when selecting "python", whereas a fancier output (decorated with TeX syntax) is returned if selecting "tex".
	"""

	if style == "python":
		inline = "F({},{})={}, p={}".format(
			int(df["df"][factor]),
			int(df["df"]["Residual"]),
			df["F"][factor],
			df["PR(>F)"][factor],
			)
	elif style == "tex":
		inline = "F({},{})={}, p={}".format(
			df["df"][factor],
			df["df"]["Residual"],
			df["F"][factor],
			df["PR(>F)"][factor],
			)

	return inline

def registration_qc(df,
	samri_style=True,
	show=True,
	value={"similarity":"Similarity"},
	group={"sub":"Subject"},
	repeat={"ses":"Session"},
	print_model=False,
	print_anova=False,
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

	value = value.values()[0]
	group = group.values()[0]
	repeat = repeat.values()[0]

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

	return anova_summary

if __name__ == "__main__":
	anova_summary = registration_qc("../../example_data/f_reg_quality.csv", show=False)

	subject_anova_summary = "F({},{})={}, p={}".format(
		anova_summary["df"]["C(Subject)"],
		anova_summary["df"]["Residual"],
		anova_summary["F"]["C(Subject)"],
		anova_summary["PR(>F)"]["C(Subject)"],
		)
	session_anova_summary = "F({},{})={}, p={}".format(
		anova_summary["df"]["C(Session)"],
		anova_summary["df"]["Residual"],
		anova_summary["F"]["C(Session)"],
		anova_summary["PR(>F)"]["C(Session)"],
		)
	print(subject_anova_summary,session_anova_summary)
