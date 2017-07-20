import numpy as np
from os import path
from matplotlib import pyplot as plt
from numpy import genfromtxt
import seaborn as sns
import collections

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
	labels = '~/ni_data/templates/roi/DSURQE_mapping.csv',
	save_as = True,
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
	labels_np = genfromtxt(labels, delimiter=',', usecols = (1,2,3), dtype = 'str', skip_header = 1)
	labels_np[0]
	print(type(labels_np))
	labels_np = fix_labels(labels_np)
	if isinstance(correlation_matrix, str):
		correlation_matrix = path.abspath(path.expanduser(correlation_matrix))
		correlation_matrix = genfromtxt(correlation_matrix, delimiter=',')


	plt.figure(figsize=figsize)
	np.fill_diagonal(correlation_matrix, 0)
	sns.heatmap(correlation_matrix,
		xticklabels=labels_np,
		yticklabels=labels_np,
		square = 1,
		cbar_kws={"shrink": 0.75},
		)
	if(save_as):
		plt.savefig('matrix.png')
	plt.show()

	# old plt routing, keep for now
	# plt.imshow(correlation_matrix,
	# 	interpolation="nearest",
	# 	cmap="RdBu_r",
	# 	vmax=0.8,
	# 	vmin=-0.8
	# 	)
	#
	# x_ticks = plt.xticks(range(len(labels) - 1), labels[1:], rotation=90)
	# y_ticks = plt.yticks(range(len(labels) - 1), labels[1:])
	# plt.gca().yaxis.tick_right()
	# plt.subplots_adjust(left=.01, bottom=.3, top=.99, right=.62)
