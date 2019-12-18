import nibabel as nib
from os import path

def flip_axis(img_path,
	axis=2,
	out_path='flipped.nii.gz',
	):
	"""Flip along an axis, while avoiding axis inversion (e.g. left-right inversion to right-left).

	Parameters
	----------
	img_path : str
		Path to a NIfTI file.
	axis : {0,1,2}, optional
		Integer specifying one of the three spatial axes along which the object should be flipped.
		Note that this is the axis which does not change, i.e. in order to rotate an animal from prone to supine (rotating the X and Y axes), the axis selected here should be 2.
	out_path : str, optional
		Path to which to save the flipped NIfTI file.
	"""

	img_path = path.abspath(path.expanduser(img_path))
	out_path = path.abspath(path.expanduser(out_path))
	img = nib.load(img_path)
	data = img.get_data()
	affine = img.affine
	if axis == 0:
	    flipped_data = data[:,::-1,::-1,...]
	elif axis == 1:
	    flipped_data = data[::-1,:,::-1,...]
	elif axis == 2:
	    flipped_data = data[::-1,::-1,:,...]
	flipped_img = nib.Nifti1Image(flipped_data,affine,img.header)
	nib.save(flipped_img,out_path)
	return out_path
