def dr_full():
	from labbookdb.report.development import animal_multiselect
	from samri.pipelines import glm
	from samri.pipelines.preprocess import bruker
	from samri.report.snr import iter_significant_signal
	from samri.utilities import bids_autofind

	bids_base = '~/ni_data/ofM.dr/bids'

	animal_list = animal_multiselect(cage_treatments=['cFluDW','cFluDW_','cFluIP'])
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['cbv',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=animal_list,
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=True,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['bold',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=animal_list,
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=False,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	# Animal list selection needs fixing in LabbookDB database, so we do the following animals manually
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['cbv',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=['4001','4005','4006','4007','4008','4009','4011','4012','4013'], # Known Resoponders
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=True,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['bold',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=['4001','4005','4006','4007','4008','4009','4011','4012','4013'], # Known Resoponders
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=False,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	glm.l1('~/ni_data/ofM.dr/preprocessing/generic',
		out_dir='~/ni_data/ofM.dr/l1',
		workflow_name='generic',
		habituation="confound",
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True,
		)

	substitutions = bids_autofind('~/ni_data/ofM.dr/bids/l1/generic/',
		path_template="{bids_dir}/sub-{{subject}}/ses-{{session}}/sub-{{subject}}_ses-{{session}}_acq-{{acquisition}}_task-{{task}}_cbv_pfstat.nii.gz",
		match_regex='.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/.*?_acq-(?P<acquisition>.+).*?_task-(?P<task>.+)_cbv_pfstat\.nii.gz',
		)
	iter_significant_signal('~/ni_data/ofM.dr/bids/l1/generic/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_pfstat.nii.gz',
		substitutions=substitutions,
		mask_path='~/ni_data/templates/DSURQEc_200micron_mask.nii.gz',
		save_as='~/ni_data/ofM.dr/bids/l1/generic/total_significance.csv'
		)
def more():
	from labbookdb.report.development import animal_multiselect
	from samri.pipelines import glm
	from samri.pipelines.preprocess import bruker
	from samri.report.snr import iter_significant_signal
	from samri.utilities import bids_autofind

	bids_base = '~/ni_data/ofM.dr/bids'
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['cbv',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=['4001','4005','4006','4007','4008','4009','4011','4012','4013'], # Known Resoponders
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=True,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		functional_match={'type':['bold',],},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov'],},
		subjects=['4001','4005','4006','4007','4008','4009','4011','4012','4013'], # Known Resoponders
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=False,
		out_dir='~/ni_data/ofM.dr/preprocessing',
		)
	glm.l1('~/ni_data/ofM.dr/preprocessing/generic',
		out_dir='~/ni_data/ofM.dr/l1',
		workflow_name='generic',
		habituation="confound",
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True,
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
		"~/ni_data/templates/DSURQEc_200micron_average.nii",
		metric="CC",
		radius_or_number_of_bins=radius,
		sampling_strategy="Regular",
		sampling_percentage=0.33,
		save_as="f_reg_quality.csv",
		)

def reg_cc(
        path = "~/ni_data/ofM.dr/preprocessing/composite",
        template = "~/ni_data/templates/DSURQEc_200micron_average.nii",
        radius=5,
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


def metadata():
	from samri.pipelines.extra_functions import get_data_selection
	info = get_data_selection('~/ni_data/test')
	print(info)

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
		"~/ni_data/templates/DSURQEc_200micron_average.nii",
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
