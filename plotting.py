import os
import nibabel
from nilearn import image

def plot_nii(file_path, slices):
	# Using nibabel.load to load existing Nifti image #############################
	# anat_img = nibabel.load(file_path)

	# Accessing image data and affine #############################################
	# anat_data = anat_img.get_data()
	# print('anat_data has shape: %s' % str(anat_data.shape))
	# anat_affine = anat_img.get_affine()
	# print('anat_affine:\n%s' % anat_affine)

	# Using image in nilearn functions ############################################
	# functions containing 'img' can take either a filename or an image as input
	smooth_anat_img = image.smooth_img(file_path, 6)
	# smooth_anat_img = image.smooth_img(anat_img, 6)


	# Visualization ###############################################################
	from nilearn import plotting
	cut_coords = slices
	plotting.plot_anat(file_path, cut_coords=cut_coords, display_mode="y", annotate=False, draw_cross=False)
	# plotting.plot_anat(smooth_anat_img, cut_coords=cut_coords)

	# Saving image to file ########################################################
	# smooth_anat_img.to_filename('smooth_anat_img.nii.gz')

if __name__ == '__main__':
	plot_nii("/home/chymera/GLM/_measurement_id_20151103_191031_4006_1_1/structural_FAST/6_restore.nii.gz", 1)
	plotting.show()
