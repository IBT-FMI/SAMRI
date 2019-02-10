def test_reset_background():
	from samri.pipelines.extra_functions import reset_background
	import nibabel as nib

	reset_background('/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofM/func/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv.nii.gz',
		restriction_range=10,
		bg_value=1000,
		out_file='reset_background.nii.gz'
		)
	img = nib.load('reset_background.nii.gz')
	data = img.get_data()
	bg_by_coordinates = data[0,0,0,0]
	assert bg_by_coordinates == 1000
