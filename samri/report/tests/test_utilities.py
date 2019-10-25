#!/usr/bin/env python
# -*- coding: utf-8 -*-

def test_roi_data():
	from samri.report.utilities import roi_data

	means, medians = roi_data('/usr/share/samri_bidsdata/preprocessing/sub-{subject}/ses-ofM/func/sub-{subject}_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv.nii.gz',
		'/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		substitution={'subject':4007}
		)
	assert means - 86.87587966450252 <= 0.001
	assert medians - 86.67946648370136 <= 0.001

def test_rois_for_comparison():
	import numpy as np
	from samri.report.utilities import rois_for_comparison

	img1 = '/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofM/anat/sub-4007_ses-ofM_acq-TurboRARElowcov_T2w.nii.gz'
	img2 = '/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofMaF/anat/sub-4007_ses-ofMaF_acq-TurboRARElowcov_T2w.nii.gz'

	img1, img2, rois = rois_for_comparison(img1, img2)

	img1_segment_rounded = [np.round(i) for i in img1[::30]]
	img2_segment_rounded = [np.round(i) for i in img2[::30]]
	rois_list = [i for i in rois[::30]]

	assert img1_segment_rounded == [30.0, 51.0, 24.0, 48.0, 50.0, 32.0, 45.0, 48.0, 34.0]
	assert img2_segment_rounded == [25.0, 43.0, 21.0, 46.0, 44.0, 30.0, 46.0, 47.0, 30.0]
	assert rois_list == [
		'amygdala, left',
		'pre-para subiculum, left',
		'Cortex-amygdala transition zones, left',
		'Primary somatosensory cortex: jaw region, left',
		'PoDG, left',
		'fornix, right',
		"Cingulate cortex: area 24a', right",
		'Primary motor cortex, right',
		'Ventral intermediate entorhinal cortex, right',
		]

def test_voxels_for_comparison():
	import numpy as np
	from samri.report.utilities import voxels_for_comparison

	img1 = '/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofM/anat/sub-4007_ses-ofM_acq-TurboRARElowcov_T2w.nii.gz'
	img2 = '/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofMaF/anat/sub-4007_ses-ofMaF_acq-TurboRARElowcov_T2w.nii.gz'

	img1, img2 = voxels_for_comparison(img1, img2,
		resample_voxel_size=[0.225,0.45,0.225],
		)

	img1_segment_rounded = [np.round(i) for i in img1[::500]]
	img2_segment_rounded = [np.round(i) for i in img2[::500]]

	assert img1_segment_rounded == [50.0, 54.0, 50.0, -3.0, 0.0, 27.0, 47.0, 57.0, 26.0, 49.0, 1.0, 21.0, 30.0, 0.0, 51.0, 23.0, 23.0, 54.0, 63.0, 33.0, 28.0, 34.0]
	assert img2_segment_rounded == [42.0, 53.0, 48.0, -3.0, 0.0, 23.0, 45.0, 24.0, 26.0, 46.0, 0.0, 33.0, 26.0, -0.0, 47.0, 22.0, 16.0, 52.0, 61.0, 27.0, 27.0, 30.0]
