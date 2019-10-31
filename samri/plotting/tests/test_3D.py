def test_stat3D_mask():
	import samri.plotting.maps as maps

	stat_map = "/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii"
	template = "/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii"

	maps.stat3D(stat_map,
		template=template,
		save_as="_stat3D_mask.png",
		show_plot=False,
		threshold=0.5,
		threshold_mesh = 0.5,
		)

def test_stat3D_heatmap():
	import samri.plotting.maps as maps

	bindata_dir = '/usr/share/samri_bidsdata'
	heatmap_image = '{}/l1/sub-4007/ses-ofM/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv_tstat.nii.gz'.format(bindata_dir)
	template = "/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii"

	maps.stat3D(heatmap_image,
		cut_coords=(0.0,-4.6,-3.4),
		template=template,
		save_as="_stat3D_heatmap.png",
		show_plot=False,
		threshold=4,
		threshold_mesh=4,
		)

def test_stat3D_overlay():
	"""No explicit `threshold_mesh` specification, in order to test implicit behaviour."""
	import samri.plotting.maps as maps

	bindata_dir = '/usr/share/samri_bidsdata'
	heatmap_image = '{}/l1/sub-4007/ses-ofM/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv_tstat.nii.gz'.format(bindata_dir)
	overlay = "/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii"
	template = "/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii"

	maps.stat3D(heatmap_image,
		cut_coords=(0.0,-4.6,-3.4),
		overlays=[overlay],
		template=template,
		save_as="_stat3D_overlay.png",
		show_plot=False,
		threshold=4,
		)

