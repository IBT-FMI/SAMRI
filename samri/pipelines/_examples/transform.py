from samri.pipelines.manipulations import transform_feature

transform_feature('~/ni_data/templates/roi/DSURQEc_drs.nii.gz', '/usr/share/mouse-brain-atlases/dsurqec_200micron_masked.nii', '/usr/share/mouse-brain-atlases/ambmc_200micron.nii',
	target_mask='',
	phases=['rigid','affine','syn'],
	num_threads=4,
	output_name='transformed_feature.nii.gz',
	interpolation='NearestNeighbor',
	)

