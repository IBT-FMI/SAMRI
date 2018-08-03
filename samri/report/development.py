# -*- coding: utf-8 -*-

# Development work, e.g. for higher level functions.
# These functions are not intended to work on any machine or pass the tests.
# They are early drafts (e.g. of higher level workflows) intended to be shared among select collaborators or multiple machines of one collaborator.
# Please don't edit functions which are not yours, and only perform imports in local scope.

def pattern_fc():
	import pandas as pd
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel

	workflow_name = 'drs_seed'
	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700"],
                ["CogB",],
                "~/ni_data/ofM.dr/",
                workflow_name,
                acquisitions=["EPI",],
                check_file_format='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		)
	subjectdf = summary.analytic_pattern_per_session(substitutions,
		'~/ni_data/ofM.dr/l2/anova_ctx/anova_zfstat.nii.gz',
                t_file_template='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		figure="per-participant",
		color="#309079",
		xy_label=["Session","Pattern Score"],
		)
	subjectdf['treatment']='Fluoxetine'

	substitutions_ = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		["6262","6255","5694","5706",'5704'],
                ["CogB",],
                "~/ni_data/ofM.dr/",
                workflow_name,
                acquisitions=["EPI",],
                check_file_format='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		)
	subjectdf_ = summary.analytic_pattern_per_session(substitutions_,
		'~/ni_data/ofM.dr/l2/anova_ctx/anova_zfstat.nii.gz',
                t_file_template='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		figure="per-participant",
		color="#309079",
		xy_label=["Session","Pattern Score"],
		)
	subjectdf_['treatment']='Vehicle'

	subjectdf=pd.concat([subjectdf_,subjectdf])
	subjectdf=subjectdf.rename(columns={'session': 'Session',})

	subjectdf.to_csv('~/ni_data/ofM.dr/fc/{}/ctx_pattern_summary.csv'.format(workflow_name))

def vol():
	from snr import df_threshold_volume ,iter_threshold_volume
	from samri.utilities import bids_autograb
	import pandas as pd

	base_df = bids_autograb('~/ni_data/ofM.dr/bids')
	base_df = base_df.loc[~base_df['path'].str.endswith('.json')]
	base_df = base_df.loc[base_df['type'].isin(['bold','cbv'])]
	base_df['uID'] = base_df['subject']+'_'+base_df['session']+'_'+base_df['type']

	generic_df = bids_autograb('~/ni_data/ofM.dr/preprocessing/generic')
	generic_df = generic_df.loc[~generic_df['path'].str.endswith('.json')]
	generic_df = generic_df.loc[generic_df['type'].isin(['bold','cbv'])]
	generic_df['uID'] = generic_df['subject']+'_'+generic_df['session']+'_'+generic_df['type']

	uids = generic_df['uID'].unique()
	base_df = base_df.loc[base_df['uID'].isin(uids)]

	base_df['Processing'] = 'Generic'
	df = pd.DataFrame([])
	df_ = df_threshold_volume(base_df,
		threshold=0.0,
		threshold_is_percentile=False,
		)
	df = df.append(df_)
	generic_df['Processing'] = 'Generic'
	df_ = df_threshold_volume(generic_df, inverted_data={'type':'cbv'},
		threshold=0.0,
		threshold_is_percentile=False,
		)
	df = df.append(df_)
	print(df)

def pattern_activity():
	import pandas as pd
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel

	workflow_name = 'generic'
	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
                ["CogB",],
                "~/ni_data/ofM.dr/bids",
                workflow_name,
                acquisitions=["EPI",],
                validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	df = roi.analytic_pattern_per_session(substitutions,
		'~/ni_data/ofM.dr/bids/l2/best_responders/sessionofM/tstat1.nii.gz',
		t_file_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	df['treatment']='Fluoxetine'

	substitutions_ = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		["6262","6255","5694","5706",'5704','6455','6459'],
                ["CogB",],
                "~/ni_data/ofM.dr/bids",
                workflow_name,
                acquisitions=["EPI",],
                validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	df_ = roi.analytic_pattern_per_session(substitutions_,
		'~/ni_data/ofM.dr/bids/l2/best_responders/sessionofM/tstat1.nii.gz',
		t_file_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	df_['treatment']='Vehicle'

	df=pd.concat([df_,df])
	df=df.rename(columns={'session': 'Session',})

	df.to_csv('~/ni_data/ofM.dr/bids/l1/{}/pattern_summary.csv'.format(workflow_name))

def label_activity(label):
	"""
	Create a DataFrame containing the per-session per-subject mean values for an autogenerated ROI based on the given label.
	Other parameter customizations are hard-coded below.
	"""
	import pandas as pd
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel
	from os.path import basename, splitext

	mapping='/usr/share/mouse-brain-atlases/dsurqec_mapping.csv'
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii'
	my_roi = roi_from_atlaslabel(atlas,
		mapping=mapping,
		label_names=[label],
		)

	workflow_name = 'generic'
	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
                ["CogB",],
                "~/ni_data/ofM.dr/bids/",
                workflow_name,
                acquisitions=["EPI",],
                validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	df = roi.per_session(substitutions,
		filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		roi_mask=my_roi,
		feature=[label],
		atlas=atlas,
		mapping=mapping,
		)
	df['treatment']='Fluoxetine'
	substitutions_ = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		["6262","6255","5694","5706",'5704','6455','6459'],
                ["CogB",],
                "~/ni_data/ofM.dr/bids/",
                workflow_name,
                acquisitions=["EPI",],
		validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		)
	df_ = roi.per_session(substitutions_,
		filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_tstat.nii.gz',
		roi_mask=my_roi,
		feature=[label],
		atlas=atlas,
		mapping=mapping,
		)
	df_['treatment']='Vehicle'

	df=pd.concat([df_,df])
	df=df.rename(columns={'session': 'Session',})

	df.to_csv('~/ni_data/ofM.dr/bids/l1/{}/{}.csv'.format(workflow_name, label))

def roi_activity(roi_mask="~/ni_data/templates/roi/DSURQEc_drp.nii.gz"):
	"""
	Create a DataFrame containing the per-session per-subject mean values for the specified ROI.
	Other parameter customizations are hard-coded below.
	"""

	import pandas as pd
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel
	from os.path import basename, splitext

	workflow_name = 'generic'
	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		#["5689","5690","6456","6461"],
		['5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
		#['5691',"5689","5690","5700",],
                ["CogB",],
                "~/ni_data/ofM.dr/bids/",
                workflow_name,
                acquisitions=["EPI",],
                validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
		)
	df = roi.per_session(substitutions,
		filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
		roi_mask=roi_mask,
		)
	df['treatment'] = 'Fluoxetine'
	substitutions_ = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		#["5694","5706",'5704','6455','6459','5794'],
		["6262","6255","5694","5706",'5704','6455','6459'],
		#["6262","6255","5694","5706",'5704',],
                ["CogB",],
                "~/ni_data/ofM.dr/bids/",
                workflow_name,
                acquisitions=["EPI",],
		validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
		)
	df_ = roi.per_session(substitutions_,
		filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
		roi_mask=roi_mask,
		)
	df_['treatment'] = 'Vehicle'
	substitutions__ = bids_substitution_iterator(
		["ofM"],
		#["5694","5706",'5704','6455','6459','5794'],
		["6530","6532","6542","6548",'6549','6552','6553','6556','6557'],
		#["6262","6255","56","5706",'5704',],
                ["CogB",],
                "~/ni_data/ofM.dr/bids/",
                workflow_name,
                acquisitions=["EPI",],
		validate_for_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
		)
	df__ = roi.per_session(substitutions__,
		filename_template='{data_dir}/l1/{l1_dir}/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{acquisition}_cbv_tstat.nii.gz',
		roi_mask=roi_mask,
		)
	df__['treatment'] = 'New'

	df = pd.concat([df__,df_,df])
	df = df.rename(columns={'session': 'Session',})

	roi_name = splitext(basename(roi_mask))[0]
	if roi_name[-4:] == '.nii':
		roi_name = roi_name[:-4]
	df.to_csv('~/ni_data/ofM.dr/bids/l1/{}/{}.csv'.format(workflow_name, roi_name))

def label_connectivity(workflow_name='DSURQEc_drp', labels=['cortex']):
	import pandas as pd
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel

	mapping='/usr/share/mouse-brain-atlases/dsurqec_mapping.csv'
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii'
	my_roi = roi_from_atlaslabel(atlas,
		mapping=mapping,
		label_names=labels,
		)

	substitutions = bids_substitution_iterator(
                ["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
                ["CogB",],
                "~/ni_data/ofM.dr/bids",
                workflow_name,
                acquisitions=["EPI",],
		validate_for_template='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		)
	df = roi.per_session(substitutions,
		filename_template='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		roi_mask=my_roi,
		feature=labels,
		atlas=atlas,
		mapping=mapping,
		)
	df['treatment']='Fluoxetine'
	substitutions_ = bids_substitution_iterator(
                ["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		["6262","6255","5694","5706",'5704','6455','6459'],
                ["CogB",],
                "~/ni_data/ofM.dr/bids",
		workflow_name,
                acquisitions=["EPI",],
		validate_for_template='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		)
	df_ = roi.per_session(substitutions_,
		filename_template='{data_dir}/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		roi_mask=my_roi,
		feature=labels,
		atlas=atlas,
		mapping=mapping,
		)
	df_['treatment']='Vehicle'

	df = pd.concat([df_,df])
	df = df.rename(columns={'session': 'Session','t':'z'})

	df.to_csv('~/ni_data/ofM.dr/bids/fc/{}/{}_summary.csv'.format(workflow_name,'-'.join(labels)))

def total_significance():
	from samri.report.snr import iter_significant_signal
	from samri.utilities import bids_autofind

	substitutions = bids_autofind('~/ni_data/ofM.dr/bids/l1/generic/',
		path_template="{bids_dir}/sub-{{subject}}/ses-{{session}}/sub-{{subject}}_ses-{{session}}_acq-{{acquisition}}_task-{{task}}_cbv_pfstat.nii.gz",
		match_regex='.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_acq-(?P<acquisition>.+).*?_task-(?P<task>.+)_cbv_pfstat\.nii.gz',
		)
	iter_significant_signal('~/ni_data/ofM.dr/bids/l1/generic/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_pfstat.nii.gz',
		substitutions=substitutions,
		mask_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
		save_as='~/ni_data/ofM.dr/bids/l1/generic/total_significance.csv'
		)

def test_signal():
	from samri.report.snr import significant_signal

	substitution={"subject":5686,"session":"ofM","task":'CogB'}
	mean, median = significant_signal('~/ni_data/ofM.dr/bids/l1/generic/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-EPI_task-{task}_cbv_pfstat.nii.gz',
		substitution=substitution,
		mask_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
		)
	print(mean,median)

def ctx_pattern_mask_drs_sfc():
	import pandas as pd
	from samri.plotting import summary
	from samri.report import roi
	from samri.utilities import bids_substitution_iterator
	from samri.fetch.local import roi_from_atlaslabel

	workflow_name = 'drs_seed'
	my_roi = '~/ni_data/ofM.dr/l2/anova_ctx/anova_fstat.nii.gz'

	my_roi = roi.from_img_threshold(my_roi, 2., save_as='~/ni_data/ofM.dr/fc/{}/ctx_pattern_mask.nii.gz'.format(workflow_name))

	substitutions = bids_substitution_iterator(
                ["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		['5691',"5689","5690","5700"],
                ["CogB",],
                "~/ni_data/ofM.dr/",
                workflow_name,
                acquisitions=["EPI",],
                check_file_format='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		)
	subjectdf, voxeldf = roi.per_session(substitutions,
		filename_template='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
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
                check_file_format='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		)
	subjectdf_, voxeldf_ = roi.per_session(substitutions_,
		filename_template='~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz',
		roi_mask=my_roi,
		)
	subjectdf_['treatment']='Vehicle'

	subjectdf=pd.concat([subjectdf_,subjectdf])
	subjectdf=subjectdf.rename(columns={'session': 'Session','t':'z'})

	subjectdf.to_csv('~/ni_data/ofM.dr/fc/{}/ctx_pattern_mask_summary.csv'.format(workflow_name))
