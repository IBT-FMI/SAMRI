from samri.pipelines.reposit import bru2bids

BRU_DIR = '/usr/share/samri_bindata/'

BRU_DIR = '~/samri_bindata'
def test_bru2bids():
	bru2bids(BRU_DIR,
		inflated_size=False,
		functional_match={"acquisition":["EPI"]},
		structural_match={"acquisition":["TurboRARE"]},
		out_base='/var/tmp/samri_testing/pytest/',
		)
