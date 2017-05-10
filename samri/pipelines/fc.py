from os import path, listdir, getcwd, remove
import nipype.interfaces.io as nio

from nilearn.input_data import NiftiLabelsMasker
from nilearn.connectome import ConnectivityMeasure

def dual_regression(substitutions_a, substitutions_b,
	ts_file_template="~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_trial-{scan}.nii.gz",
	):

	ts_a = []
	for substitution in substitutions_a:
		ts_a.append(ts_file_template.format(**substitution))
	ts_b = []
	for substitution in substitutions_b:
		ts_b.append(ts_file_template.format(**substitution))
	ts_all = ts_a + ts_b
	print(ts_a)
	print(ts_b)
	print(ts_all)

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
