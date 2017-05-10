import numpy as np
from matplotlib import pyplot as plt

def plot_connectivity_matrix(correlation_matrix,
	figsize,
	labels,
	):

	plt.figure(figsize=figsize)
	np.fill_diagonal(correlation_matrix, 0)

	plt.imshow(correlation_matrix,
		interpolation="nearest",
		cmap="RdBu_r",
		vmax=0.8,
		vmin=-0.8
		)

	x_ticks = plt.xticks(range(len(labels) - 1), labels[1:], rotation=90)
	y_ticks = plt.yticks(range(len(labels) - 1), labels[1:])
	plt.gca().yaxis.tick_right()
	plt.subplots_adjust(left=.01, bottom=.3, top=.99, right=.62)
