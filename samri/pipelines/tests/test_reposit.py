from samri.pipelines.reposit import bru2bids

data_dir = '/usr/share/samri_bindata/'

def test_bru2bids():
	bru2bids(data_dir,
		inflated_size=False,
		functional_match={"acquisition":["EPI"]},
		structural_match={"acquisition":["TurboRARE"]},
		out_base='/var/tmp/samri_testing/pytest/',
		)
