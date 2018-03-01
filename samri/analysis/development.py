def dr_seed_fc():
	import numpy as np
	from os import path
	from labbookdb.report.tracking import treatment_group, append_external_identifiers
	from samri.plotting.overview import multiplot_matrix, multipage_plot
	from samri.utilities import bids_substitution_iterator
	from samri.analysis import fc

	db_path = '~/syncdata/meta.db'
	groups = treatment_group(db_path, ['cFluDW','cFluDW_'], 'cage')
	groups = append_external_identifiers(db_path, groups, ['Genotype_code'])
	all_subjects = groups['ETH/AIC'].unique()

	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		all_subjects,
		["CogB",],
		"~/ni_data/ofM.dr/",
		"composite",
		acquisitions=["EPI",],
		check_file_format='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz')

	fc_results = fc.seed_based(substitutions, "~/ni_data/templates/roi/DSURQEc_dr.nii.gz", "~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		ts_file_template='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz',
		save_results="~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz",
		)
def drs_seed_fc():
	import numpy as np
	from os import path
	from labbookdb.report.tracking import treatment_group, append_external_identifiers
	from samri.plotting.overview import multiplot_matrix, multipage_plot
	from samri.utilities import bids_substitution_iterator
	from samri.analysis import fc

	db_path = '~/syncdata/meta.db'
	groups = treatment_group(db_path, ['cFluDW','cFluDW_'], 'cage')
	groups = append_external_identifiers(db_path, groups, ['Genotype_code'])
	all_subjects = groups['ETH/AIC'].unique()

	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		all_subjects,
		["CogB",],
		"~/ni_data/ofM.dr/",
		"composite",
		acquisitions=["EPI",],
		check_file_format='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz')

	fc_results = fc.seed_based(substitutions, "~/ni_data/templates/roi/DSURQEc_dr-s.nii.gz", "~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		ts_file_template='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz',
		save_results="~/ni_data/ofM.dr/fc/dr-s_seed/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz",
		)

