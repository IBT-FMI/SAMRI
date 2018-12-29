def test_reset_background():
	from samri.pipelines.extra_functions import reset_background
	reset_background('/usr/share/samri_bidsdata/preprocessing/generic/sub-4007/ses-ofM/func/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv.nii.gz',
		restriction_range=10,
		bg_value=1000,
		)
