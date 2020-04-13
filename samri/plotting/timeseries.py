import nibabel as nib
import nipype.interfaces.io as nio
import numpy as np
import pandas as pd
from copy import deepcopy
from matplotlib import rcParams
from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker, NiftiMasker
from os import path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker

from samri.plotting import maps, utilities
from samri.plotting.utilities import QUALITATIVE_COLORSET

def visualize(fsl_basis_set):
	df = pd.read_csv(fsl_basis_set, sep='  ', header=None, index_col=False)
	df.plot()
	plt.show()

def plot_fsl_design(file_path):
	"""Returns a plot of a Dataframe resulted from a csv file.

	Parameters
	----------
	file_path : str
		The path and the filename to obtain the csv from.

	Returns
	-------
	axes : matplotlib.AxesSubplot or np.array of them.
	"""

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
	ax = df.plot(ax=ax)
	#REMove bottom and top small tick lines
	plt.tick_params(axis='x', which='both', bottom='off', top='off', left='off', right='off')
	plt.tick_params(axis='y', which='both', bottom='off', top='off', left='off', right='off')

def roi_based(
	beta_filename=None,
	events_filename=None,
	ts_filename=None,
	design_filename=None,
	substitutions={},
	ax=None,
	design_color="c",
	ts_color="r",
	flip=False,
	design_len=None,
	melodic_hit=None,
	plot_design_regressors=[0,1,2],
	roi=None,
	save_as='',
	scale_design=1,
	ylabel='Arbitrary Units',
	):
	"""Plot timecourses and design for measurements. should be deprecated in favour of multi.

	Parameteres
	-----------

	beta_filename : str, optional
		Path to beta (a.k.a. COPE) file, which represents the loading of the design matrix to voxelwise timecourses.
	events_filename : str, optional
		Path to events file, which conforms to the BIDS specification and contains a tab-separated table of stimulation events.
	ts_filename : str, optional
		Path to NIfTI timeseries (4D file) which contains the voxelwise timecourses, as they have been passed on to the GLM.
		It is very important that this is the exact same file which is forwarded to the GLM, as a timecourse file e.g. not subjected to a bandpass filter will not visually match the beta loading obtained by fitting a GLM to the same timecourse file after it was subjected to a bandpass filter.
	design_filename : str, optional
		Path to a mat file containing an ascii matrix for design, as outputted by FSL's `feat_model`.
	substitutions : dict, optional
		Dictionary which, if provided will be applied to formattable Python strings passed to the `beta_filename`, `events_filename`, `ts_filename`, and `design_filename` parameters (e.g. "part_of_path-{replace_this}-other_part_of_path") in order to replace occurrences of each key with its respective value pair.
	flip : bool, optional
		Whether to flip the plot by 90 degrees (plotting in "portrait" rather than "landscape" mode, as it were).
	roi : str, optional
		Path to a NIfTI mask file which determines based on what region to extract summaries from the voxelwise inputs.
	save_as : str, optional
		Path to save the plot under.
	ylabel : str, optional
		Text to place on the y label.
	"""

	if not ax:
		_, ax = plt.subplots(facecolor='#eeeeee', tight_layout=True)

	if roi:
		if isinstance(roi, str):
			roi = path.abspath(path.expanduser(roi))
			roi = nib.load(roi)
		if ts_filename:
			ts_file = path.expanduser(ts_filename.format(**substitutions))
			ts_file = nib.load(ts_file)
			masker = NiftiMasker(mask_img=roi, target_affine=ts_file.affine)
			final_time_series = masker.fit_transform(ts_file)
			final_time_series = final_time_series.T
			final_time_series = np.mean(final_time_series, axis=0)
			if flip:
				ax.plot(final_time_series, np.arange(len(final_time_series)), color=ts_color)
				ax.set_ylim([0,len(final_time_series)])
			else:
				ax.plot(final_time_series, color=ts_color)
				ax.set_xlim([0,len(final_time_series)])
	else:
		if ts_filename:
			ts_file = path.expanduser(ts_filename.format(**substitutions))
			ts_file = nib.load(ts_file)
			final_time_series = ts_file.get_data()
			final_time_series = np.mean(final_time_series, axis=0)
			final_time_series = np.mean(final_time_series, axis=0)
			final_time_series = np.mean(final_time_series, axis=0)
			if flip:
				ax.plot(final_time_series, np.arange(len(final_time_series)), color=ts_color)
				ax.set_ylim([0,len(final_time_series)])
			else:
				ax.plot(final_time_series, color=ts_color)
				ax.set_xlim([0,len(final_time_series)])

	if design_filename:
		design_file = path.expanduser(design_filename.format(**substitutions))
		design_df = pd.read_csv(design_file, skiprows=5, sep="\t", header=None, index_col=False)
		if beta_filename and roi:
			beta_file = path.expanduser(beta_filename.format(**substitutions))
			beta_file = nib.load(beta_file)
			masker = NiftiMasker(mask_img=roi, target_affine=beta_file.affine)
			roi_betas = masker.fit_transform(beta_file).T
			design_df = design_df*np.mean(roi_betas)
		for i in plot_design_regressors:
			regressor = design_df[[i]].values.flatten()
			if flip:
				ax.plot(regressor.T*scale_design, np.arange(len(regressor)), lw=rcParams['lines.linewidth']*2, color=design_color)
			else:
				ax.plot(regressor*scale_design, lw=rcParams['lines.linewidth']*2, color=design_color)
		if flip:
			ax.set_ylim([0,len(regressor)])
		else:
			ax.set_xlim([0,len(regressor)])

	if events_filename:
		events_file = path.expanduser(events_filename.format(**substitutions))
		events_df = pd.read_csv(events_file, sep="\t")
		for d, o in zip(events_df["duration"], events_df["onset"]):
			d = round(d)
			o = round(o)
			if flip:
				ax.axhspan(o,o+d, facecolor="cyan", alpha=0.15)
			else:
				ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)
		if design_len:
			if flip:
				ax.set_ylim([0,design_len])
			else:
				ax.set_xlim([0,design_len])

	# Very deprecated, we keep this around since it is not yet clear whether we will remove or reimplement this feature.
	if melodic_hit:
		pass
		melodic_file = "~/ni_data/ofM.dr/20151208_182500_4007_1_4/melo10/report/t4.txt"
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
		ax.set_ylabel(ylabel)
		ax.set_xlabel('Time [TR]')

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		plt.savefig(save_as)
	return ax

def multi(timecourses,
	designs=[],
	events_dfs=[],
	subplot_titles=[],
	colors=QUALITATIVE_COLORSET,
	quantitative=True,
	save_as="",
	samri_style=True,
	ax_size=[28,4],
	unit_ticking=False,
	x_label="TR [1s]",
	model_line_multiplier=2,
	scale_x=False,
	):
	"""Plot multiple timecourses on an intelligently scaled multi-axis figure.

	Parameters
	----------

	timecourses : list or pandas.DataFrame
		Timecourses to plot.
		The value can be a list of lists of floats (in which case every list gives a timecourse to plot separately);
		or a list of dictionaries, every one of which has strings as keys and lists of floats as values (in which case each dictionary contains one or multiple timeseries to be plotted on the same axis - and labelled according to the respective keys);
		or a list of `pandas.DataFrame` objects (in which case each DataFrame is plotted on a new axis);
		or a `pandas.DataFrame` object (in which case the object is broken apart into a list of DataFrames by the values in the column specified by a string `subplot_titles` value - and the `subplot_tiles` value will be set to the values in the selected column).
	subplot_titles : list or str, optional
		The titles to assign to the individual plots.
		For compactness, this title is actually assigned to the y-label field, and can be placed left or right of the plot (corresponding to `False` or `True` values of the `quantitative` attribute, respectively)
	ax_size : list, optional
		A list of two floats or integers, giving the width and height of the constituent axes of the figures.
	"""

	if isinstance(timecourses, pd.DataFrame):
		if subplot_titles in ['subject','session','acquisition','task']:
			timecourses_ = []
			subplot_titles_ = []
			values = list(timecourses[subplot_titles].unique())
			for value in values:
				timecourse = timecourses[timecourses[subplot_titles]==value]
				timecourse = deepcopy(timecourse)
				timecourses_.append(timecourse)
				subplot_titles_.append(value)
			timecourses = timecourses_
			subplot_titles = subplot_titles_
		else:
			timecourses = [timecourses,]

	if samri_style:
		this_path = path.dirname(path.realpath(__file__))
		plt.style.use(path.join(this_path,"samri.conf"))

	if len(timecourses) > 1:
		ncols = 2
		max_rowspan = int(np.ceil((len(timecourses) / float(ncols))))
		min_rowspan = int(np.floor((len(timecourses) / float(ncols))))
		fig, axes = plt.subplots(figsize=(ax_size[0]*ncols,ax_size[1]*max_rowspan), nrows=max_rowspan*min_rowspan, ncols=ncols)
		xlabel_positive = [(i*max_rowspan)-1 for i in range(1,ncols)]
		xlabel_positive.append(len(timecourses)-1)
		max_ylim = [0,0]


		for ix, timecourse in enumerate(timecourses):
			col = ix // max_rowspan
			row = ix % max_rowspan
			if col+1 == ncols:
				ax = plt.subplot2grid((max_rowspan*min_rowspan,ncols), (row*max_rowspan, col), rowspan=max_rowspan)
			else:
				ax = plt.subplot2grid((max_rowspan*min_rowspan,ncols), (row*min_rowspan, col), rowspan=min_rowspan)

			#Add plotting elements as available
			try:
				events_df = events_dfs[ix]
			except:
				pass
			else:
				if isinstance(events_df,str):
					events_file = path.expanduser(events_df)
					events_df = pd.read_csv(events_file, sep="\t")
				for d, o in zip(events_df["duration"], events_df["onset"]):
					d = round(d)
					o = round(o)
					ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)

			if isinstance(timecourse, pd.DataFrame):
				timecourse.plot(ax=ax)
			elif isinstance(timecourse[0], int) or isinstance(timecourse[0], float) or isinstance(timecourse[0], np.float32):
				ax.plot(timecourse, lw=rcParams['lines.linewidth'])
			else:
				for timecourse_variant in timecourse:
					if isinstance(timecourse_variant, dict):
						ax.plot(list(timecourse_variant.values())[0],
							lw=rcParams['lines.linewidth'],
							label=list(timecourse_variant.keys())[0],
							)
					else:
						try:
							ax.plot(timecourse_variant.values,
								lw=rcParams['lines.linewidth'],
								)
						except:
							pass

			try:
				design = designs[ix]
			except:
				pass
			else:
				if isinstance(design, pd.DataFrame):
					for column in design:
						ax.plot(design[column], lw=rcParams['lines.linewidth']*model_line_multiplier)
				else:
					ax.plot(design, lw=rcParams['lines.linewidth']*model_line_multiplier)

			if not ix in xlabel_positive:
				plt.setp(ax.get_xticklabels(), visible=False)
			if quantitative:
				ax_ = ax.twinx()
				ax_.yaxis.set_label_position("right")
				ax_.yaxis.grid(False)
				ax_.set_yticks([])
				try:
					subplot_title = subplot_titles[ix]
				except:
					pass
				else:
					ax_.set_ylabel(subplot_title)
			else:
				ax.yaxis.grid(False)
				ax.set_yticks([])
				try:
					subplot_title = subplot_titles[ix]
				except:
					pass
				else:
					ax.set_ylabel(subplot_title)

			ax.tick_params(axis='y',)

			if unit_ticking:
				ax.xaxis.set_ticks_position('both')
				loc_maj = plticker.MultipleLocator(base=10.0)
				ax.xaxis.set_major_locator(loc_maj)
				loc_min = plticker.MultipleLocator(base=1.0)
				ax.xaxis.set_minor_locator(loc_min)

			ax.set_xlim([0,len(timecourse)])
			if scale_x:
				from matplotlib import ticker
				if isinstance(timecourse[0], int) or isinstance(timecourse[0], float) or isinstance(timecourse[0], np.float32):
					ticks_x = ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x/scale_x))
				else:
					ticks_x = ticker.FuncFormatter(lambda x, pos: '{0:g}'.format(x/scale_x[ix]))
				ax.xaxis.set_major_formatter(ticks_x)
	else:
		fig, ax = plt.subplots(facecolor='#eeeeee')

		try:
			timecourse = timecourses[0]
		except:
			pass
		else:
			if isinstance(timecourse, pd.DataFrame):
				timecourse.plot(ax=ax)
			else:
				ax.plot(timecourse, lw=rcParams['lines.linewidth']*1.5, color=colors[0], alpha=1)

		subplot_title = subplot_titles[0]

		# Add plot elements as appropriate
		try:
			design = designs[0]
		except:
			pass
		else:
			for ix, i in enumerate(design):
				try:
					iteration_color=colors[ix+1]
				except IndexError:
					pass
				ax.plot(design[ix], lw=rcParams['lines.linewidth']*2, color=iteration_color, alpha=1)

		try:
			events_df = events_dfs[0]
		except:
			pass
		else:
			for d, o in zip(events_df["duration"], events_df["onset"]):
				d = round(d)
				o = round(o)
				ax.axvspan(o,o+d, facecolor="cyan", alpha=0.15)

		if not quantitative:
			ax.yaxis.grid(False)
			ax.set_yticks([])
		ax.set_xlim([0,len(timecourse)])
		plt.title(subplot_title)
		ax.set_xlabel(x_label)
		if unit_ticking:
			ax.xaxis.set_ticks_position('both')
			loc_maj = plticker.MultipleLocator(base=10.0)
			ax.xaxis.set_major_locator(loc_maj)
			loc_min = plticker.MultipleLocator(base=1.0)
			ax.xaxis.set_minor_locator(loc_min)
	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		plt.savefig(save_as)

