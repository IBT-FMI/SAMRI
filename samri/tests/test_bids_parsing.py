from os import path

DATA_DIR = path.join(path.dirname(path.realpath(__file__)),'../tests/data/')

def assert_and_feedback(obtained, expected,
	debug='',
	):
	try:
		assert obtained == expected
	except AssertionError:
		print(debug)
		raise AssertionError('The compared strings are not identical:\n"{}" - computed.\n"{}" - expected.'.format(obtained, expected))

def test_bids_naming():
	from samri.pipelines.extra_functions import get_data_selection
	from samri.pipelines.utils import bids_naming
	import pandas as pd
	import os

	bruker_data_dir = path.join(DATA_DIR,'bruker')
	f_data_selection = get_data_selection(bruker_data_dir,
		match={
			'task':['JogB','CogB','CogB2m'],
			},
		)
	s_data_selection = get_data_selection(bruker_data_dir,
		match={
			'acquisition':['TurboRARE', 'TurboRARElowcov'],
			},
		)

	name = bids_naming(
			subject_session=('5706','ofMpF'),
			metadata=f_data_selection,
			)
	assert_and_feedback(name,'sub-5706_ses-ofMpF_task-CogB_acq-EPI_cbv.nii.gz', debug=f_data_selection)

	name = bids_naming(
			subject_session=('4011','ofMaF'),
			metadata=s_data_selection,
			)
	assert_and_feedback(name,'sub-4011_ses-ofMaF_acq-TurboRARElowcov_T2w.nii.gz', debug=s_data_selection)

	name = bids_naming(
			subject_session=('5704','ofMpF'),
			metadata=f_data_selection,
			)
	assert_and_feedback(name,'sub-5704_ses-ofMpF_task-CogB_acq-EPI_cbv.nii.gz', debug=f_data_selection)

	name = bids_naming(
			subject_session=('5704','ofMpF'),
			metadata=s_data_selection,
			)
	assert_and_feedback(name,'sub-5704_ses-ofMpF_acq-TurboRARE_T2w.nii.gz', debug=s_data_selection)

# The following test fails because it will not work with our dummy data (containing only the directory hierarchy and some metadata files).
# This should work once we can include `2dseq` files in our example data.
#def test_bru2bids():
#	from samri.pipelines.reposit import bru2bids
#
#	bruker_data_dir = path.join(DATA_DIR,'bruker')
#	bru2bids(bruker_data_dir,
#		debug=False,
#		functional_match={'task':['JogB','CogB','CogB2m'],},
#		structural_match={'acquisition':['TurboRARE', 'TurboRARElowcov']},
#		actual_size=True,
#		keep_work=False,
#		)


# will fail as well (see above)

#def test_bruker_bids():
#	from samri.pipelines.preprocess import bruker
#
#	bids_base = '~/ni_data/bruker/bids'
#
#	bruker(bids_base,
#		"mouse",
#		functional_match={'task':['JogB','CogB','CogB2m'],},
#		structural_match={'acquisition':['TurboRARE', 'TurboRARElowcov']},
#		functional_registration_method="composite")

