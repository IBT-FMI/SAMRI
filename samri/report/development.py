# -*- coding: utf-8 -*-
def ctx_connectivity():
	import pandas as pd
	from behaviopy.plotting import qualitative_times
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel

	workflow_name = 'composite'
	my_roi = roi_from_atlaslabel("~/ni_data/templates/roi/DSURQEc_200micron_labels.nii",
		mapping="~/ni_data/templates/roi/DSURQE_mapping.csv",
		label_names=["cortex"],
		)

	substitutions = bids_substitution_iterator(
                ["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700"],
                ["CogB",],
                "~/ni_data/ofM.dr/",
                workflow_name,
                acquisitions=["EPI",],
                check_file_format='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_cbv_zstat.nii.gz',
		)
	fit, anova, subjectdf, voxeldf = roi.roi_per_session(substitutions,
		filename_template='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_cbv_zstat.nii.gz',
		roi_mask=my_roi,
		)
	subjectdf['treatment']='Fluoxetine'
	substitutions_ = bids_substitution_iterator(
                ["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		["6262","6255","5694","5706",'5704'],
                ["CogB",],
                "~/ni_data/ofM.dr/",
		workflow_name,
                acquisitions=["EPI",],
                check_file_format='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_cbv_zstat.nii.gz',
		)
	fit_, anova_, subjectdf_, voxeldf_ = roi.roi_per_session(substitutions_,
		filename_template='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_cbv_zstat.nii.gz',
		roi_mask=my_roi,
		)
	subjectdf_['treatment']='Vehicle'

	subjectdf=pd.concat([subjectdf_,subjectdf])
	subjectdf=subjectdf.rename(columns={'session': 'Session','t':'z'})

	subjectdf.to_csv('~/ni_data/ofM.dr/fc/{}/ctx_summary.csv'.format(workflow_name))
