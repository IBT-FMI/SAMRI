def test_stat3D():
	import samri.plotting.maps as maps

	stat_map = "/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii"
	template = "/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii"

	maps.stat3D(stat_map,
		template=template,
		save_as="stat_3D.png",
		show_plot=False,
		threshold=4,
		threshold_mesh=12,
		)

