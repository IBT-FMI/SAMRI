def test_stat3D():
	import samri.plotting.maps as maps

	stat_map = "/usr/share/mouse-brain-atlases/abi2dsurqec_40micron_masked.nii"
	template = "/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii"

	maps.stat3D(stat_map,
			template = template,
			save_as = "stat_3D.png",
			threshold = 4,
			threshold_mesh = 12,
			)

