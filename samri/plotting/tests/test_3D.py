def test_composite_stat3D():
	import samri.plotting.maps as maps

	stat_map = "/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii"
	template = "/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii"

	maps.stat3D(stat_map,
		template=template,
		save_as="stat3D.png",
		show_plot=False,
		threshold=0.5,
		threshold_mesh = 0.5,
		)

