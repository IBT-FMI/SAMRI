from samri.pipelines.reposit import bru2bids

data_dir = '/usr/share/samri_bindata/'

bru2bids(data_dir,
	inflated_size=False,
	functional_match={"acquisition":["EPI"]},
	structural_match={"acquisition":["TurboRARE"]},
	out_base='/tmp/samri_testing/bids',
	)
