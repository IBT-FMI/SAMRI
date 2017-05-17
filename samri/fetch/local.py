import os

import nibabel as nib
import numpy as np
import pandas as pd

def roi_from_atlaslabel(atlas, mapping, label_names,
	parser={
		"textcolumn":"Structure",
		"valuecolumn right":"right label",
		"valuecolumn left":"left label",
		},
	bilateral=True,
	save_as="",
	):
	"""Return a region of interest map based on an atlas and a label."""

	mapping = os.path.abspath(os.path.expanduser(mapping))
	atlas = os.path.abspath(os.path.expanduser(atlas))
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
	roi = nib.Nifti1Image(masked_data, affine, header)
	if save_as:
		roi.to_filename(os.path.abspath(os.path.expanduser(save_as)))

	return roi
