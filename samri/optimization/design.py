# -*- coding: utf-8 -*-

import numpy as np
from scipy import stats, signal
import matplotlib.pyplot as plt
import matplotlib as mpl

plt.style.use(u'seaborn-darkgrid')
plt.style.use(u'ggplot')

def get_irf():
	my_x = np.linspace(0,100,100)
	my_y = stats.beta.pdf(my_x/100, 2, 5)
	my_z = np.linspace(0,0,100)
	my_z[:20]=1

	irf = signal.deconvolve(my_y, my_z)[1]
	block_response = signal.convolve(irf,my_z)
	basis_function = signal.deconvolve(block_response, my_z)[1] #should be equal to irf

	return irf/irf.sum()

def butter_highpass(cutoff, fs, order=5):
	nyq = 0.5 * fs
	normal_cutoff = cutoff / nyq
	b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)

	return b, a

def butter_highpass_filter(data, cutoff, fs, order=5):
	b, a = butter_highpass(cutoff, fs, order=order)
	y = signal.filtfilt(b, a, data)

	return y

def period_padded_period_filtered(irf, reps=8, stim=20, period=150, extra_padding=[42,0]):
	initial_power, resulting_power, power_loss, percent_loss = plot_design(irf, reps, stim, period,
		period+extra_padding[0],
		period+extra_padding[1],
		highpass=1./(2*period),
		)

	return initial_power, resulting_power, power_loss, percent_loss

def plot_design(
	irf,
	reps = 8,
	stim = 20,
	period = 150,
	onset = 192,
	post = 150,
	highpass =0.006,
	irfcolor="#111111",
	stimcolor="#00cccc",
	regressorcolor="#cc5200",
	):

	design = np.zeros(onset)
	for i in range(reps):
		rep = np.append(np.ones(stim),np.zeros(period-stim))
		design = np.append(design,rep)
	design = np.append(design,np.zeros(post))
	total = len(design)

	x = np.linspace(0,total,total)
	convoluted = signal.convolve(design, irf)
	convoluted = convoluted[:total]
	filtered = butter_highpass_filter(convoluted, highpass, 1)

	fig, ax = plt.subplots(2, 4, figsize=(15,8))

	ax[0,0].plot(range(len(irf)), irf, irfcolor, lw=2, alpha=0.8, label='gamma pdf')
	ax[0,0].yaxis.get_major_formatter().set_powerlimits((0, 1))
	ax[0,0].set_xlabel("time [s]")
	ax[0,0].set_title("IRF", color=irfcolor)

	ax[0,1].plot(x, design, stimcolor, lw=2, alpha=0.8, label='gamma pdf')
	plt.setp(ax[0,1].xaxis.get_majorticklabels(), rotation=30, ha="right")
	ax[0,1].set_title("Stimulaton", color=stimcolor)

	ax[0,2].plot(x, convoluted, regressorcolor, lw=2, alpha=0.8, label='gamma pdf')
	plt.setp(ax[0,2].xaxis.get_majorticklabels(), rotation=30, ha="right")
	ax[0,2].set_title(u"Stimulation × IRF", color=regressorcolor)

	ax[0,3].plot(x, filtered, regressorcolor, lw=2, alpha=0.8, label='gamma pdf')
	plt.setp(ax[0,3].xaxis.get_majorticklabels(), rotation=30, ha="right")
	ax[0,3].set_title(u"Stimulation × IRF × highpass", color=regressorcolor)

	f_design, Pxx_den_design = signal.periodogram(design, 1, "barthann")
	ax[1,1].plot(f_design, Pxx_den_design, stimcolor, lw=2, alpha=0.5, label='gamma pdf')
	ax[1,1].set_xscale("log")

	f_irf, Pxx_den_irf = signal.periodogram(irf, 1, "barthann")
	ax[1,0].plot(f_irf, Pxx_den_irf, irfcolor, lw=2, alpha=0.5, label='gamma pdf')
	ax[1,0].set_xscale("log")
	ax[1,0].yaxis.get_major_formatter().set_powerlimits((0, 1))
	ax[1,0].set_xlim(ax[1,1].get_xlim())
	ax[1,0].set_xlabel("frequency [Hz]")

	f_convoluted, Pxx_den_convoluted = signal.periodogram(convoluted, 1, "barthann")
	ax[1,2].plot(f_convoluted, Pxx_den_convoluted, regressorcolor, lw=2, alpha=0.5, label='gamma pdf')
	ax[1,2].set_xscale("log")

	f_filtered, Pxx_den_filtered = signal.periodogram(filtered, 1, "barthann")
	ax[1,3].plot(f_filtered, Pxx_den_filtered, regressorcolor, lw=2, alpha=0.5, label='gamma pdf')
	ax[1,3].set_xscale("log")

	initial_power = get_power(Pxx_den_design, f_design)
	resulting_power = get_power(Pxx_den_filtered, f_filtered)
	power_loss = initial_power-resulting_power
	percent_loss = power_loss/initial_power

	return initial_power, resulting_power, power_loss, percent_loss

def get_power(Pxx_den, f, highpass=0):
	highpass_ix = 0
	for ix,i in enumerate(f):
		if i > highpass:
			highpass_ix = ix
			break
	power = np.sum(Pxx_den[highpass_ix:])
	return power

if __name__ == '__main__':
	irf = get_irf()
	print(period_padded_period_filtered(irf, 8, 20, 150))
	# print(period_padded_period_filtered(irf, 6, 20, 180))
	plt.show()
