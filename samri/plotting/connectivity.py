import numpy as np
import collections
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from numpy import genfromtxt
from os import path
from pandas import read_csv

def fix_labels_mapping_txt(labels,
		):

	ret = {}
	for idx, item in enumerate(labels):
		if(idx<14):
			continue
		ret[int(item.split()[0])] = " ".join(item.split()[7:])
	ret = collections.OrderedDict(sorted(ret.items()))
	ret = np.array(ret.items())[:,1]
	return ret

def fix_labels(labels,
	):

	#TODO: double check if no missing or no double
	ret = {}
	for label in labels:
		ret[int(label[1])] = label[0] + '_right'
		ret[int(label[2])] = label[0] + '_left'

	ret = collections.OrderedDict(sorted(ret.items()))
	ret = np.array(ret.items())[:,1]
	return ret

def plot_connectivity_matrix(correlation_matrix,
	figsize = (50,50),
	labels = '',
	save_as = '',
	):
	"""Plot correlation_matrix

	Parameters
	----------

	correlation_matrix : real matrix
	Path to correlation matrix as csv file.

	figsize : (int,int)
	Tupel defining plotsize.

	labels : str
	Path to csv file containing annotations for NIFTI atlas.

	"""

	#TODO: fomatting
	labels = path.abspath(path.expanduser(labels))
	# fix labels loaded from website (through templates.py)
	if('itksnap' in labels):
		with open(labels) as f:
			content = f.readlines()
		labels_np = fix_labels_mapping_txt(content)
	else:
		labels_np = read_csv(labels)
		labels_np = fix_labels(labels_np.as_matrix(['Structure','right label','left label']))

	if isinstance(correlation_matrix, str):
		correlation_matrix = path.abspath(path.expanduser(correlation_matrix))
		correlation_matrix = genfromtxt(correlation_matrix, delimiter=',')


	plt.figure(figsize=figsize)
	np.fill_diagonal(correlation_matrix, 0)

	plt.imshow(correlation_matrix,
		interpolation="nearest",
		cmap="RdBu_r",
		vmax=0.8,
		vmin=-0.8,
		aspect='auto'
		)
	x_ticks = plt.xticks(range(len(labels_np) - 1), labels_np[1:], rotation=90)
	y_ticks = plt.yticks(range(len(labels_np) - 1), labels_np[1:])
	plt.gca().yaxis.tick_left()
	cbar = plt.colorbar()
	cbar.ax.tick_params(labelsize=75)
	# plt.subplots_adjust(left=.01, bottom=.3, top=.99, right=.62)
	if(save_as):
		plt.savefig(path.abspath(path.expanduser(save_as)))

	return plt
