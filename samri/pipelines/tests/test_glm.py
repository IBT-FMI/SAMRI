from samri.pipelines.glm import seed

def test_seed():
	seed('/var/tmp/samri_testing/pytest/preprocessed','/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
		match={"acq":["EPIlowcov"]},
		out_base='/var/tmp/samri_testing/pytest/',
		workflow_name='dr_fc',
		)
