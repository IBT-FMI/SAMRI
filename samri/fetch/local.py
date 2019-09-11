import nibabel as nib
import numpy as np
import pandas as pd
from copy import deepcopy
from os import path
from scipy import ndimage

def roi_from_atlaslabel(atlas, label_names,
	mapping=False,
	laterality='',
	dilate=True,
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
