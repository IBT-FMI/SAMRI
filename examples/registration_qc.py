import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from os import path
from samri.plotting.aggregate import registration_qc
from samri.typesetting import inline_anova
from samri.development import reg_cc
from samri.pipelines.reposit import bru2bids
from samri.pipelines.preprocess import generic, legacy
from math import sqrt
import matplotlib.pyplot as plt
import numpy as np



def evaluateQuality():
	data_dir = path.join(path.dirname(path.realpath(__file__)),"../example_data/")
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


	# plotting variance results for different metrics
	# TODO: warum MI = 0?

	metrics = ['CC', 'MI', 'GC']
	means = []
	stds = []

	for metric in metrics:

		df_path = path.join('/media/nexus/storage/coding/github/SAMRI/',"f_reg_quality_"+metric+".csv")
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


def evaluateMetrics(fname = "./f_reg_quality",
		metrics = ['CC', 'MI', 'GC'],
		):

	means = []
        stds = []

        for metric in metrics:
                df_path = fname + "_" +  metric + ".csv"
                df = pd.read_csv(df_path)
                variances = df.groupby('subject').agg('var')
                std = sqrt(variances['similarity'].sum())
                mean = df.groupby('subject').agg('mean')['similarity'].sum()
                means.append(mean)
                stds.append(std)

        return metrics, means, stds


def preprocessData(bids_base, template, out_dir):

	#generic(bids_base,
	 #      	"mouse",
	  #     # comma is important since otherwise tuple instead of dict
	   #    	functional_match={'acquisition':['EPIlowcov'],},
	     #  	structural_match={'acquisition':['TurboRARElowcov'],},
	    #   	actual_size=True,
	      # 	functional_registration_method="composite",
	       #	negative_contrast_agent=True,
	       	#keep_work=True,
	       	#out_dir=out_dir[0]
		#)

	legacy(bids_base,
	       "mouse",
	       # comma is important since otherwise tuple instead of dict
	       functional_match={'acquisition':['EPIlowcov'],},
	       structural_match={'acquisition':['TurboRARElowcov'],},
	       negative_contrast_agent=True,
	       keep_work=True,
	       out_dir=out_dir[1]
	       )


def compareOursWithLegacy(out_dirs, template, results_path = "./"):


	reg_cc(path =	out_dirs[0] + "/generic/", save = results_path + "f_reg_quality_ours", template=template, autofind=True)
	reg_cc(path =	out_dirs[1] + "/generic/", save = results_path + "f_reg_quality_legacy", template=template, autofind=True)

	metrics_ours, means_ours, stds_ours		= evaluateMetrics(fname=results_path + "f_reg_quality_ours", metrics=['CC', 'GC'])
	metrics_legacy, means_legacy, stds_legacy	= evaluateMetrics(fname=results_path + "f_reg_quality_legacy", metric = ['CC', 'GC'])

	return metrics_ours, means_ours, stds_ours, metrics_legacy, means_legacy, stds_legacy

def main():
	bids_base = '/media/nexus/storage2/ni_data/christian_bids_data/bids/'
	template = "/home/nexus/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii"
	out_dirs = [bids_base+'preprocessing/ours', bids_base+'preprocessing/legacy']

	preprocessData(bids_base, template, out_dirs)
	metrics_ours, means_ours, stds_ours, metrics_legacy, means_legacy, stds_legacy = compareOursWithLegacy(out_dirs, template)


	plotting = pd.DataFrame(np.vstack((stds_ours, stds_legacy)), columns = ['ours', 'legacy'])
        plotting = plotting.set_index(np.asarray(metrics).transpose())
        ax = plotting.plot(kind='bar', use_index=True, rot=90)
        ax.set_xlabel('Metric')
        ax.set_ylabel('Variance')
        fig = ax.get_figure()
        fig.savefig('VarianceOverMetric.png')


if __name__ == "__main__":
	main()
