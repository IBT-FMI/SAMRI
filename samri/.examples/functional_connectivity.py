# This example illustrates how to generate a functional connectivity matrix and its respective plot

import os
from os import path
from samri.analysis import fc
from samri.plotting import connectivity
from samri.fetch.templates import fetch_mouse_DSURQE

# fetch data templates and data
data_dir = path.join(path.dirname(path.realpath(__file__)),"../../example_data/")
results_dir = path.abspath(path.expanduser('~/.samri_files/results/fc/'))
# check if results dir exists, otherwise create
if not os.path.exists(path.abspath(path.expanduser(results_dir))):
	os.makedirs(path.abspath(path.expanduser(results_dir)))

template = fetch_mouse_DSURQE()

# run analysis and plot result
ts = path.abspath(path.expanduser('~/ni_data/ofM.dr/preprocessing/as_composite/sub-4011/ses-ofM_aF/func/sub-4011_ses-ofM_aF_trial-EPI_CBV_jb_long.nii.gz'))
#ts= data_dir + "sub-5690_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz"
figsize=(50,50)
correlation_matrix = fc.correlation_matrix(ts, labels_img = template['atlas'], save_as = results_dir + '/correlation_matrix.csv')
connectivity.plot_connectivity_matrix(correlation_matrix, figsize = figsize, labels=template['labels'], save_as = results_dir + '/correlation_matrix.png')
