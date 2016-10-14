import os
import nibabel
from nilearn import image, plotting
import pandas as pd
import numpy as np
from nilearn.input_data import NiftiLabelsMasker
import nipype.interfaces.io as nio

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
plt.style.use('ggplot')

def plot_timecourses(parcellation="/home/chymera/NIdata/templates/roi/ds_QBI_vze_chr.nii.gz", condition=["ERC_ofM"], subject=["5502"], scan_type=["EPI_CBV_alej"]):
	datasource = nio.DataGrabber(infields=["condition","subject","scan_type"], outfields=["nii_data", "delay_file", "stimulation_file"], sort_filelist = True)
	datasource.inputs.base_directory = "/home/chymera/NIdata/ofM.erc/level1"
	datasource.inputs.template = '*'
	datasource.inputs.field_template = dict(
		nii_data='bruker_preprocessing/_condition_%s_subject_%s/_scan_type_%s/functional_bandpass/*.nii.gz',
		delay_file='bruker_preprocessing/_condition_%s_subject_%s/_scan_type_%s/timing_metadata/_report/report.rst',
		stimulation_file='first_level/_condition_%s_subject_%s/_scan_type_%s/specify_model/_report/report.rst'
		)
	datasource.inputs.template_args = dict(
		nii_data=[
			['condition','subject','scan_type']
			],
		delay_file=[
			['condition','subject','scan_type']
			],
		stimulation_file=[
			['condition','subject','scan_type']
			]
		)
	datasource.inputs.condition = ['ERC_ofM']
	datasource.inputs.subject = ['5502']
	datasource.inputs.scan_type = ['EPI_CBV_alej']

	results = datasource.run()
	nii_data = results.outputs.stimulation_file
	print nii_data

	masker = NiftiLabelsMasker(labels_img=parcellation, standardize=True, memory='nilearn_cache', verbose=5)

	time_series = masker.fit_transform("/home/chymera/NIdata/ofM.erc/level1/bruker_preprocessing/_condition_ERC_ofM_subject_5502/_scan_type_EPI_CBV_alej/functional_bandpass/corr_7_trans_filt.nii.gz").T

	region_assignments = pd.read_csv("/home/chymera/NIdata/templates/roi/QBI_vze_chr.csv", index_col=["ID"])

	for i in [10,11]:
		plt.plot(time_series[i], label=region_assignments.get_value(i, "acronym"))
	plt.legend()

# def plot_timecourse(file_path, roi_path=None, roi_number=None):

def plot_fsl_design(file_path):
	df = pd.read_csv(file_path, skiprows=5, sep="\t", header=None, names=[1,2,3,4,5,6], index_col=False)
	print(df)
	df.plot()

def plot_stim_design(file_path,stim):
	if isinstance(stim,str):
		from nipype.interfaces.base import Bunch
		match_string='* output : '
		with open(stim) as subject_info_report:
			for line in subject_info_report:
				if line[:11] == match_string:
					_, bunch_string = line.split(match_string)
					bunch=eval(bunch_string[1:-2])
					break
		durations=bunch.durations
		onsets=bunch.onsets
	elif isinstance(stim,dict):
		durations = stim["durations"]
		onsets = stim["onsets"]

	df = pd.read_csv(file_path, skiprows=5, sep="\t", header=None, names=[1,2,3,4,5,6], index_col=False)
	fig, ax = plt.subplots(figsize=(6,4) , facecolor='#eeeeee', tight_layout=True)
	for d, o in zip(durations, onsets):
		d = int(d[0])
		o = int(o[0])
		ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)
		plt.hold(True)
	ax = df.plot(ax=ax)
	#remove bottom and top small tick lines
	plt.tick_params(axis='x', which='both', bottom='off', top='off', left='off', right='off')
	plt.tick_params(axis='y', which='both', bottom='off', top='off', left='off', right='off')

# def plot_model(model_file):


if __name__ == '__main__':
	# plot_nii("/home/chymera/FSL_GLM_work/GLM/_measurement_id_20151103_213035_4001_1_1/functional_cutoff/6_restore_maths.nii.gz", (-50,20))
	# plot_fsl_design("/home/chymera/NIdata/ofM.dr/level1/first_level/_condition_ofM_subject_4001/modelgen/run0.mat")
	# stim = {"durations":[[20.0], [20.0], [20.0], [20.0], [20.0], [20.0]], "onsets":[[172.44299999999998], [352.443], [532.443], [712.443], [892.443], [1072.443]]}
	# plot_stim_design("/home/chymera/level1/first_level/_condition_ERC_ofM_subject_5503/_scan_type_T2_TurboRARE/_scan_type_EPI_CBV_alej/modelgen/run0.mat",stim)
	# plot_stim_design(
		# "/home/chymera/run0_dg.mat",
		# "/home/chymera/report_dg.rst"
		# )

	# from itertools import product
	# for i,j in product(["level2_dgamma_blurxy56","level2_dgamma_blurxy56n"],["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]):
	# 	plot_stat_map(stat_map="/home/chymera/NIdata/ofM.dr/GLM/"+i+"/_category_multi_"+j+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz", cbv=True, save_as="/home/chymera/"+i+"_"+j+".png", cut_coords=(-50,8,45))

	# for i in ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]:
	# 	plot_stat_map(stat_map="/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy56/_category_multi_"+i+"/flameo/mapflow/_flameo0/stats/tstat1.nii.gz", cbv=True, save_as="/home/chymera/"+i+".pdf", cut_coords=(-49,8,43), threshold=3)

	# plot_stat_map("/home/chymera/NIdata/ofM.dr/GLM/level2_dgamma_blurxy56/_category_multi_ofM_cF2/flameo/mapflow/_flameo0/stats/tstat1.nii.gz", cbv=True, save_as="/home/chymera/ofM_cF2.pdf", cut_coords=(-49,8,43), threshold=3, interpolation="gaussian")

	# plot_model()

	plt.show()
