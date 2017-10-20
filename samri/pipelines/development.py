from os import path
import preprocessing, glm, fc
try:
	from ..utilities import bids_substitution_iterator
except (SystemError, ValueError):
	from samri.utilities import bids_substitution_iterator

def dbu(
	data_path="~/ni_data/DBu/",
	workflow_name="functional_registration",
	preprocessing_dir="preprocessing",
	):
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

def bids_test():
	preprocessing.bruker('~/ni_data/test/',
		functional_scan_types=["CogB","CogB2m","jb_long"],
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

def cbv_composite(data_path,workflow_name,
	preprocessing_dir="preprocessing",
	l1_dir="l1",
	):
	preprocessing.bruker(data_path,
		#exclude_measurements=['20151027_121613_4013_1_1'],
		functional_scan_types=["EPI_CBV_chr_longSOA","EPI_CBV_jb_long"],
		#subjects=["4007","4008","4011","4012","5687","5688","5695","5689","5690","5691","5703","5704","5706"],
		#subjects=["4007","4008","5687","5688","5704",
		#	"5692","6262","5694","5700","6255","5699"],
		#subjects=["4001","4011","5703","5706",],
		workflow_name=workflow_name,
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
	glm.l1(path.join(data_path,preprocessing_dir,workflow_name),
		workflow_name=workflow_name,
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True,
		)
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="composite_subjects",
		exclude={"scans":["EPI_BOLD_"],},
		groupby="subject",
		keep_work=True,
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		)
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="composite_sessions_responders",
		exclude={"scans":["EPI_BOLD_"],"subjects":["4001","4002","4003","4004","4006","4008","4009","5674","5703","5704","5706"]},
		groupby="session",
		keep_work=True,
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		)

def typical_resp(data_path='~/ni_data/ofM.dr/', l1_dir='l1', workflow_name='composite'):
	glm.l2_common_effect(path.join(data_path,l1_dir,workflow_name),
		workflow_name="sessions_best_responders",
		subjects=["5689","5690","5691","5700","6262","6255","5694","5706"],
		trials=["EPI_CBV_chr_longSOA"],
		groupby="session",
		keep_work=True,
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		)


def dr_only():
	glm.l1("~/ni_data/ofM.dr/preprocessing/_composite",
		mask="/home/chymera/ni_data/templates/roi/f_dr_chr.nii.gz",
		workflow_name="dr",
		# include={"subjects":["5689","5690","5691"]},
		habituation="confound",
		keep_work=True,
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

def test_dual_regression(group_level="migp"):
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
	glm.l1(preprocessing_dir='~/bandpass_ni_data/rsfM/preprocessing/composite',
		workflow_name='as_composite',
		habituation='confound',
		mask="/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii.gz",
		keep_work=True)

if __name__ == '__main__':
	# test_dual_regression()
#	vta_composite()
	cbv_composite("~/ni_data/ofM.dr/","composite")
#	dr_only()
#	run_level1_glm()
