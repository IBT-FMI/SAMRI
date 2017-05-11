import nibabel
import numpy as np
import nipype.interfaces.io as nio
from os import path, listdir, getcwd, remove


from nilearn.input_data import NiftiLabelsMasker, NiftiMasker
from nilearn.connectome import ConnectivityMeasure
from nipype.interfaces import fsl

def dual_regression(substitutions_a, substitutions_b,
	all_merged_path="~/all_merged.nii.gz",
	components=9,
	group_level="concat",
	tr=1,
	ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	):

	all_merged_path = path.abspath(path.expanduser(all_merged_path))

	ts_a = []
	for substitution in substitutions_a:
		ts_a.append(path.abspath(path.expanduser(ts_file_template.format(**substitution))))
	ts_b = []
	for substitution in substitutions_b:
		ts_b.append(path.abspath(path.expanduser(ts_file_template.format(**substitution))))

	ts_all = ts_a + ts_b
	if group_level == "concat" and not path.isfile(all_merged_path):
		ts_all_merged = nibabel.concat_images(ts_all, axis=3)
		ts_all_merged.to_filename(all_merged_path)

	ica = fsl.model.MELODIC()
	ica.inputs.report = True
	ica.inputs.tr_sec = tr
	ica.inputs.no_bet = True
	ica.inputs.no_mask = True
	ica.inputs.sep_vn = True
	if components:
		ica.inputs.dim = int(components)
	if group_level == "migp":
		ica.inputs.in_files = ts_all
		ica._cmd = 'melodic --migp'
	elif group_level == "concat":
		ica.inputs.approach = "concat"
		ica.inputs.in_files = all_merged_path
	print(ica.cmdline)
	ica_run = ica.run

def get_signal(substitutions_a, substitutions_b,
	functional_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	mask="~/ni_data/templates/DSURQEc_200micron_bin.nii.gz",
	):

	mask = path.abspath(path.expanduser(mask))

	out_t_names = []
	out_cope_names = []
	out_varcb_names = []
	for substitution in substitutions_a+substitutions_b:
		ts_name = path.abspath(path.expanduser("{subject}_{session}.mat".format(**substitution)))
		out_t_name = path.abspath(path.expanduser("{subject}_{session}_tstat.nii.gz".format(**substitution)))
		out_cope_name = path.abspath(path.expanduser("{subject}_{session}_cope.nii.gz".format(**substitution)))
		out_varcb_name = path.abspath(path.expanduser("{subject}_{session}_varcb.nii.gz".format(**substitution)))
		out_t_names.append(out_t_name)
		out_cope_names.append(out_cope_name)
		out_varcb_names.append(out_varcb_name)
		functional_file = path.abspath(path.expanduser(functional_file_template.format(**substitution)))
		if not path.isfile(ts_name):
			masker = NiftiMasker(mask_img=mask)
			ts = masker.fit_transform(functional_file).T
			ts = np.mean(ts, axis=0)
			header = "/NumWaves 1\n/NumPoints 1490\n/PPheights 1.308540e+01 4.579890e+00\n\n/Matrix"
			np.savetxt(ts_name, ts, delimiter="\n", header=header, comments="")
		glm = fsl.GLM(in_file=functional_file, design=ts_name, output_type='NIFTI_GZ')
		glm.inputs.contrasts = path.abspath(path.expanduser("run0.con"))
		glm.inputs.out_t_name = out_t_name
		glm.inputs.out_cope = out_cope_name
		glm.inputs.out_varcb_name = out_varcb_name
		print(glm.cmdline)
		glm_run=glm.run()

	copemerge = fsl.Merge(dimension='t')
	varcopemerge = fsl.Merge(dimension='t')


def correlation_matrix(func_data,
	mask="/home/chymera/NIdata/templates/ds_QBI_chr_bin.nii.gz",
	labels = '',
	loud = False,
	):

	labels_masker = NiftiLabelsMasker(labels_img=mask, verbose=loud)

	timeseries = labels_masker.fit_transform(func_data)

	correlation_measure = ConnectivityMeasure(kind='correlation')
	correlation_matrix = correlation_measure.fit_transform([timeseries])[0]

	np.save(correlation_matrix, 'correlation_matrix.csv')
