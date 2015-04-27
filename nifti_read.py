from nibabel.nifti1 import Nifti1Header
import nibabel as nib
from os import listdir
from dicom import read_file

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

def read_header_nii(filesdir, my_file=False):
	files_list = listdir(filesdir)
	if my_file:
		myfile = filesdir+myfile
	else:
		my_file = filesdir+files_list[0]
	meta = nib.load(my_file)
	print(meta)

def read_header_dicom(filesdir, my_file=False):
	files_list = listdir(filesdir)
	if my_file:
		myfile = filesdir+myfile
	else:
		my_file = filesdir+files_list[0]
	meta = read_file(my_file)
	print(meta)

def check_dicom_header(filesdir, check_value):
	import nipype.interfaces.dcmstack as dcmstack
	from dcmstack.extract import default_extractor
	for dicom_file in listdir(filesdir):
		meta = default_extractor(read_file(filesdir+dicom_file, stop_before_pixels=True, force=True))
		meta = meta[check_value]	
		if meta != 0.35:
			print(dicom_file, "muie")

if __name__ == "__main__":
	# files_dir = "/home/chymera/data2/dc.rs/export_ME/nii/4459/1/EPI/"
	# example_filelist = [files_dir+file_path for file_path in listdir(files_dir)]
	# example_filelist_joanes=[
	# 	"/home/chymera/src/RS/1eME.nii",
	# 	"/home/chymera/src/RS/2eME.nii",
	# 	"/home/chymera/src/RS/3eME.nii"
	# ]
	# read_header(example_filelist)
	# read_header_dicom("/home/chymera/data2/dc.rs/export_ME/dicom/4459/1/EPI/")
	check_dicom_header("/home/chymera/data2/dc.rs/export_ME/dicom/4459/1/EPI/", check_value="SliceThickness")
	# read_header_nii("/home/chymera/data2/dc.rs/export_ME/nii/4459/1/EPI/")
