import glob
import nibabel as nib
import numpy as np
import os
import pandas as pd
from copy import deepcopy
from os import path
from scipy import ndimage
from sklearn.preprocessing import minmax_scale, MinMaxScaler

def prepare_abi_connectivity_maps(identifier,
	abi_data_root='/usr/share/ABI-connectivity-data/',
	invert_lr_experiments=[],
	reposit_path='/var/tmp/samri/abi_connectivity/{identifier}/sub-{experiment}/ses-1/anat/sub-{experiment}_ses-1_cope.nii.gz',
	**kwargs
	):
	"""
	Prepare NIfTI feature maps from the ABI connectivity data for analysis.
	This function is a thin wrapper applying the known path formats for the ABI dataset structure to the `samri.fetch.local.prepare_feature_map()` function.

	Parameters
	----------

	identifier : str
		Experiment set identifier which corresponds to the data set paths from the ABI-connectivity-data package.
	abi_data_root : str, optional
		Root path for the ABI-connectivity-data package installation on the current machine.
	invert_lr_experiments : list of str, optional
		List of strings, each string 9 characters long, identifying which experiments need to be inverted with respect to the left-right orientation.
	reposit_path : string, optional
		Python-formattable string, which can contain "{experiment}" and may contain "{identifier}", under which the prepared data is to be saved.
		Generally this should be a temporal path, which ideally is deleted after the prepared data is used.
	"""

	for experiment_path in glob.glob(path.join(abi_data_root,identifier)+"*"):
		experiment = experiment_path[-9:]
		invert_lr = experiment in invert_lr_experiments
		save_as = reposit_path.format(identifier=identifier,experiment=experiment)
		prepare_feature_map(experiment_path,
			invert_lr = invert_lr,
			save_as=save_as,
			**kwargs
			)

def prepare_feature_map(data_path,
	invert_lr=False,
	lr_dim=1,
	save_as='',
	scaling='',
	):
	"""
	Prepare NIfTI feature map file for analysis.
	This function is primarily intended to help with ABI gene expression and connectivity data, and can do flipping (left-right is often necessary for lateralized features), and normalization.

	Parameters
	----------

	data_path : str
		Path to either the target feature map file (NIfTI file, ending in ".nii" or ".nii.gz"), or a directory containing a single NIfTI file, which is the target feature map.
	invert_lr : str, optional
		Whether to invert the (presumably) left-right dimension of the image.
	lr_dim : {1,2,3}, optional
		Which dimension corresponds to the left-right dimension of the image.
		If the image uses the NIfTI specification correctly (RAS orientation), this will always be the first dimension.
	save_as : str, optional
		Path to which to save the prepared feature map.
	scaling : {'minmax', ''}, optional
		String specifying what scaling should be performed to homogenize data ranges.
		If this parameter evaluates to false, no scaling is performed.
	"""

	data_path = path.abspath(path.expanduser(data_path))
	if path.isdir(data_path):
		file_names = []
		for my_file in os.listdir(data_path):
			if my_file.endswith(".nii.gz") or my_file.endswith(".nii"):
				file_names.append(my_file)
		if len(file_names) > 1:
			files_string = '\n'.join(file_names)
			raise ValueError('More than one file was found in the `{}` directory:\n'
					'{}\n Please choose one and pass the file name to the `data_path` parameter of the `samri.fetch.local.prepare_abi_connctivity()` function.'.format(
						data_path,
						file_names,
						))
		else:
			file_name = file_names[0]
		data_path = path.join(data_path,file_name)
	img = nib.load(data_path)
	header = img.header
	affine = img.affine
	data = img.get_data()
	if invert_lr:
		if lr_dim == 1:
			data = data[::-1,:,:]
		elif lr_dim == 2:
			data = data[:,::-1,:]
		elif lr_dim == 3:
			data = data[:,:,::-1]
	if scaling == 'minmax':
		data = (data-data.min()) / (data.max() - data.min())
	if scaling == 'normalize':
		data = (data-data.mean()) / data.std()
	if scaling == 'standardize':
		data = data / data.std()
	if scaling == 'standardize positive':
		data = (data-data.min()) / data.std()
	prepared_file = nib.Nifti1Image(data, affine, header)
	if save_as:
		save_dir = os.path.dirname(save_as)
		if not os.path.exists(save_dir):
			    os.makedirs(save_dir)
		prepared_file.to_filename(path.abspath(path.expanduser(save_as)))

	return prepared_file

def summary_atlas(atlas,
	mapping='',
	label_column_l='left label',
	label_column_r='right label',
	structure_column='Structure',
	save_as='',
	summary={
		1:{
			'structure':'Cortex',
			'summarize':['cortex'],
			'laterality':'right',
			},
		2:{
			'structure':'Cortex',
			'summarize':['cortex'],
			'laterality':'left',
			},
		},
	):
	"""Return an atlas with labels corresponding to summary categories

	Parameters
	----------
	atlas : str, optional
		Path to NIfTI file containing integer values.
	mapping : str, optional
		Path to CSV file which contains columns matching the values assigned to the `label_column_l`, `label_column_r`, `structure_column` parameters of this function.
	summary : dict, optional
		Dictionary with keys which are integers, and values which are dictionaries, whose keys in turn are:
			* 'structure': accepting any value assignement
			* 'summarize': the value of which is a list of strings which are present on the `mapping` data file column entitled according to `structure_column`.
			* 'laterality': the value of which is one of {'','both','left','right'}
	"""

	new_mapping = []
	new_atlas = None
	for key in summary:

		metadata = summary[key]
		new_structure = {}
		new_structure[structure_column] = metadata['structure']
		if metadata['laterality'] == 'left':
			new_structure[label_column_l] = key
		elif metadata['laterality'] == 'right':
			new_structure[label_column_r] = key
		elif metadata['laterality'] in ['','both']:
			new_structure[label_column_l] = key
			new_structure[label_column_r] = key
		new_mapping.append(new_structure)

		roi = roi_from_atlaslabel(atlas, metadata['summarize'],
			mapping=mapping,
			label_column_l='left label',
			label_column_r='right label',
			structure_column='Structure',
			output_label=key,
			laterality=metadata['laterality'],
			)
		if new_atlas:
			header = new_atlas.header
			affine = new_atlas.affine
			data = new_atlas.get_data()
			roi_data = roi.get_data()
			new_atlas_data = data + roi_data
			new_atlas = nib.Nifti1Image(new_atlas_data, affine, header)
		else:
			new_atlas = roi
	df = pd.DataFrame(new_mapping)
	df = df.groupby(structure_column).sum()
	df[structure_column] = df.index
	new_mapping = df.astype({label_column_l: int, label_column_r: int})

	return new_atlas, new_mapping


def roi_from_atlaslabel(atlas, label_names,
	dilate=False,
	label_column_l='left label',
	label_column_r='right label',
	laterality='',
	mapping=None,
	output_label=1,
	save_as='',
	structure_column='Structure',
	):
	"""Return a region of interest (ROI) map based on an atlas and a label.

	Parameters
	----------
	dilate : bool, optional
		Whether to dilate the region of interest by one voxel. This is useful for filling up downsampled masks (nearest-neighbour interpolation may create unexpected holes in masks).
	laterality : {'', 'both', 'left', 'right'}, optional
		What side of the brain to select if labels are lateralized and a structure match gives labels for both sides.
	mapping : str, optional
		Path to CSV file which contains columns matching the values assigned to the `label_column_l`, `label_column_r`, `structure_column` parameters of this function.
	output_label : int, optional
		Integer value to use so as to label the desired region of interest voxels.
	"""

	if isinstance(atlas, str):
		atlas = path.abspath(path.expanduser(atlas))
		atlas = nib.load(atlas)
	if mapping is None:
		atlas_data = atlas.get_data()
		components = []
		for i in label_names:
			i_data = deepcopy(atlas_data)
			i_data[i_data!=i] = False
			i_data[i_data==i] = True
			components.append(i_data)
		roi_data = sum(components).astype(bool).astype(int)
		roi = nib.Nifti1Image(roi_data, atlas.affine, atlas.header)
	else:
		if isinstance(mapping, str):
			mapping = path.abspath(path.expanduser(mapping))
			mapping = pd.read_csv(mapping)
		roi_values = []
		for label_name in label_names:
			if laterality == 'left':
				roi_values.extend(mapping[mapping[structure_column].str.contains(label_name)][label_column_l].values.tolist())
			elif laterality == 'right':
				roi_values.extend(mapping[mapping[structure_column].str.contains(label_name)][label_column_r].values.tolist())
			elif laterality in ['', 'both']:
				roi_values.extend(mapping[mapping[structure_column].str.contains(label_name)][label_column_r].values.tolist())
				roi_values.extend(mapping[mapping[structure_column].str.contains(label_name)][label_column_l].values.tolist())
			else:
				raise ValueError('You need to provide an accepted value for the `laterality` parameter of the `samri.fetch.local.roi_from_atlaslabel()` function.')
		header = atlas.header
		affine = atlas.affine
		data = atlas.get_data()
		masked_data = np.in1d(data, roi_values).reshape(data.shape).astype(int)
		if dilate:
			masked_data = ndimage.binary_dilation(masked_data).astype(masked_data.dtype)
		masked_data = masked_data*output_label
		roi = nib.Nifti1Image(masked_data, affine, header)
	if save_as:
		roi.to_filename(path.abspath(path.expanduser(save_as)))

	return roi
