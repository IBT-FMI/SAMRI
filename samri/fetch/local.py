import nibabel as nib
import numpy as np
import pandas as pd
from os import path
from scipy import ndimage

def roi_from_atlaslabel(atlas, mapping, label_names,
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

	mapping = path.abspath(path.expanduser(mapping))
	atlas = path.abspath(path.expanduser(atlas))
	atlas = nib.load(atlas)

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
