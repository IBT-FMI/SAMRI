from os import path, listdir, getcwd, remove
if not __package__:
	import sys
	pkg_root = path.abspath(path.join(path.dirname(path.realpath(__file__)),"../../.."))
	sys.path.insert(0, pkg_root)

import nipype.interfaces.io as nio

from nilearn.input_data import NiftiLabelsMasker
from nilearn.connectome import ConnectivityMeasure

import numpy as np

from matplotlib import pyplot as plt



def plot_connectivity_matrix(correlation_matrix,
	figsize,
	labels,
	):

	plt.figure(figsize=figsize)
	np.fill_diagonal(correlation_matrix, 0)

	plt.imshow(correlation_matrix, interpolation="nearest", cmap="RdBu_r",
			   vmax=0.8, vmin=-0.8)

	x_ticks = plt.xticks(range(len(labels) - 1), labels[1:], rotation=90)
	y_ticks = plt.yticks(range(len(labels) - 1), labels[1:])
	plt.gca().yaxis.tick_right()
	plt.subplots_adjust(left=.01, bottom=.3, top=.99, right=.62)


def functional_connectivity(func_data,
	mask="/home/chymera/NIdata/templates/ds_QBI_chr_bin.nii.gz",
	labels = '',
	loud = False,
	):

	labels_masker = NiftiLabelsMasker(labels_img=mask, verbose=loud)

	timeseries = labels_masker.fit_transform(func_data)

	correlation_measure = ConnectivityMeasure(kind='correlation')
	correlation_matrix = correlation_measure.fit_transform([timeseries])[0]

	np.save(correlation_matrix, 'correlation_matrix.csv')
