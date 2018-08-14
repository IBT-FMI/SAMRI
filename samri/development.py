# -*- coding: utf-8 -*-

# Development work, e.g. for higher level functions.
# These functions are not intended to work on any machine or pass the tests.
# They are early drafts (e.g. of higher level workflows) intended to be shared among select collaborators or multiple machines of one collaborator.
# Please don't edit functions which are not yours, and only perform imports in local scope.

def vta_full(
	workflow_name='generic',
	):
	from labbookdb.report.development import animal_multiselect
	from samri.pipelines import glm
	from samri.pipelines.preprocess import full_prep
	from samri.report.snr import iter_significant_signal
	from samri.utilities import bids_autofind

	# Assuming data cobnverted to BIDS
	bids_base = '~/ni_data/ofM.vta/bids'

	#full_prep(bids_base, "/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
	#	registration_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	#	functional_match={'type':['cbv',],},
	#	structural_match={'acquisition':['TurboRARE']},
	#	actual_size=True,
	#	functional_registration_method='composite',
	#	negative_contrast_agent=True,
	#	out_dir='~/ni_data/ofM.vta/preprocessing',
	#	workflow_name=workflow_name,
	#	)
	#glm.l1('~/ni_data/ofM.vta/preprocessing/generic',
	#	out_dir='~/ni_data/ofM.vta/l1',
	#	workflow_name=workflow_name,
	#	habituation="confound",
	#	mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	#	# We need the workdir to extract the betas
	#	keep_work=True,
	#	)

	# Determining Responders by Significance
	path_template, substitutions = bids_autofind('~/ni_data/ofM.vta/l1/generic/',
		path_template="{bids_dir}/sub-{{subject}}/ses-{{session}}/sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_cbv_pfstat.nii.gz",
		match_regex='.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_task-(?P<task>.+).*?_acq-(?P<acquisition>.+)_cbv_pfstat\.nii.gz',
		)
	print(substitutions)
	iter_significant_signal(path_template,
		substitutions=substitutions,
		mask_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
		save_as='~/ni_data/ofM.dr/vta/generic/total_significance.csv'
		)

def dr_full():
	from labbookdb.report.development import animal_multiselect
	from samri.pipelines import glm
	from samri.pipelines.preprocess import bruker
	from samri.report.snr import iter_significant_signal
	from samri.utilities import bids_autofind

	# Assuming data cobnverted to BIDS
	bids_base = '~/ni_data/ofM.dr/bids'

	# Preprocess
	animal_list = animal_multiselect(cage_treatments=['cFluDW','cFluDW_','cFluIP'])
	# Animal list selection needs fixing in LabbookDB database, so we add the following animals manually
	animal_list.extend(['4001','4002','4003','4004','4005','4006','4007','4008','4009','4011','4012','4013','6557'])
	full_prep(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['cbv',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=animal_list,
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=True,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	#bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
	#	registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
	#	functional_match={'type':['bold',],},
	#	structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
	#	subjects=animal_list,
	#	actual_size=True,
	#	functional_registration_method="composite",
	#	negative_contrast_agent=False,
	#	out_dir='~/ni_data/ofM.dr/preprocessing',
	#	)
	# Model fitting
	glm.l1('~/ni_data/ofM.dr/preprocessing/generic',
		out_dir='~/ni_data/ofM.dr/l1',
		workflow_name='generic',
		habituation="confound",
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		# We need the workdir to extract the betas
		keep_work=True,
		)

	# Determining Responders by Significance
	substitutions = bids_autofind('~/ni_data/ofM.dr/l1/generic/',
		path_template="{bids_dir}/sub-{{subject}}/ses-{{session}}/sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_cbv_pfstat.nii.gz",
		match_regex='.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_task-(?P<task>.+).*?_acq-(?P<acquisition>.+)_cbv_pfstat\.nii.gz',
		)
	iter_significant_signal('~/ni_data/ofM.dr/l1/generic/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{{acquisition}}_cbv_pfstat.nii.gz',
		substitutions=substitutions,
		mask_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
		save_as='~/ni_data/ofM.dr/l1/generic/total_significance.csv'
		)

	# Determining Responders by a priori pattern
	glm.l2_common_effect('~/ni_data/ofM.dr/l1/',
		workflow_name="a_priori_responders",
		include={
			'subject':['4001','4005','4006','4007','4008','4009','4011','4012','4013'],
			},
		groupby="session",
		keep_work=True,
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		)
def dr_cont():
	from labbookdb.report.development import animal_multiselect
	from samri.pipelines import glm
	from samri.pipelines.preprocess import bruker
	from samri.report.snr import iter_significant_signal
	from samri.utilities import bids_autofind

	# Assuming data cobnverted to BIDS
	bids_base = '~/ni_data/ofM.dr/bids'

	# Preprocess
	#animal_list = animal_multiselect(cage_treatments=['cFluDW','cFluDW_','cFluIP'])
	# Animal list selection needs fixing in LabbookDB database, so we add the following animals manually
	#animal_list.extend(['4001','4002','4003','4004','4005','4006','4007','4008','4009','4011','4012','4013','6557'])

	# Determining Responders by Significance
	_ , substitutions = bids_autofind('~/ni_data/ofM.dr/l1/generic/',
		path_template="{bids_dir}/sub-{{subject}}/ses-{{session}}/sub-{{subject}}_ses-{{session}}_task-{{task}}_acq-{{acquisition}}_cbv_pfstat.nii.gz",
		match_regex='.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_task-(?P<task>.+).*?_acq-(?P<acquisition>.+)_cbv_pfstat\.nii.gz',
		)
	print(substitutions)
	iter_significant_signal('~/ni_data/ofM.dr/l1/generic/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_task-{task}_acq-{{acquisition}}_cbv_pfstat.nii.gz',
		substitutions=substitutions,
		mask_path='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
		save_as='~/ni_data/ofM.dr/l1/generic/total_significance.csv'
		)

	# Determining Responders by a priori pattern
	glm.l2_common_effect('~/ni_data/ofM.dr/l1/',
		workflow_name="a_priori_responders",
		include={
			'subject':['4001','4005','4006','4007','4008','4009','4011','4012','4013'],
			},
		groupby="session",
		keep_work=True,
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		)

def temporal_qc_separate():
	import matplotlib.pyplot as plt
	import matplotlib.ticker as plticker
	import numpy as np
	import pandas as pd
	from samri.report.snr import base_metrics
	from samri.plotting.timeseries import multi
	from samri.utilities import bids_substitution_iterator

	substitutions = bids_substitution_iterator(
		['testSTIM'],
		['COILphantom'],
		['CcsI'],
		'/home/chymera/ni_data/phantoms/',
		'bids',
		acquisitions=['EPIalladj','EPIcopyadjNODUM','EPIcopyadj','EPImoveGOP'],
		)

	for i in substitutions:
		timecourses  = base_metrics('{data_dir}/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}.nii', i)
		events_df = pd.read_csv('{data_dir}/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_events.tsv'.format(**i), sep='\t')
		multi(timecourses,
			designs=[],
			events_dfs=[events_df],
			subplot_titles='acquisition',
			quantitative=False,
			save_as='temp_{acquisition}.pdf'.format(**i),
			samri_style=True,
			ax_size=[16,6],
			unit_ticking=True,
			)

def temporal_qc_al_in_one():
	import matplotlib.pyplot as plt
	import matplotlib.ticker as plticker
	import numpy as np
	from samri.report.snr import iter_base_metrics
	from samri.plotting.timeseries import multi
	from samri.utilities import bids_substitution_iterator

	substitutions = bids_substitution_iterator(
		['testSTIM'],
		['COILphantom'],
		['CcsI'],
		'/home/chymera/ni_data/phantoms/',
		'bids',
		acquisitions=['EPIalladj','EPIcopyadjNODUM','EPIcopyadj','EPImoveGOP'],
		)

	timecourses  = iter_base_metrics('{data_dir}/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}.nii', substitutions)
	multi(timecourses,
		designs=[],
		events_dfs=[],
		subplot_titles='acquisition',
		quantitative=False,
		save_as="temp_qc.pdf",
		samri_style=True,
		ax_size=[16,6],
		unit_ticking=True,
		)

def reg_gc():
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import iter_measure_sim
	from samri.typesetting import inline_anova

	df = iter_measure_sim(
		"~/ni_data/ofM.dr/preprocessing/composite",
		"~/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii",
		#modality="anat",
		metric="GC",
		radius_or_number_of_bins = 0,
		sampling_strategy = "Regular",
		sampling_percentage=0.5,
		save_as=False,
		)

	anova_summary = registration_qc(df,
		value={"similarity":"Similarity"},
		group={"sub":"Subject"},
		repeat={"ses":"Session"},
		show=False,
		save_as="/tmp/f_reg_gc.png",
		)

	subject_effect = inline_anova(anova_summary,"C(Subject)",style="python")
	print("Subject Main Effect: {}".format(subject_effect))
	session_effect = inline_anova(anova_summary,"C(Session)",style="python")
	print("Session Main Effect: {}".format(session_effect))

def test_reg_qc(
	radius=5,
	autofind=False,
	plot=False,
	):
	"""This could be used as a continuous integration test function once we can distribute demo data."""
	from samri.utilities import bids_autofind
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import iter_measure_sim
	from samri.typesetting import inline_anova
	from samri.utilities import bids_substitution_iterator

	if autofind:
		path_template, substitutions = bids_autofind("~/ni_data/ofM.dr/preprocessing/composite","func")
	else:
		path_template = "{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz"
		substitutions = bids_substitution_iterator(
			["ofM", "ofMaF", "ofMcF1", "ofMcF2", "ofMpF"],
			["5689","5690","5691","5694","5706","5700","5704","6255","6262"],
			["CogB"],
			"~/ni_data/ofM.dr/",
			"composite",
			acquisitions=['EPI'],
			check_file_format=path_template,
			)

	df = iter_measure_sim(path_template, substitutions,
		"/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		metric="CC",
		radius_or_number_of_bins=radius,
		sampling_strategy="Regular",
		sampling_percentage=0.33,
		save_as="f_reg_quality.csv",
		)

def reg_cc(
        path = "~/ni_data/ofM.dr/preprocessing/composite",
        template = "/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
        radius=8,
        autofind=False,
        plot=False,
        save = "f_reg_quality",
        metrics = ['CC','GC','MI'],
        ):
        from samri.utilities import bids_autofind
        from samri.plotting.aggregate import registration_qc
        from samri.report.registration import iter_measure_sim
        from samri.typesetting import inline_anova
        from samri.utilities import bids_substitution_iterator

        if autofind:
                path_template, substitutions = bids_autofind(path,"func")
        else:
                path_template = "{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz"
                substitutions = bids_substitution_iterator(
                        ["ofM", "ofMaF", "ofMcF1", "ofMcF2", "ofMpF"],
                        ["4001","4007","4008","4011","5692","5694","5699","5700","5704","6255","6262"],
                        ["CogB","JogB"],
                        "~/ni_data/ofM.dr/",
                        "composite",
                        acquisitions=['EPI','EPIlowcov'],
                        validate_for_template=path_template,
                        )


        for metric in metrics:
                df = iter_measure_sim(path_template, substitutions,
                        template,
                        metric=metric,
                        radius_or_number_of_bins=radius,
                        sampling_strategy="Regular",
                        sampling_percentage=0.33,
			save_as= save + "_" + metric +  ".csv",
                        )


def test_autofind():
	"""We may be able to turn this into a CI function, if we put together a data fetching script for dummy (empty) BIDS-formatted data.
	"""
	from samri.utilities import bids_autofind
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import iter_measure_sim
	from samri.typesetting import inline_anova
	from samri.utilities import bids_substitution_iterator

	path_template, substitutions = bids_autofind("~/ni_data/ofM.dr/preprocessing/composite","func")

	df = iter_measure_sim(path_template, substitutions,
		"/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		metric="CC",
		radius_or_number_of_bins=10,
		sampling_strategy="Regular",
		sampling_percentage=0.33,
		save_as=False,
		)

	anova_summary = registration_qc(df,
		value={"similarity":"Similarity"},
		group={"sub":"Subject"},
		repeat={"ses":"Session"},
		show=False,
		save_as="/tmp/f_reg_cc10.png",
		)

	subject_effect = inline_anova(anova_summary,"C(Subject)",style="python")
	print("Subject Main Effect: {}".format(subject_effect))
	session_effect = inline_anova(anova_summary,"C(Session)",style="python")
	print("Session Main Effect: {}".format(session_effect))
