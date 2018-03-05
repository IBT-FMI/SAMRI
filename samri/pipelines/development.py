from os import path
import pandas as pd
from samri.utilities import bids_substitution_iterator

def higher():
	glm.l1('~/ni_data/test/preprocessing/composite',
		workflow_name='higher',
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True,
		)

def dbu(
	data_path="~/ni_data/DBu/",
	workflow_name="functional_registration",
	preprocessing_dir="preprocessing",
	):
	from samri.pipelines import preprocess, glm
	preprocessing.bruker(data_path,
		functional_scan_types=["3GE_EPI_ET_mAb911_1Rep",],
		structural_scan_types=-1,
		workflow_name=workflow_name,
		lowpass_sigma=2,
		highpass_sigma=225,
		functional_blur_xy=.4,
		functional_registration_method="functional",
		keep_work=True,
		template="~/ni_data/templates/DSURQEc_200micron_average.nii",
		registration_mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		actual_size=True,
		verbose=True,
		)

def rs(
	data_path="~/ni_data/_test/",
	workflow_name="functional_registration",
	preprocessing_dir="preprocessing",
	):
	from samri.pipelines import preprocess, glm
	preprocessing.bruker(data_path,
		functional_scan_types=["EPI_CBV",],
		structural_scan_types=-1,
		workflow_name=workflow_name,
		lowpass_sigma=2,
		highpass_sigma=225,
		functional_blur_xy=.4,
		functional_registration_method="functional",
		keep_work=True,
		template="~/ni_data/templates/DSURQEc_200micron_average.nii",
		registration_mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		actual_size=True,
		)

def ss():
	from samri.pipelines import preprocess, glm
	preprocessing.bruker('~/ni_data/ss/',
		functional_match={'task':['FshSbu','FshSbb']},
		structural_match={'acquisition':['TurboRARE']},
		workflow_name='composite',
		lowpass_sigma=2,
		highpass_sigma=225,
		very_nasty_bruker_delay_hack=True,
		negative_contrast_agent=True,
		functional_blur_xy=.4,
		functional_registration_method="composite",
		keep_work=True,
		template="~/ni_data/templates/DSURQEc_200micron_average.nii",
		registration_mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		actual_size=True,
		verbose=True,
		)

def aic():
	from samri.pipelines import preprocess, glm
	preprocessing.bruker('~/ni_data/test/',
		functional_match={'task':['CogB','CogB2m','JogB']},
		structural_match={'acquisition':['TurboRARE','TurboRARElowcov']},
		workflow_name='composite',
		lowpass_sigma=2,
		highpass_sigma=225,
		very_nasty_bruker_delay_hack=True,
		negative_contrast_agent=True,
		functional_registration_method="composite",
		keep_work=True,
		template="~/ni_data/templates/DSURQEc_200micron_average.nii",
		registration_mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		actual_size=True,
		verbose=True,
		)
	glm.l1('~/ni_data/test/preprocessing/composite',
		workflow_name='composite',
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True,
		)

def bids_preprocessing():
	from samri.pipelines.preprocess import bruker
	bids_base = '~/ni_data/ofM.dr/'

	bruker(bids_base, "~/ni_data/templates/DSURQEc_40micron_average.nii",
		functional_match={'task':['CogB',],},
		structural_match={'acquisition':['TurboRARE',]},
		subjects=['5700'],
		actual_size=True,
		functional_registration_method="composite",
		)

def cbv_composite(data_path="~/ni_data/ofM.dr/",
	workflow_name='composite',
	preprocessing_dir="preprocessing",
	l1_dir="l1",
	):
	from samri.pipelines import preprocess, glm
	#preprocessing.bruker(data_path,
	#	#exclude_measurements=['20151027_121613_4013_1_1'],
	#	functional_match={'task':['CogB','JogB']},
	#	structural_match={'acquisition':['TurboRARE','TurboRARElowcov']},
	#	#subjects=["4007","4008","4011","4012","5687","5688","5695","5689","5690","5691","5703","5704","5706"],
	#	#subjects=["4007","4008","5687","5688","5704",
	#	#	"5692","6262","5694","5700","6255","5699"],
	#	#subjects=["4001","4011","5703","5706",],
	#	workflow_name=workflow_name,
	#	lowpass_sigma=2,
	#	highpass_sigma=225,
	#	very_nasty_bruker_delay_hack=True,
	#	negative_contrast_agent=True,
	#	functional_blur_xy=.4,
	#	functional_registration_method="composite",
	#	keep_work=True,
	#	template="~/ni_data/templates/DSURQEc_200micron_average.nii",
	#	registration_mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
	#	actual_size=True,
	#	verbose=True,
	#	)
	#glm.l1(path.join(data_path,preprocessing_dir,workflow_name),
	#	workflow_name=workflow_name,
	#	# include={"subjects":["5689","5690","5691"]},
	#	habituation="confound",
	#	mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
	#	keep_work=True,
	#	)
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="composite_subjects",
		groupby="subject",
		keep_work=True,
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		)
	#glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
	#	workflow_name="composite_sessions_responders",
	#	exclude={"scans":["EPI_BOLD_"],"subjects":["4001","4002","4003","4004","4006","4008","4009","5674","5703","5704","5706"]},
	#	groupby="session",
	#	keep_work=True,
	#	mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
	#	)

def anova_fc():
	from samri.pipelines import preprocess, glm
	glm.l2_anova("~/ni_data/ofM.dr/fc/drs_seed/",
		workflow_name="anova_fc",
		keep_work=True,
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		include={
			'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
			'subject':['5691',"5689","5690","5700"],
			},
		)
def anova():
	from samri.fetch.local import roi_from_atlaslabel
	from samri.pipelines import preprocess, glm
	roi = roi_from_atlaslabel("~/ni_data/templates/roi/DSURQEc_200micron_labels.nii",
		mapping="~/ni_data/templates/roi/DSURQE_mapping.csv",
		label_names=["cortex"],
		save_as="/tmp/ctx.nii.gz")
	glm.l2_anova("~/ni_data/ofM.dr/l1/composite/",
		workflow_name="anova_ctx",
		keep_work=False,
		mask="/tmp/ctx.nii.gz",
		include={
			'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
			'subject':['5691',"5689","5690","5700"],
			},
		)
	#glm.l2_anova("~/ni_data/ofM.dr/l1/composite/",
	#	workflow_name="anova_drs",
	#	keep_work=False,
	#	mask="~/ni_data/templates/roi/DSURQEc_drs.nii.gz",
	#	include={
	#		'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
	#		'subject':['5691',"5689","5690","5700"],
	#		},
	#	)
	#glm.l2_anova("~/ni_data/ofM.dr/l1/composite/",
	#	workflow_name="anova_dr",
	#	keep_work=False,
	#	mask="~/ni_data/templates/roi/DSURQEc_dr.nii.gz",
	#	include={
	#		'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
	#		'subject':['5691',"5689","5690","5700"],
	#		},
	#	)
	#glm.l2_anova("~/ni_data/ofM.dr/l1/composite/",
	#	workflow_name="anova_control",
	#	keep_work=False,
	#	mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
	#	include={
	#		'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
	#		'subject':["6262","6255","5694","5706",'5704'],
	#		},
	#	)
	#glm.l2_anova("~/ni_data/ofM.dr/l1/composite/",
	#	workflow_name="anova",
	#	keep_work=False,
	#	mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
	#	include={
	#		'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
	#		'subject':['5691',"5689","5690","5700"],
	#		},
	#	)

def typical_resp(data_path='~/ni_data/ofM.dr/', l1_dir='l1', workflow_name='composite'):
	from samri.pipelines import preprocess, glm
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="best_responders_old",
		include={
			'subject':["5689","5690","5691","5700","6262","6255","5694","5706"],
			'task':["CogB"],
			},
		groupby="session",
		keep_work=True,
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		)
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="best_responders",
		include={
			'subject':["5699","5687","5691","5694","4005","6255","5706"],
			'task':["CogB"],
			},
		groupby="session",
		keep_work=True,
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		)


def dr_only():
	from samri.pipelines import preprocess, glm
	glm.l1("~/ni_data/ofM.dr/preprocessing/_composite",
		mask="~/ni_data/templates/roi/f_dr_chr.nii.gz",
		workflow_name="dr",
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		keep_work=True,
		)

def dr_composite():
	from samri.pipelines import preprocess, glm
	preprocessing.bruker("~/ni_data/ofM.dr/",exclude_measurements=['20151027_121613_4013_1_1'], workflow_name="composite", very_nasty_bruker_delay_hack=True, negative_contrast_agent=True, functional_blur_xy=4, functional_registration_method="composite")
	glm.l1("~/ni_data/ofM.dr/preprocessing/composite", workflow_name="composite", include={"subjects":[i for i in range(4001,4010)]+[4011,4012]}, habituation="confound",mask="~/ni_data/templates/ds_QBI_chr_bin.nii.gz",keep_work=True)
	glm.l1("~/ni_data/ofM.dr/preprocessing/composite", workflow_name="composite_dr", include={"subjects":[i for i in range(4001,4010)]+[4011,4012]}, habituation="confound",mask="~/ni_data/templates/roi/f_dr_chr_bin.nii.gz",)
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite", workflow_name="subjectwise_composite", groupby="subject")
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite", workflow_name="sessionwise_composite", groupby="session", exclude={"subjects":["4001","4002","4003","4004","4005","4006","4009","4011","4013"]})
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite", workflow_name="sessionwise_composite_w4011", groupby="session", exclude={"subjects":["4001","4002","4003","4004","4005","4006","4009","4013"]})
def vta_composite():
	from samri.pipelines import preprocess, glm
	preprocessing.bruker("~/ni_data/ofM.vta/",workflow_name="composite", very_nasty_bruker_delay_hack=False, negative_contrast_agent=True, functional_blur_xy=4, functional_registration_method="composite")

def test_dual_regression(group_level="migp"):
	from samri.analysis import fc
	substitutions_a = bids_substitution_iterator(
		["ofM",],
		["5689","5690","5691"],
		["EPI_CBV_chr_longSOA"],
		"~/ni_data/ofM.dr/",
		"as_composite",
		)
	substitutions_b = bids_substitution_iterator(
		["ofM_cF2",],
		["5689","5690","5691"],
		["EPI_CBV_chr_longSOA"],
		"~/ni_data/ofM.dr/",
		"as_composite",
		)
	fc.dual_regression(substitutions_a,substitutions_b,
		group_level=group_level,
		)
	#fc.get_signal(substitutions_a,substitutions_b

def run_level1_glm():
	from samri.pipelines import preprocess, glm
	glm.l1(preprocessing_dir='~/bandpass_ni_data/rsfM/preprocessing/composite',
		workflow_name='as_composite',
		habituation='confound',
		mask="~/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True)
