#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np

def test_ts():
	from samri.report.roi import ts

	means, medians = ts('/usr/share/samri_bidsdata/preprocessing/sub-{subject}/ses-ofM/func/sub-{subject}_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv.nii.gz',
		'/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		substitution={'subject':4007}
		)
	means_start_rmse = (np.mean((means[:10] - np.array([88.47972138, 87.10901634, 87.67940811, 88.42660877, 88.20030224, 87.68827589, 87.88693223, 87.69688059, 86.15325618, 86.86802075]))**2))*(1/2.)
	assert means_start_rmse <= 10**-10
	means_end_rmse = (np.mean((means[-10:] - np.array([88.62766323, 87.29243884, 86.79143292, 86.55561678, 87.28995264, 86.94760042, 87.46978338, 87.23758544, 87.56910308, 86.37714772]))**2))*(1/2.)
	assert means_end_rmse <= 10**-10
	medians_start_rmse = (np.mean((medians[:10] - np.array([88.47972138, 87.10901634, 87.67940811, 88.42660877, 88.20030224, 87.68827589, 87.88693223, 87.69688059, 86.15325618, 86.86802075]))**2))*(1/2.)
	assert medians_start_rmse <= 10**-10
	medians_end_rmse = (np.mean((medians[-10:] - np.array([88.62766323, 87.29243884, 86.79143292, 86.55561678, 87.28995264, 86.94760042, 87.46978338, 87.23758544, 87.56910308, 86.37714772]))**2))*(1/2.)
	assert medians_end_rmse <= 10**-10


def test_atlasassignment():
	from samri.report.roi import atlasassignment

	atlasassignment(data_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		null_label=0.0,
		verbose=False,
		lateralized=True,
		save_as='/var/tmp/samri_testing/pytest/atlasassignment_lateralized.csv',
		)
	atlasassignment(data_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		null_label=0.0,
		verbose=False,
		lateralized=False,
		save_as='/var/tmp/samri_testing/pytest/atlasassignment.csv',
		)

def test_erode():
	from samri.report.roi import erode

	my_mask = erode('/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		iterations=1,
		)
	data = my_mask.get_data()
	assert np.sum(data) == 26

	my_mask = erode('/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		iterations=2,
		)
	data = my_mask.get_data()
	assert np.sum(data) == 2
