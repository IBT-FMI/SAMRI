import nibabel as nib
import numpy as np
import pandas as pd
from copy import deepcopy
from os import path
from scipy import ndimage

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
	new_mapping = df.astype({label_column_l: int, label_column_r: int})

	return new_atlas, new_mapping


def roi_from_atlaslabel(atlas, label_names,
	mapping=False,
	laterality='',
	dilate=False,
	label_column_l='left label',
	label_column_r='right label',
	structure_column='Structure',
	save_as='',
	output_label=1,
	):
	"""Return a region of interest map based on an atlas and a label.

	dilate : bool, optional
		Whether to dilate the roi by one voxel. This is useful for filling up downsampled masks (nearest-neighbour interpolation may create unexpected holes in masks).
	laterality : {'', 'both', 'left', 'right'}, optional
		What side of the brain to select if labels are lateralized and a structure match gives labels for both sides.
	mapping : str, optional
		Path to CSV file which contains columns matching the values assigned to the `label_column_l`, `label_column_r`, `structure_column` parameters of this function.
	"""

	if isinstance(atlas, str):
		atlas = path.abspath(path.expanduser(atlas))
		atlas = nib.load(atlas)
	if not mapping:
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
