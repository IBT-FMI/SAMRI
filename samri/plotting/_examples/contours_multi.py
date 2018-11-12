import itertools
import matplotlib.pyplot as plt

from samri.plotting.maps import contour_slices
from samri.utilities import bids_substitution_iterator

subjects = [
	'4001',
#	'4002',
#	'4004',
#	'4005',
#	'4006',
#	'4007',
#	'4008',
#	'4009',
#	'4011',
#	'4012',
#	'4013',
	]
contrasts= [
	'bold',
	'cbv',
	]

for i in list(itertools.product(subjects, contrasts)):
	file_template='{{data_dir}}/preprocessing/generic_collapsed/sub-{{subject}}/ses-{{session}}/func/sub-{{subject}}_ses-{{session}}_task-JogB_acq-EPIlowcov_run-{{run}}_{}.nii.gz'.format(i[1])

	substitutions = bids_substitution_iterator(
		sessions=[
			'ofM',
			'ofMaF',
			'ofMcF1',
			'ofMcF2',
			'ofMpF',
			],
		subjects=[i[0]],
		runs=[0,1],
		data_dir='~/ni_data/ofM.dr',
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
		ratio=[7,5],
		save_as='contours_multi_{}_{}.png'.format(i[0],i[1]),
		slice_spacing=0.45,
		substitutions=substitutions,
		)
