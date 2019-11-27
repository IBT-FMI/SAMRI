def test_multi_roi_timeseries():
	import matplotlib.pyplot as plt
	from os import path
	from samri.plotting import summary, timeseries
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel

	substitutions = bids_substitution_iterator(
		sessions=[
			'ofM',
			'ofMaF',
			],
		subjects=[
		     '4007',
		     ],
		runs=[
		     '0',
		     '1',
		     ],
		modalities=[
		     'bold',
		     'cbv',
		     ],
		data_dir='/usr/share/samri_bidsdata',
		# BOLD scans are not recognized, since the current (=sci-biology/samri_bidsdata-0.2) filt file suffix also contains `_maths_` for CBV, but not for BOLD.
		validate_for_template="{data_dir}/l1/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-JogB_acq-EPIlowcov_run-{run}_{modality}.nii.gz",
		)

	mapping='/usr/share/mouse-brain-atlases/dsurqe_labels.csv'
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii'
	my_roi = roi_from_atlaslabel(atlas,
		mapping=mapping,
		label_names=['cortex'],
		)
	timecourses, designs, _, events_dfs, subplot_titles = summary.ts_overviews(substitutions, my_roi,
		ts_file_template="{data_dir}/l1/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-JogB_acq-EPIlowcov_run-{run}_{modality}.nii.gz",
		betas_file_template="{data_dir}/l1/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-JogB_acq-EPIlowcov_run-{run}_{modality}_betas.nii.gz",
		design_file_template="{data_dir}/l1/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-JogB_acq-EPIlowcov_run-{run}_{modality}_design.mat",
		event_file_template='{data_dir}/preprocessing/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_task-JogB_acq-EPIlowcov_run-{run}_events.tsv',
		n_jobs_percentage=0.2,
		)

	style_file = path.join(path.dirname(path.realpath(__file__)),'../samri_multiple-ts.conf')
	plt.style.use(style_file)

	timeseries.multi(timecourses, designs, events_dfs, subplot_titles,
		quantitative=False,
		save_as='_multi_roi_timeseries.pdf',
		)

