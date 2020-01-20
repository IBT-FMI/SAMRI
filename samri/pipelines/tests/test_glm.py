from samri.pipelines.glm import l1, l1_physio, seed

PREPROCESS_BASE = '/usr/share/samri_bidsdata/preprocessing'

def test_l1():
	l1(PREPROCESS_BASE,
		mask='mouse',
		match={'session': ['ofMaF'], 'acq':['EPIlowcov']},
		out_base='/var/tmp/samri_testing/pytest/',
		workflow_name='l1',
		)

# Takes too long or hangs
#def test_physio():
#	l1_physio(PREPROCESS_BASE, 'astrocytes',
#		highpass_sigma=180,
#		convolution=False,
#		mask='mouse',
#		n_jobs_percentage=.33,
#		match={
#			'modality':['bold'],
#			'session':['ofM'],
#			},
#		invert=False,
#		workflow_name='l1_astrocytes',
#		out_base='/var/tmp/samri_testing/pytest/',
#		)

# Takes too long or hangs
#def test_seed():
#	seed(PREPROCESS_BASE,'/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
#		match={"acq":["EPIlowcov"]},
#		out_base='/var/tmp/samri_testing/pytest/',
#		workflow_name='dr_fc',
#		)
