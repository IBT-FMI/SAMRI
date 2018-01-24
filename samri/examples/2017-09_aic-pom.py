from os import path
import matplotlib.pyplot as plt
from samri.plotting.aggregate import registration_qc
from samri.typesetting import inline_anova

this_path = path.dirname(path.realpath(__file__))

data_dir = path.join(this_path,"../../example_data/")
df_path = path.join(data_dir,"f_reg_quality.csv")

plt.style.use(path.join(this_path,"dark.conf"))
registration_qc(df_path,
	value={"similarity":"Similarity"},
	group={"subject":"Subject"},
	repeat={"session":"Session"},
	extra={"acquisition":"Type"},
	save_as="2017-09_aic-pom.pdf",
	show=False,
	samri_style=False,
	extra_cmap=["#FFFFFF","#000000"],
	cmap=["#EE1111","#11DD11","#1111FF","#CCCC22","#AA11AA"],
	values_rename={
		"sub":"Subject",
		"EPI_CBV_chr_longSOA":"longer",
		"EPI_CBV_jb_long":"shorter",
		},
	)
