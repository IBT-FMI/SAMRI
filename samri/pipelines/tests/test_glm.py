from samri.pipelines.glm import l1, seed

def test_l1():
	l1('/var/tmp/samri_testing/pytest/prep',
		mask='mouse',
		match={"acq":["EPIlowcov"]},
		out_base='/var/tmp/samri_testing/pytest/',
		workflow_name='l1',
		)

def test_seed():
	seed('/usr/share/samri_bidsdata/preprocessing','/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		match={"acq":["EPIlowcov"]},
		out_base='/var/tmp/samri_testing/pytest/',
		workflow_name='dr_fc',
		)
