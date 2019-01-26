# This example illustrates how to generate a functional connectivity matrix and its respective plot

import matplotlib
matplotlib.use('Agg')


import os
from os import path
from samri.analysis import fc
from samri.plotting import connectivity
from samri.fetch.templates import fetch_rat_waxholm

# fetch data templates and data
data_dir = path.join(path.dirname(path.realpath(__file__)),"../tests/data/")
results_dir = path.abspath(path.expanduser('~/.samri_files/results/fc/'))
# check if results dir exists, otherwise create
if not os.path.exists(path.abspath(path.expanduser(results_dir))):
	os.makedirs(path.abspath(path.expanduser(results_dir)))

template = fetch_rat_waxholm()

trial = 'MhBu'
ts = path.abspath(path.expanduser('~/ni_data/data/preprocessing/composite/sub-22/ses-noFUSr0/func/sub-22_ses-noFUSr0_acq-seEPI_trial-'+trial+'.nii.gz'))

figsize=(50,50)
correlation_matrix = fc.correlation_matrix(ts, labels_img = template['atlas'], mask=template['mask'], save_as = results_dir + '/correlation_matrix_'+trial+'.csv')
connectivity.plot_connectivity_matrix(correlation_matrix, figsize = figsize, labels=template['labels'], save_as = results_dir + '/correlation_matrix_'+trial+'.png')

# also plot dendogram
fc.dendogram(correlation_matrix, figsize = figsize, save_as = results_dir + '/dendogram_'+trial+'.png')
