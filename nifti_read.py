from nibabel.nifti1 import Nifti1Header
import nibabel as nib
from os import listdir

def read_header(example_filelist, save_header=False):
	for example_file in example_filelist:
		img=nib.load(example_file)
		print(example_file)
		if save_header:
			text_file = open("Output_joanes.txt", "w")
			text_file.write(str(img.header))
			text_file.close()
		else:
			print(img.header)

if __name__ == "__main__":
	files_dir = "/home/chymera/data2/dc.rs/export_ME/nifti/4459/1/EPI/"
	example_filelist = [files_dir+file_path for file_path in listdir(files_dir)]
	example_filelist_joanes=[
		"/home/chymera/src/RS/1eME.nii",
		"/home/chymera/src/RS/2eME.nii",
		"/home/chymera/src/RS/3eME.nii"
	]
	read_header(example_filelist)
