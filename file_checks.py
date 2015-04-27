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

def check_dicom_header(filesdir, check_value=False, given_value=False, firstonly=False):
	import nipype.interfaces.dcmstack as dcmstack
	from dcmstack.extract import default_extractor
	for dicom_file in listdir(filesdir):
		meta = default_extractor(read_file(filesdir+dicom_file, stop_before_pixels=True, force=True))
		if check_value:
			meta = meta[check_value]
			if meta != given_value:
				print(dicom_file, "not the given value", meta)
		else:
			print(meta)
		if firstonly:
			break

if __name__ == "__main__":
	# read_header_dicom("/home/chymera/data2/dc.rs/export_ME/dicom/4459/1/EPI/")
	check_dicom_header("/home/chymera/data2/dc.rs/export_ME/dicom/4459/1/EPI/", firstonly=True)
	# read_header_nii("/home/chymera/data2/dc.rs/export_ME/nii/4459/1/EPI/")
