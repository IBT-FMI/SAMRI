from os import path

DATA_DIR = path.join(path.dirname(path.realpath(__file__)),'../../example_data/')

def assert_and_feedback(obtained, expected,
	debug='',
	):
	try:
		assert obtained == expected
	except AssertionError:
		print(debug)
		raise AssertionError('The compared strings are not identical:\n"{}" - computed.\n"{}" - expected.'.format(obtained, expected))

def test_bruker_to_bids(
	):
	from samri.pipelines.extra_functions import get_data_selection
	from samri.pipelines.utils import bids_naming
	import pandas as pd
	import os

	bruker_data_dir = path.join(DATA_DIR,'bruker')
	data_selection = get_data_selection(bruker_data_dir,
		match={
			'trial':['JogB','CogB','CogB2m'],
			'acquisition':['TurboRARE', 'TurboRARElowcov']},
		)

	name = bids_naming(
			metadata=data_selection,
			scan_type='acq-EPI_CBV_trial-CogB',
			subject_session=('5706','ofMpF'),
			)
	assert_and_feedback(name,'sub-5706_ses-ofMpF_acq-EPI_trial-CogB_cbv.nii.gz', debug=data_selection)

	name = bids_naming(
			metadata=data_selection,
			scan_type='acq-TurboRARElowcov',
			subject_session=('4011','ofMaF'),
			)
	assert_and_feedback(name,'sub-4011_ses-ofMaF_acq-TurboRARElowcov_T2w.nii.gz', debug=data_selection)

	name = bids_naming(
			metadata=data_selection,
			scan_type='acq-EPI_CBV_trial-CogB',
			subject_session=('5704','ofMpF'),
			)
	assert_and_feedback(name,'sub-5704_ses-ofMpF_acq-EPI_trial-CogB_cbv.nii.gz', debug=data_selection)

	name = bids_naming(
			metadata=data_selection,
			scan_type='acq-TurboRARE',
			subject_session=('5704','ofMpF'),
			)
	assert_and_feedback(name,'sub-5704_ses-ofMpF_acq-TurboRARE_T2w.nii.gz', debug=data_selection)
