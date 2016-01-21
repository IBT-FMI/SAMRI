"""
GLM fitting in fMRI
===================
Full step-by-step example of fitting a GLM to experimental data and visualizing
the results.
More specifically:
1. A sequence of fMRI volumes are loaded
2. A design matrix describing all the effects related to the data is computed
3. a mask of the useful brain volume is computed
4. A GLM is applied to the dataset (effect/covariance, then contrast estimation)
"""
def the_function(n_scans, tr, paradigm_file, fmri_img):
	print(__doc__)

	from os import mkdir, path

	import numpy as np
	import pandas as pd
	from nilearn import plotting

	from nistats.glm import FirstLevelGLM
	from nistats.design_matrix import make_design_matrix
	from nistats import datasets


	### Data and analysis parameters #######################################

	# timing
	frame_times = np.linspace(0.5 * tr, (n_scans - .5) * tr, n_scans) # frame time set to mean acquisition time, and not onset
	# print frame_times

	# data
	if not fmri_img:
		data = datasets.fetch_localizer_first_level()
		fmri_img = data.epi_img
	# print data.paradigm, fmri_img

	### Design matrix ########################################

	paradigm = pd.read_csv(paradigm_file, sep=' ', header=None, index_col=None)
	paradigm.columns = ['session', 'name', 'onset', 'duration']
	design_matrix = make_design_matrix(frame_times, paradigm, hrf_model='canonical with derivative', drift_model="cosine", period_cut=128)
	print(design_matrix)

	### Perform a GLM analysis ########################################

	fmri_glm = FirstLevelGLM().fit(fmri_img, design_matrix)

	### Estimate contrasts #########################################

	# Specify the contrasts

	# write directory
	write_dir = 'results'
	if not path.exists(write_dir):
		mkdir(write_dir)

	# contrast estimation
	z_map, = fmri_glm.transform([[0,0,1,1,0,0,0,0]], contrast_name="Video",output_z=True)

	# Create snapshots of the contrasts
	display = plotting.plot_stat_map(z_map, display_mode='z', threshold=3.0, title="Video")
	display.savefig(path.join(write_dir, '%s_z_map.png' % "Video"))

	plotting.show()

if __name__ == "__main__":
	the_function(n_scans = 128, tr = 2.4, paradigm_file = "/home/chymera/src/chyMRI/sample_paradigm.csv", fmri_img="")
