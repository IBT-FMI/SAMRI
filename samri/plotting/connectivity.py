import numpy as np
from matplotlib import pyplot as plt
from numpy import genfromtxt
import seaborn as sns

def plot_connectivity_matrix(correlation_matrix,
	figsize = (50,50),
	labels = '~/ni_data/templates/roi/DSURQE_mapping.csv',
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

	#TODO: fix labels in ascending order corresponding to intensity values
	labels = path.abspath(path.expanduser(labels))

	labels_np = genfromtxt(labels, delimiter=',', usecols = (1), dtype = 'str')

	plt.figure(figsize=figsize)
	np.fill_diagonal(correlation_matrix, 0)

	sns.heatmap(correlation_matrix,
        xticklabels=labels_np,
        yticklabels=labels_np,
        square = 1
		)

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
