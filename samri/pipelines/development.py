# -*- coding: utf-8 -*-

# Development work, e.g. for higher level functions.
# These functions are not intended to work on any machine or pass the tests.
# They are early drafts (e.g. of higher level workflows) intended to be shared among select collaborators or multiple machines of one collaborator.
# Please don't edit functions which are not yours, and only perform imports in local scope.

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
		template="/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		registration_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
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
		template="/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		registration_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
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
		template="/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		registration_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
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
		template="/usr/share/mouse-brain-atlases/dsurqec_200micron.nii",
		registration_mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		actual_size=True,
		verbose=True,
		)
	glm.l1('~/ni_data/test/preprocessing/composite',
		workflow_name='composite',
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		keep_work=True,
		)

def glm_only():
	from samri.pipelines import glm
	glm.l1('~/ni_data/ofM.vta/bids/',
		workflow_name='composite',
		include={"subject":["SN2143","SN2145","SN3974","SN3975"]},
		habituation="confound",
		keep_work=True,
		mask="",
		)

def bids_preprocessing():
	from samri.pipelines.preprocess import bruker
	from labbookdb.report.development import animal_multiselect

	bids_base = '~/ni_data/ofM.dr/bids'

	animal_list = animal_multiselect()
	bruker(bids_base, "~/ni_data/templates/dsurqec_200micron.nii",
		registration_mask="~/ni_data/templates/dsurqec_200micron_mask.nii",
		#functional_match={'acquisition':['EPIlowcov',],},
		#structural_match={'acquisition':['TurboRARElowcov',]},
		#functional_match={'task':['JogB','CogB',],'acquisition':['EPI',],},
		#functional_match={'task':['JogB','CogB',],'acquisition':['EPIlowcov',],},
		#functional_match={'task':['JogB'],'type':['cbv']},
		#structural_match={'acquisition':['TurboRARElowcov']},
		#subjects=animal_list,
		#subjects=['6530','6532','6542','6548','6549','6552','6553','6556','6557'],
		subjects=['5673','5668','5675','6557'],
		actual_size=True,
		functional_registration_method="composite",
		negative_contrast_agent=True,
		)

def legacy_preprocessing():
	from samri.pipelines.preprocess import legacy_bruker
	bids_base = '~/ni_data/ofM.dr/bids'

	legacy_bruker(bids_base, "~/ni_data/templates/lambmc_180micron.nii",
		#functional_match={'acquisition':['EPIlowcov',],},
		structural_match={'acquisition':['TurboRARElowcov',]},
		functional_match={'task':['JogB','CogB'],'acquisition':['EPIlowcov',]},
		#functional_match={'task':['JogB','CogB',],'acquisition':['EPI',],},
		#functional_match={'task':['JogB','CogB',],'acquisition':['EPIlowcov',],},
		#functional_match={'task':['JogB'],'type':['cbv']},
		#structural_match={'acquisition':['TurboRARElowcov']},
		#subjects=['5667','6542'],
		#subjects=['6530','6532','6542','6548','6549','6552','6553','6556','6557'],
		functional_registration_method="functional",
		negative_contrast_agent=False,
		workflow_name='legacy',
		keep_work=True,
		)

def anova_fc():
	from samri.pipelines import preprocess, glm
	glm.l2_anova("~/ni_data/ofM.dr/fc/drs_seed/",
		workflow_name="anova_fc",
		keep_work=True,
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		include={
			'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
			'subject':['5691',"5689","5690","5700"],
			},
		)
def anova():
	from samri.fetch.local import roi_from_atlaslabel
	from samri.pipelines import preprocess, glm
	#roi = roi_from_atlaslabel("/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii",
	#	mapping="/usr/share/mouse-brain-atlases/dsurqec_mapping.csv",
	#	label_names=["cortex"],
	#	save_as="/tmp/ctx.nii.gz")
	glm.l2_anova("~/ni_data/ofM.dr/bids/l1/generic/",
		workflow_name="anova",
		keep_work=False,
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		include={
			'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
			'subject':['5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
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
	#	mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	#	include={
	#		'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
	#		'subject':["6262","6255","5694","5706",'5704'],
	#		},
	#	)
	#glm.l2_anova("~/ni_data/ofM.dr/l1/composite/",
	#	workflow_name="anova",
	#	keep_work=False,
	#	mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
	#	include={
	#		'session':['ofM','ofMaF','ofMcF1','ofMcF2','ofMpF'],
	#		'subject':['5691',"5689","5690","5700"],
	#		},
	#	)

def typical_resp(data_path='~/ni_data/ofM.dr/bids/', l1_dir='l1', workflow_name='generic'):
	from samri.pipelines import preprocess, glm
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="best_responders",
		include={
			'subject':["6262","6255","5694","5706",'5704','6455','6459','5691',"5689","5690","5700","6451","6460","6456","6461","6462"],
			'task':["CogB"],
			},
		groupby="session",
		keep_work=True,
		mask="/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		)

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

