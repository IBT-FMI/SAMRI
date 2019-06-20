import nibabel as nib
import numpy as np
import pandas as pd
from copy import deepcopy
from os import path
from scipy import ndimage

def roi_from_atlaslabel(atlas, label_names,
	mapping=False,
	bilateral=True,
	dilate=True,
	parser={
		"textcolumn":"Structure",
		"valuecolumn right":"right label",
		"valuecolumn left":"left label",
		},
	save_as="",
	):
	"""Return a region of interest map based on an atlas and a label.

	dilate : bool
	Whether to dilate the roi by one voxel. This is useful for filling up downsampled masks (nearest-neighbour interpolation, may create unexpected holes in masks).
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

		return roi


	mapping = path.abspath(path.expanduser(mapping))
	mapping = pd.read_csv(mapping)
	if bilateral and (parser["valuecolumn right"] and parser["valuecolumn left"]):
		roi_values = []
		for label_name in label_names:
			roi_values.extend(mapping[mapping[parser["textcolumn"]].str.contains(label_name)][parser["valuecolumn right"]].values.tolist())
			roi_values.extend(mapping[mapping[parser["textcolumn"]].str.contains(label_name)][parser["valuecolumn left"]].values.tolist())
	header = atlas.header
	affine = atlas.affine
	data = atlas.get_data()
	masked_data = np.in1d(data, roi_values).reshape(data.shape).astype(int)
	if dilate:
		masked_data = ndimage.binary_dilation(masked_data).astype(masked_data.dtype)
	roi = nib.Nifti1Image(masked_data, affine, header)
	if save_as:
		roi.to_filename(path.abspath(path.expanduser(save_as)))

	return roi
