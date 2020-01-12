from samri.pipelines.manipulations import transform_feature

# Takes too long
#def test_transform_feature():
#	transform_feature('/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii', '/usr/share/mouse-brain-atlases/dsurqec_200micron_masked.nii', '/usr/share/mouse-brain-atlases/ambmc_200micron.nii',
#		target_mask='',
#		phases=['rigid','affine','syn'],
#		num_threads=4,
#		output_path='transformed_feature.nii.gz',
#		interpolation='NearestNeighbor',
#		)
