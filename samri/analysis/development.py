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
def drp_seed_fc():
	import numpy as np
	from os import path
	#from labbookdb.report.tracking import treatment_group, append_external_identifiers
	from samri.plotting.overview import multiplot_matrix, multipage_plot
	from samri.utilities import bids_substitution_iterator
	from samri.analysis import fc
	from samri.utilities import N_PROCS

	N_PROCS=max(N_PROCS-8, 2)

	from bids.grabbids import BIDSLayout
	from bids.grabbids import BIDSValidator
	import os

	base = '~/ni_data/ofM.dr/bids/preprocessing/generic/'
	base = os.path.abspath(os.path.expanduser(base))
        validate = BIDSValidator()
        for x in os.walk(base):
                print(x[0])
                print(validate.is_bids(x[0]))
        layout = BIDSLayout(base)
        df = layout.as_data_frame()
	df = df[df.type.isin(['cbv'])]
        print(df)

	#substitutions = bids_substitution_iterator(
	#	list(df['session'].unique()),
	#	all_subjects,
	#	["CogB",],
	#	"~/ni_data/ofM.dr/",
	#	"composite",
	#	acquisitions=["EPI",],
	#	check_file_format='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz')

	#substitutions = df.T.to_dict().values()[:2]
	substitutions = df.T.to_dict().values()
	print(substitutions)

	fc_results = fc.seed_based(substitutions, "~/ni_data/templates/roi/DSURQEc_drp.nii.gz", "~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		ts_file_template='~/ni_data/ofM.dr/bids/preprocessing/generic/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz',
		save_results="~/ni_data/ofM.dr/bids/fc/DSURQEc_drp/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz",
		n_procs=N_PROCS,
		cachedir='/mnt/data/joblib')

