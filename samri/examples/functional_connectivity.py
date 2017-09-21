# This example illustrates how to generate a functional connectivity matrix and it's respective plot

from os import path
from samri.pipelines import fc
from samri.plotting import connectivity
from samri.fetch import fetch_mouse_DSURQE

# fetch data templates and data
data_dir = path.join(path.dirname(path.realpath(__file__)),"../../example_data/")
results_dir = path.abspath(path.expanduser('~/.samri_files/results/'))
template = fetch_mouse_DSURQE()

# run analysis and plot result
#ts= data_dir + "sub-5690_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz"
ts= "~/ni_data/ofM.dr/preprocessing/marksm_composite/sub-5690/ses-ofM_aF/sub-5690_ses-ofM_aF_trial-EPI_CBV_chr_longSOA.nii.gz"
figsize=(50,50)
correlation_matrix = fc.correlation_matrix(ts, template.labels, save_as = results_dir + '/fc/correlation_matrix.csv')
connectivity.plot_connectivity_matrix(correlation_matrix, figsize, template.labels, save_as = results_dir + '/fc/correlation_matrix.png')
