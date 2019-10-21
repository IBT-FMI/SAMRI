def test_physiofile_ts():
	from samri.pipelines.extra_functions import physiofile_ts

	timecourse_file = '/home/chymera/.scratch/nvcz/preprocessed/sub-7293/ses-ketxyl/func/sub-7293_ses-ketxyl_task-rhp_acq-geEPI_run-0_bold.nii.gz'
	physiofile_ts(timecourse_file,'neurons')

# Uncomment when testing data with physiology files is available
#def test_write_bids_physio_file():
#	from samri.pipelines.extra_functions import write_bids_physio_file
#
#	scan_path = '/usr/share/samri_bindata/20170317_203312_5691_1_5/8/'
#	write_bids_physio_file(scan_path,
#		nii_name='sub-0001_ses-01_acq-geEPI_cbv.nii.gz',
#		)

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
