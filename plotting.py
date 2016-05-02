import os
import nibabel
from nilearn import image, plotting
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
plt.style.use('ggplot')
# plt.rcParams['font.size']=14
plt.rcParams['xtick.labelsize']="x-large"
plt.rcParams['ytick.labelsize']="x-large"

def plot_nii(file_path, slices):
	plotting.plot_anat(file_path, cut_coords=slices, display_mode="y", annotate=False, draw_cross=False)

# def plot_timecourse(file_path, roi_path=None, roi_number=None):

def plot_fsl_design(file_path):
	df = pd.read_csv(file_path, skiprows=5, sep="\t", header=None, names=[1,2,3,4,5,6], index_col=False)
	print(df)
	df.plot()

def plot_stim_design(file_path,stim):
	df = pd.read_csv(file_path, skiprows=5, sep="\t", header=None, names=[1,2,3,4,5,6], index_col=False)
	fig, ax = plt.subplots(figsize=(6,4) , facecolor='#eeeeee', tight_layout=True)
	for d, o in zip(stim["durations"], stim["onsets"]):
		d = int(d[0])
		o = int(o[0])
		ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)
		plt.hold(True)
	ax = df.plot(ax=ax)
	#remove bottom and top small tick lines
	plt.tick_params(axis='x', which='both', bottom='off', top='off', left='off', right='off')
	plt.tick_params(axis='y', which='both', bottom='off', top='off', left='off', right='off')

if __name__ == '__main__':
	# plot_nii("/home/chymera/FSL_GLM_work/GLM/_measurement_id_20151103_213035_4001_1_1/structural_cutoff/6_restore_maths.nii.gz", (-50,20))
	# plot_fsl_design("/home/chymera/NIdata/ofM.dr/level1/first_level/_condition_ofM_subject_4001/modelgen/run0.mat")
	stim = {"durations":[[20.0], [20.0], [20.0], [20.0], [20.0], [20.0]], "onsets":[[172.44299999999998], [352.443], [532.443], [712.443], [892.443], [1072.443]]}
	plot_stim_design("/home/chymera/NIdata/ofM.dr/level1/first_level/_condition_ofM_subject_4001/modelgen/run0.mat",stim)
	plt.show()
