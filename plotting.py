import os
import nibabel
from nilearn import image, plotting

def plot_nii(file_path, slices):
	plotting.plot_anat(file_path, cut_coords=slices, display_mode="y", annotate=False, draw_cross=False)

if __name__ == '__main__':
	plot_nii("/home/chymera/FSL_GLM_work/GLM/_measurement_id_20151103_213035_4001_1_1/structural_cutoff/6_restore_maths.nii.gz", (-50,20))
	plotting.show()
