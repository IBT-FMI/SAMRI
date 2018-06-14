import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from os import path
from samri.plotting.aggregate import registration_qc
from samri.typesetting import inline_anova
from math import sqrt
from samri.development import reg_cc
from samri.pipelines.reposit import bru2bids
from os import path

from samri.pipelines.preprocess import bruker, legacy_bruker
from samri.development import reg_cc

def evaluateQuality():
#       data_dir = path.join(path.dirname(path.realpath(__file__)),"../../example_data/")
#       df_path = path.join(data_dir,"f_reg_quality.csv")
#
#       registration_qc(df_path,
#               value={"similarity":"Similarity"},
#               group={"subject":"Subject"},
#               repeat={"session":"Session"},
#               extra={"acquisition":"Acquisition"},
#               save_as="registration_qc.png",
#               show=False,
#               )

        path = "/media/nexus/storage2/ni_data/christian_bids_data/preprocessing_new/generic/"
        template = "/home/nexus/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii"
        reg_cc(path=path, template=template)

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


        # plotting variance results for different metrics
        # TODO: warum MI = 0?

        metrics = ['CC', 'MI', 'GC']
        means = []
        stds = []

        for metric in metrics:
                df_path = path.join('./',"f_reg_quality_"+metric+".csv")
                df = pd.read_csv(df_path)
                variances = df.groupby('subject').agg('var')
                std = sqrt(variances['similarity'].sum())
                mean = df.groupby('subject').agg('mean')['similarity'].sum()
                means.append(mean)
                stds.append(std)

        print(metrics)
        print(means)
        print(stds)

        return metrics, means, stds


def evaluateMetrics(fname = "./f_reg_quality"):


#       import matplotlib
#       matplotlib.use('agg')
#
#       path = "/media/nexus/storage2/ni_data/christian_bids_data/newly_processed/preprocessing/generic/"
#       template = "/home/nexus/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii"
#       reg_cc(path=path, template=template)

        metrics = ['CC', 'MI', 'GC']
        means = []
        stds = []

        for metric in metrics:
                df_path = fname + metric + ".csv"
                df = pd.read_csv(df_path)
                variances = df.groupby('subject').agg('var')
                std = sqrt(variances['similarity'].sum())
                mean = df.groupby('subject').agg('mean')['similarity'].sum()
                means.append(mean)
                stds.append(std)

        return metrics, means, stds



def compareOursWithLegacy():

	# preprocess the data
	# ------------------
	bids_base = '/media/nexus/storage2/ni_data/christian_bids_data/bids/'
	template = "/home/nexus/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii"

	bruker(bids_base,
	       	"mouse",
	       # comma is important since otherwise tuple instead of dict
	       	functional_match={'acquisition':['EPIlowcov'],},
	       	structural_match={'acquisition':['TurboRARElowcov'],},
	       	actual_size=True,
	       	functional_registration_method="composite",
	       	negative_contrast_agent=True,
	       	keep_work=True,
	       	out_dir="preprocessing_ours"
		)

	reg_cc(path=path + "preprocessing_ours/generic/", save = "./f_reg_quality_ours", template=template, autofind=True)

	legacy_bruker(bids_base,
	       "mouse",
	       # comma is important since otherwise tuple instead of dict
	       functional_match={'acquisition':['EPIlowcov'],},
	       structural_match={'acquisition':['TurboRARElowcov'],},
	       negative_contrast_agent=True,
	       keep_work=True,
	       out_dir="preprocessing_legacy"
	       )

	reg_cc(path=path + "preprocessing_legacy/generic/", save = "./f_reg_quality_legacy", template=template, autofind=True)

        # TODO: plotting
	metrics, means, stds = evaluateMetrics(fname="./f_reg_quality_ours")
	metrics, means, stds = evaluateMetrics(fname="./f_reg_quality_legacy")
