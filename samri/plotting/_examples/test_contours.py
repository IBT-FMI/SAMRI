def test_contours_single():
	from samri.plotting.maps import contour_slices
	import matplotlib.pyplot as plt

	file_template = '/usr/share/mouse-brain-atlases/dsurqec_200micron_masked.nii'

	cmap = plt.get_cmap('tab20').colors
	contour_slices('~/ni_data/ofM.dr/preprocessing/generic/sub-4001/ses-ofM/func/sub-4001_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv.nii.gz',
		alpha=[0.9],
		colors=cmap[::2],
		figure_title='Single-Session Fit and Distortion Control',
		file_template=file_template,
		force_reverse_slice_order=True,
		legend_template='Template',
		levels_percentile=[79],
		ratio=[8,5],
		slice_spacing=0.45,
		save_as='contours_single.png',
		)
