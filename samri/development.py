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

def reg_cc3():
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import get_scores
	from samri.typesetting import inline_anova

	df = get_scores(
		"~/ni_data/ofM.dr/preprocessing/composite",
		"~/ni_data/templates/DSURQEc_200micron_average.nii",
		metric="CC",
		radius_or_number_of_bins = 3,
		sampling_strategy = "Regular",
		sampling_percentage=0.33,
		save_as=False,
		)

	anova_summary = registration_qc(df,
		value={"similarity":"Similarity"},
		group={"sub":"Subject"},
		repeat={"ses":"Session"},
		show=False,
		save_as="/tmp/f_reg_cc3.png",
		)

	subject_effect = inline_anova(anova_summary,"C(Subject)",style="python")
	print("Subject Main Effect: {}".format(subject_effect))
	session_effect = inline_anova(anova_summary,"C(Session)",style="python")
	print("Session Main Effect: {}".format(session_effect))

def reg_cc10():
	from samri.plotting.aggregate import registration_qc
	from samri.report.registration import get_scores
	from samri.typesetting import inline_anova
	from samri.utilities import bids_substitution_iterator

	substitutions = bids_substitution_iterator(
		["ofM", "ofM_aF", "ofM_cF1", "ofM_cF2", "ofM_pF"],
		["4007","4008","5692","5694","5699","5700","5704","6255","6262"],
		["EPI_CBV_chr_longSOA","EPI_CBV_jb_long"],
		"~/ni_data/ofM.dr/",
		"composite",
		)
	file_template = "~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{trial}.nii.gz"

	df = get_scores(file_template, substitutions,
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
