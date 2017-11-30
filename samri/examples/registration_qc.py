import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from os import path
from samri.plotting.aggregate import registration_qc
from samri.typesetting import inline_anova

data_dir = path.join(path.dirname(path.realpath(__file__)),"../../example_data/")
df_path = path.join(data_dir,"f_reg_quality.csv")

registration_qc(df_path,
	value={"similarity":"Similarity"},
	group={"subject":"Subject"},
	repeat={"session":"Session"},
	extra={"acquisition":"Acquisition"},
	save_as="registration_qc.png",
	show=False,
	)

df = pd.read_csv(df_path)
#model="similarity ~ C(acquisition) + C(session) + C(subject)"
model="similarity ~ C(session) + C(subject)"
regression_model = smf.ols(model, data=df).fit()
anova_summary = sm.stats.anova_lm(regression_model, typ=2)

print(inline_anova(anova_summary,"C(subject)",style="python"))
print(inline_anova(anova_summary,"C(session)",style="python", max_len=2))
#print(inline_anova(anova_summary,"C(acquisition)",style="python"))
print(inline_anova(anova_summary,"C(subject)",style="tex"))
print(inline_anova(anova_summary,"C(session)",style="tex", max_len=2))
#print(inline_anova(anova_summary,"C(acquisition)",style="tex"))
