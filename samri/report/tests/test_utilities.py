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
