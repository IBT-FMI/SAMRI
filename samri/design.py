import numpy as np
from scipy import stats, signal
import matplotlib.pyplot as plt


def get_irf():
	my_x = np.linspace(0,100,100)
	my_y = stats.beta.pdf(my_x/100, 2, 5)
	my_z = np.linspace(0,0,100)
	my_z[:20]=1

	irf = signal.deconvolve(my_y, my_z)[1]
	block_response = signal.convolve(irf,my_z)
	basis_function = signal.deconvolve(block_response, my_z)[1] #should be equal to irf

	return irf

def plot_design(
	irf,
	reps = 8,
	stim = 20,
	period = 150,
	onset = 192,
	post = 150,
	lowpass =0.006,
	):

	design = np.zeros(onset)
	for i in range(reps):
		rep = np.append(np.ones(stim),np.zeros(period-stim))
		design = np.append(design,rep)
	design = np.append(design,np.zeros(post))
	total = len(design)

	x = np.linspace(0,total,total)

	fig, ax = plt.subplots(2, 3)
	ax[0,0].plot(x, design,'c-', lw=3, alpha=0.5, label='gamma pdf')

	regressor = signal.convolve(design, irf)
	regressor = regressor/regressor.max()
	ax[0,2].plot(x, regressor[:total],'r-', lw=3, alpha=0.5, label='gamma pdf')

	ax[0,1].plot(range(len(irf)), irf,'r-', lw=3, alpha=0.5, label='gamma pdf')

	f, Pxx_den = signal.periodogram(design, 1)
	ax[1,0].plot(f, Pxx_den,'b-', lw=2, alpha=0.5, label='gamma pdf')
	initial_power = get_power(Pxx_den, f, lowpass)

	f, Pxx_den = signal.periodogram(irf, 1)
	ax[1,1].plot(f, Pxx_den,'b-', lw=2, alpha=0.5, label='gamma pdf')

	f, Pxx_den = signal.periodogram(regressor, 1)
	ax[1,2].plot(f, Pxx_den,'b-', lw=2, alpha=0.5, label='gamma pdf')
	resulting_power = get_power(Pxx_den, f, lowpass)

	print(initial_power, resulting_power, initial_power-resulting_power)

def get_power(Pxx_den, f, lowpass=0):
	lowpass_ix = 0
	for ix,i in enumerate(f):
		if i > lowpass:
			lowpass_ix = ix
			break
	power = np.sum(Pxx_den[lowpass_ix:])
	return power


if __name__ == '__main__':
	irf = get_irf()
	plot_design(irf)
	plt.show()
