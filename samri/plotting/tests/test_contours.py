def test_contours_single():
	from samri.plotting.maps import contour_slices
	import matplotlib.pyplot as plt

	file_template = '/usr/share/mouse-brain-atlases/dsurqec_200micron_masked.nii'

	cmap = plt.get_cmap('tab20').colors
	contour_slices('/usr/share/samri_bidsdata/preprocessing/sub-4007/ses-ofM/func/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv.nii.gz',
		alpha=[0.9],
		colors=cmap[::2],
		figure_title='Single-Session Fit and Distortion Control',
		file_template=file_template,
		force_reverse_slice_order=True,
		legend_template='Template',
		levels_percentile=[79],
		ratio=[8,5],
		slice_spacing=0.45,
		save_as='_contours_single.png',
		)

def test_contours_substitutions():
	import itertools
	import matplotlib.pyplot as plt

	from samri.plotting.maps import contour_slices
	from samri.utilities import bids_substitution_iterator

	subjects = [
		'4007',
		]
	contrasts= [
		#'bold',
		'cbv',
		]

	for i in list(itertools.product(subjects, contrasts)):
		file_template='{{data_dir}}/preprocessing/sub-{{subject}}/ses-{{session}}/func/sub-{{subject}}_ses-{{session}}_task-JogB_acq-EPIlowcov_run-{{run}}_{}.nii.gz'.format(i[1])

		substitutions = bids_substitution_iterator(
			sessions=[
				'ofM',
				'ofMaF',
				'ofMcF1',
				'ofMcF2',
				],
			subjects=[i[0]],
			runs=[0,1],
			data_dir='/usr/share/samri_bidsdata',
			validate_for_template=file_template,
			)

		cmap = plt.get_cmap('tab20').colors
		contour_slices('/usr/share/mouse-brain-atlases/dsurqec_40micron.nii',
			alpha=[0.6],
			colors=cmap[::2],
			figure_title='Multi-Session Fit and Coherence Control',
			file_template=file_template,
			force_reverse_slice_order=True,
			legend_template='{session} session',
			levels_percentile=[77],
			save_as='_contours_multi_{}_{}.png'.format(i[0],i[1]),
			slice_spacing=0.45,
			substitutions=substitutions,
			)
