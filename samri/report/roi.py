import os
import nibabel as nib
import numpy as np

from nilearn.input_data import NiftiMasker
from scipy.io import loadmat
from samri.utilities import add_roi_data


def roi_mean(img_path, mask_path):
	"""Return the mean of the masked region of an image.
	"""
	mask = os.path.abspath(os.path.expanduser(mask_path))
	if mask_path.endswith("roi"):
		mask = loadmat(mask)["ROI"]
		while mask.ndim != 3:
			mask=mask[0]
		img_path = os.path.abspath(os.path.expanduser(img_path))
		img = nib.load(img_path)
		print(mask)
		print(np.shape(mask))
		print(np.shape(img))
		print(img[mask])
	else:
		masker = NiftiMasker(mask_img=mask)
		add_roi_data(img_path,masker)
