import nibabel
import nipype.interfaces.io as nio
from os import path, listdir, getcwd, remove

#from nilearn.input_data import NiftiLabelsMasker
#from nilearn.connectome import ConnectivityMeasure
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
	ica_run = ica.run()


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
