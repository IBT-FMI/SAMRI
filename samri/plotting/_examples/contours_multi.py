import itertools
import matplotlib.pyplot as plt

from samri.plotting.maps import contour_slices
from samri.utilities import bids_substitution_iterator

subjects = [
	'4001',
	'4002',
	'4004',
	'4005',
	'4006',
	'4007',
	'4008',
	'4009',
	'4011',
	'4012',
	'4013',
	]
contrasts = [
	'bold',
	'cbv',
	]
workflows = [
	'generic',
	'legacy',
	]

for i in list(itertools.product(subjects, contrasts, workflows)):
	file_template='{{data_dir}}/preprocessing/{}_collapsed/sub-{{subject}}/ses-{{session}}/func/sub-{{subject}}_ses-{{session}}_task-JogB_acq-EPIlowcov_run-{{run}}_{}.nii.gz'.format(i[2],i[1])

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

	if i[2] == 'generic':
		template = '/usr/share/mouse-brain-atlases/dsurqec_40micron.nii'
	elif i[2] == 'legacy':
		template = '~/lambmc_40micron.nii'

	cmap = plt.get_cmap('tab20').colors
	contour_slices(template,
		alpha=[0.6],
		colors=cmap[::2],
		figure_title='Multi-Session Fit and Coherence Control',
		file_template=file_template,
		force_reverse_slice_order=True,
		legend_template='{session} session',
		levels_percentile=[77],
		save_as='contours_multi_{}_{}_{}.png'.format(i[0],i[1],i[2]),
		slice_spacing=0.45,
		substitutions=substitutions,
		ratio=[6,5],
		#scale=0.5,
		)
