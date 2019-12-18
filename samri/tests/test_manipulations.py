from samri.manipulations import flip_axis

def test_flip_axis():
	nii_path = '/usr/share/samri_bidsdata/bids_collapsed/sub-4007/ses-ofM/func/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-0_bold.nii.gz'
	flip_axis(nii_path)
