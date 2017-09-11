from os import path
import matplotlib.pyplot as plt
from samri.plotting.aggregate import registration_qc
from samri.typesetting import inline_anova

this_path = path.dirname(path.realpath(__file__))

data_dir = path.join(this_path,"../../example_data/")
df_path = path.join(data_dir,"f_reg_quality.csv")

plt.style.use(path.join(this_path,"dark.conf"))
anova_summary = registration_qc(df_path,
	value={"similarity":"Similarity"},
	group={"sub":"Subject"},
	repeat={"ses":"Session"},
	extra={"trial":"Type"},
	model="{value} ~ C({extra}) + C({repeat}) + C({group}) -1",
	save_as="2017-09_aic-pom.pdf",
	print_model=True,
	print_anova=True,
	show=False,
	anova_type=3,
	samri_style=False,
	extra_cmap=["#FFFFFF","#000000"],
	cmap=["#EE1111","#11DD11","#1111FF","#CCCC22","#AA11AA"],
	values_rename={
		"sub":"Subject",
		"EPI_CBV_chr_longSOA":"longer",
		"EPI_CBV_jb_long":"shorter",
		},
	)

print(inline_anova(anova_summary,"C(Subject)",style="python"))
print(inline_anova(anova_summary,"C(Session)",style="python", max_len=2))
print(inline_anova(anova_summary,"C(Type)",style="python"))
print(inline_anova(anova_summary,"C(Subject)",style="tex"))
print(inline_anova(anova_summary,"C(Session)",style="tex", max_len=2))
print(inline_anova(anova_summary,"C(Type)",style="tex"))
