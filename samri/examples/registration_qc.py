from os import path
from samri.plotting.aggregate import registration_qc
from samri.typesetting import inline_anova


data_dir = path.join(path.dirname(path.realpath(__file__)),"../../example_data/")
df_path = path.join(data_dir,"f_reg_quality.csv")

anova_summary = registration_qc(df_path,
	value={"similarity":"Similarity"},
	group={"sub":"Subject"},
	repeat={"ses":"Session"},
	extra={"trial":"Type"},
	model="{value} ~ C({extra}) + C({repeat}) + C({group}) -1",
	save_as="registration_qc.png",
	print_model=True,
	print_anova=True,
	show=False,
	anova_type=2,
	)

print(inline_anova(anova_summary,"C(Subject)",style="python"))
print(inline_anova(anova_summary,"C(Session)",style="python", max_len=2))
print(inline_anova(anova_summary,"C(Type)",style="python"))
print(inline_anova(anova_summary,"C(Subject)",style="tex"))
print(inline_anova(anova_summary,"C(Session)",style="tex", max_len=2))
print(inline_anova(anova_summary,"C(Type)",style="tex"))
