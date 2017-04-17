import preprocessing, glm

def cbv_composite():
	preprocessing.bruker("/home/chymera/ni_data/ofM.dr/",
		exclude_measurements=['20151027_121613_4013_1_1'],
		functional_scan_types=["EPI_CBV_chr_longSOA","EPI_CBV_jb_long"],
		#subjects=["4007","4008",],
		subjects=["4007","4008","4011","4012","5689","5690","5691"],
		workflow_name="composite",
		very_nasty_bruker_delay_hack=True,
		negative_contrast_agent=True,
		functional_blur_xy=4,
		functional_registration_method="composite",
		keep_work=True,
		template="~/ni_data/templates/DSURQEc_200micron_average.nii",
		)
	glm.l1("~/ni_data/ofM.dr/preprocessing/composite",
		workflow_name="composite",
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii",
		keep_work=True,
		)
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite",
		workflow_name="composite_subjects",
		exclude={"scans":["EPI_BOLD_"]},
		groupby="subject",
		keep_work=True,
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii",
		)
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite",
		workflow_name="composite_sessions",
		exclude={"scans":["EPI_BOLD_"]},
		groupby="session",
		keep_work=True,
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii",
		)

def dr_composite():
	preprocessing.bruker("/home/chymera/ni_data/ofM.dr/",exclude_measurements=['20151027_121613_4013_1_1'], workflow_name="composite", very_nasty_bruker_delay_hack=True, negative_contrast_agent=True, functional_blur_xy=4, functional_registration_method="composite")
	glm.l1("~/ni_data/ofM.dr/preprocessing/composite", workflow_name="composite", include={"subjects":[i for i in range(4001,4010)]+[4011,4012]}, habituation="confound",mask="/home/chymera/ni_data/templates/ds_QBI_chr_bin.nii.gz",keep_work=True)
	glm.l1("~/ni_data/ofM.dr/preprocessing/composite", workflow_name="composite_dr", include={"subjects":[i for i in range(4001,4010)]+[4011,4012]}, habituation="confound",mask="/home/chymera/ni_data/templates/roi/f_dr_chr_bin.nii.gz",)
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite", workflow_name="subjectwise_composite", groupby="subject")
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite", workflow_name="sessionwise_composite", groupby="session", exclude={"subjects":["4001","4002","4003","4004","4005","4006","4009","4011","4013"]})
	glm.l2_common_effect("~/ni_data/ofM.dr/l1/composite", workflow_name="sessionwise_composite_w4011", groupby="session", exclude={"subjects":["4001","4002","4003","4004","4005","4006","4009","4013"]})
def vta_composite():
	preprocessing.bruker("/home/chymera/ni_data/ofM.vta/",workflow_name="composite", very_nasty_bruker_delay_hack=False, negative_contrast_agent=True, functional_blur_xy=4, functional_registration_method="composite")

if __name__ == '__main__':
	# vta_composite()
	cbv_composite()
