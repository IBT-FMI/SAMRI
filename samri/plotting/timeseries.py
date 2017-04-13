import os
import nibabel
import pandas as pd
import numpy as np
from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker, NiftiMasker
import nipype.interfaces.io as nio

from matplotlib import rcParams

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def plot_fsl_design(file_path):
	df = pd.read_csv(file_path, skiprows=5, sep="\t", header=None, names=[1,2,3,4,5,6], index_col=False)
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
	# fig, ax = plt.subplots(figsize=(6,4) , facecolor='#eeeeee', tight_layout=True)
	# for d, o in zip(durations, onsets):
	# 	d = int(d[0])
	# 	o = int(o[0])
	# 	ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)
	# 	plt.hold(True)
	ax = df.plot(ax=ax)
	#remove bottom and top small tick lines
	plt.tick_params(axis='x', which='both', bottom='off', top='off', left='off', right='off')
	plt.tick_params(axis='y', which='both', bottom='off', top='off', left='off', right='off')

def roi_based(substitutions,
	beta_file_template=None,
	events_file_template=None,
	ts_file_template=None,
	design_file_template=None,
	plot_design_regressors=[0,1,2],
	roi=None,
	melodic_hit=None,
	flip=False,
	design_len=None,
	color="r",
	scale_design=1,
	):
	"""Plot timecourses and design for measurements. should be deprecated in favour of multi"""

	fig, ax = plt.subplots(figsize=(6,4) , facecolor='#eeeeee', tight_layout=True)

	if roi:
		roi = os.path.expanduser(roi)
		masker = NiftiMasker(mask_img=roi)
		if ts_file_template:
			ts_file = os.path.expanduser(ts_file_template.format(**substitutions))
			final_time_series = masker.fit_transform(ts_file).T
			final_time_series = np.mean(final_time_series, axis=0)
			if flip:
				ax.plot(final_time_series, np.arange(len(final_time_series)))
				ax.set_ylim([0,len(final_time_series)])
			else:
				ax.plot(final_time_series)
				ax.set_xlim([0,len(final_time_series)])

	if design_file_template:
		design_file = os.path.expanduser(design_file_template.format(**substitutions))
		design_df = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
		if beta_file_template and roi:
			beta_file = os.path.expanduser(beta_file_template.format(**substitutions))
			roi_betas = masker.fit_transform(beta_file).T
			design_df = design_df*np.mean(roi_betas)
		for i in plot_design_regressors:
			regressor = design_df[[i]].values.flatten()
			if flip:
				ax.plot(regressor.T*scale_design, np.arange(len(regressor)), lw=rcParams['lines.linewidth']*2, color=color)
			else:
				ax.plot(regressor*scale_design, lw=rcParams['lines.linewidth']*2, color=color)
		if flip:
			ax.set_ylim([0,len(regressor)])
		else:
			ax.set_xlim([0,len(regressor)])

	if events_file_template:
		events_file = os.path.expanduser(events_file_template.format(**substitutions))
		events_df = pd.read_csv(events_file, sep="\t")
		for d, o in zip(events_df["duration"], events_df["onset"]):
			d = round(d)
			o = round(o)
			if flip:
				ax.axhspan(o,o+d, facecolor="cyan", alpha=0.15)
			else:
				ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)
			plt.hold(True)
		if design_len:
			if flip:
				ax.set_ylim([0,design_len])
			else:
				ax.set_xlim([0,design_len])

	if melodic_hit:
		melodic_file = "/home/chymera/ni_data/ofM.dr/20151208_182500_4007_1_4/melo10/report/t4.txt"
		melodic = np.loadtxt(melodic_file)
		if flip:
			melodic = melodic.T
		ax.plot(melodic)

	if flip:
		ax.invert_yaxis()
		plt.xticks(rotation=90)
		ax.locator_params(nbins=5, axis='x')
		ax.set_ylabel('Time [TR]', rotation=270, fontsize="smaller", va="center")
	else:
		ax.set_xlabel('Time [TR]')

	return ax

def multi(timecourses, designs, stat_maps, events_dfs, subplot_titles,
	figure="maps",
	):
	if figure == "maps":
		maps.stat(stat_maps, template="~/ni_data/templates/ds_QBI_chr.nii.gz", threshold=0.1, interpolation="gaussian", subplot_titles=subplot_titles)
	elif figure == "timecourses":
		ncols = 2
		#we use inverse floor division to get the ceiling
		max_rows = (len(timecourses) // ncols) + 1
		min_rows = len(timecourses) % max_rows
		fig, axes = plt.subplots(figsize=(10*max_rows,7*ncols), facecolor='#eeeeee', nrows=max_rows*min_rows, ncols=ncols)
		xlabel_positive = [(i*max_rows)-1 for i in range(1,ncols)]
		xlabel_positive.append(len(timecourses)-1)
		max_ylim = [0,0]

		for ix, timecourse in enumerate(timecourses):
			timecourse = timecourses[ix]
			design = designs[ix]
			events_df = events_dfs[ix]
			subplot_title = subplot_titles[ix]

			col = ix // max_rows
			row = ix % max_rows
			if col+1 == ncols:
				ax = plt.subplot2grid((max_rows*min_rows,ncols), (row*max_rows, col), rowspan=max_rows)
			else:
				ax = plt.subplot2grid((max_rows*min_rows,ncols), (row*min_rows, col), rowspan=min_rows)
			for d, o in zip(events_df["duration"], events_df["onset"]):
				d = round(d)
				o = round(o)
				ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)
				plt.hold(True)
			ax.plot(timecourse, lw=rcParams['lines.linewidth']/4)
			ax.plot(design[0])
			if not ix in xlabel_positive:
				plt.setp(ax.get_xticklabels(), visible=False)
			current_ylim = ax.get_ylim()
			ax.yaxis.grid(False)
			ax.set_xlim([0,len(timecourse)])
			ax.set_yticks([])
			ax.set_ylabel(subplot_title)


if __name__ == '__main__':
	# plot_fsl_design("/home/chymera/ni_data/ofM.dr/level1/first_level/_condition_ofM_subject_4001/modelgen/run0.mat")
	# stim = {"durations":[[20.0], [20.0], [20.0], [20.0], [20.0], [20.0]], "onsets":[[172.44299999999998], [352.443], [532.443], [712.443], [892.443], [1072.443]]}
	# plot_stim_design("/home/chymera/level1/first_level/_condition_ERC_ofM_subject_5503/_scan_type_T2_TurboRARE/_scan_type_EPI_CBV_alej/modelgen/run0.mat",stim)
	# plot_stim_design(
		# "/home/chymera/run0_dg.mat",
		# "/home/chymera/report_dg.rst"
		# )

	# plt.style.use(u'seaborn-darkgrid')
	# plt.style.use(u'ggplot')
	#
	roi_based(
		roi="~/ni_data/templates/roi/f_dr_chr_bin.nii.gz",
		events_file_template="~/ni_data/ofM.dr/preprocessing/{workflow}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}_events.tsv",
		beta_file_template="~/ni_data/ofM.dr/l1/{workflow}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_trial-{scan}_cope.nii.gz",
		ts_file_template="~/ni_data/ofM.dr/preprocessing/{workflow}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
		design_file_template="~/ni_data/ofM.dr/l1/{workflow}_work/_subject_session_scan_{subject}.{session}.{scan}/modelgen/run0.mat",
		substitutions={"workflow":"composite","subject":4007,"session":"ofM_cF2","scan":"EPI_CBV_jb_long"},
		scale_design=3,
		)

	# roi_based(subject=4007, roi="dr", workflows=["generic"], melodic_hit=5)
	# roi_based(subject=4001, roi="dr", workflows=["generic"])
	# roi_based(subject=4012, workflows=["norealign","generic"], melodic_hit=5)
	# roi_based(subject=4012, session="ofM_cF1", workflows=["norealign","generic"])
	plt.show()
