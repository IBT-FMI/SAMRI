def reg_gc():
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import get_scores
	from samri.typesetting import inline_anova

	df = get_scores(
		"~/ni_data/ofM.dr/preprocessing/composite",
		"~/ni_data/templates/DSURQEc_200micron_average.nii",
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
	from samri.report.registration import get_scores
	from samri.typesetting import inline_anova
	from samri.utilities import bids_substitution_iterator

	if autofind:
		path_template, substitutions = bids_autofind("~/ni_data/ofM.dr/preprocessing/composite","func")
	else:
		path_template = "{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_cbv.nii.gz"
		substitutions = bids_substitution_iterator(
			["ofM", "ofMaF", "ofMcF1", "ofMcF2", "ofMpF"],
			["5689","5690","5691","5694","5706","5700","5704","6255","6262"],
			["CogB"],
			"~/ni_data/ofM.dr/",
			"composite",
			acquisitions=['EPI'],
			check_file_format=path_template,
			)

	df = get_scores(path_template, substitutions,
		"~/ni_data/templates/DSURQEc_200micron_average.nii",
		metric="CC",
		radius_or_number_of_bins=radius,
		sampling_strategy="Regular",
		sampling_percentage=0.33,
		save_as="f_reg_quality.csv",
		)
def reg_cc(
	radius=5,
	autofind=False,
	plot=False,
	):
	from samri.utilities import bids_autofind
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import get_scores
	from samri.typesetting import inline_anova
	from samri.utilities import bids_substitution_iterator

	if autofind:
		path_template, substitutions = bids_autofind("~/ni_data/ofM.dr/preprocessing/composite","func")
	else:
		path_template = "{data_dir}/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_trial-{trial}_cbv.nii.gz"
		substitutions = bids_substitution_iterator(
			["ofM", "ofMaF", "ofMcF1", "ofMcF2", "ofMpF"],
			["4001","4007","4008","4011","5692","5694","5699","5700","5704","6255","6262"],
			["CogB","JogB"],
			"~/ni_data/ofM.dr/",
			"composite",
			acquisitions=['EPI'],
			check_file_format=path_template,
			)

	df = get_scores(path_template, substitutions,
		"~/ni_data/templates/DSURQEc_200micron_average.nii",
		metric="CC",
		radius_or_number_of_bins=radius,
		sampling_strategy="Regular",
		sampling_percentage=0.33,
		save_as="f_reg_quality.csv",
		)

	if plot:
		anova_summary = registration_qc(df,
			value={"similarity":"Similarity"},
			group={"sub":"Subject"},
			repeat={"ses":"Session"},
			extra={"trial":"Type"},
			model="{value} ~ C({extra}) + C({repeat}) + C({group}) -1",
			save_as="registration_qc.png",
			print_model=True,
			print_anova=True,
			show=False,
			)

		subject_effect = inline_anova(anova_summary,"C(Subject)",style="python")
		print("Subject Main Effect: {}".format(subject_effect))
		session_effect = inline_anova(anova_summary,"C(Session)",style="python", max_len=2)
		print("Session Main Effect: {}".format(session_effect))
		type_effect = inline_anova(anova_summary,"C(Type)",style="python")
		print("Scan Type Main Effect: {}".format(type_effect))

def metadata():
	from samri.pipelines.extra_functions import get_data_selection
	info = get_data_selection('~/ni_data/test')
	print(info)

def test_autofind():
	"""We may be able to turn this into a CI function, if we put together a data fetching script for dummy (empty) BIDS-formatted data.
	"""
	from samri.utilities import bids_autofind
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import get_scores
	from samri.typesetting import inline_anova
	from samri.utilities import bids_substitution_iterator

	path_template, substitutions = bids_autofind("~/ni_data/ofM.dr/preprocessing/composite","func")

	df = get_scores(path_template, substitutions,
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
