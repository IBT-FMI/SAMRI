def test_extract_volume():
	from samri.pipelines.extra_functions import extract_volume
	import nibabel as nii
	import nibabel as nib

	in_file = '/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofM/func/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-0_bold.nii.gz'

	out_file_name='test_extract_volume.nii.gz'
	extract_volume(in_file,
		volume=0,
		axis=3,
		out_file=out_file_name,
		)
	img = nib.load(out_file_name)
	assert img.header['dim'][0] == 3

def test_flip_if_needed():
	import os
	import pandas as pd
	from samri.pipelines.extra_functions import flip_if_needed

	nii_path = '/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofM/anat/sub-4007_ses-ofM_acq-TurboRARElowcov_T2w.nii.gz'
	data_selection = pd.DataFrame(
			[
				{'PV_position':'Prone'},
				{'PV_position':'Supine'},
			]
		)

	ind = 0
	out_name = 'should_be_a_file.nii.gz'
	flip_if_needed(data_selection, nii_path, ind, output_filename=out_name)
	assert os.path.isfile(out_name)

	ind = 1
	out_name = 'should_not_be_a_file.nii.gz'
	flip_if_needed(data_selection, nii_path, ind, output_filename=out_name)
	assert not os.path.isfile(out_name)

def test_physiofile_ts():
	from samri.pipelines.extra_functions import physiofile_ts

	timecourse_file = '/usr/share/samri_bidsdata/bids/sub-4007/ses-ofM/func/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-0_bold.nii.gz'
	physiofile_ts(timecourse_file,'neurons')

def test_write_bids_physio_file():
	from samri.pipelines.extra_functions import write_bids_physio_file

	scan_path = '/usr/share/samri_bindata/20170317_203312_5691_1_5/8/'
	write_bids_physio_file(scan_path,
		nii_name='sub-5691_ses-ofMpF_task-CogB_acq-EPI_cbv.nii.gz',
		)

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
