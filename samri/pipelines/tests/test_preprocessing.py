from samri.pipelines.preprocess import generic, legacy
from samri.pipelines import manipulations

bids_base = '/usr/share/samri_bidsdata/bids/'

def test_generic():
	generic(bids_base,
		"/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		registration_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		functional_match={'acquisition':['EPIlowcov'],},
		structural_match={'acquisition':['TurboRARElowcov'],},
		actual_size=True,
		out_base='/tmp/samri_testing/preprocessing',
		workflow_name='generic',
		)
