from samri.pipelines.manipulations import transform_feature

transform_feature('~/ni_data/templates/roi/DSURQEc_drp.nii.gz', '/usr/share/mouse-brain-atlases/dsurqec_200micron_masked.nii', '~/ambmc_200micron.nii.gz',
	target_mask='',
	phases=['rigid','affine','syn'],
	num_threads=4,
	output_name='transformed_feature.nii.gz',
	interpolation='NearestNeighbor',
	)

