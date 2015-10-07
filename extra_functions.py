import nipype.interfaces.dcmstack as dcmstack
import nibabel as nb
from dcmstack.extract import minimal_extractor
from dicom import read_file
from os import listdir, path, makedirs, getcwd

def dcm_to_nii(dcm_dir, group_by="EchoTime", node=False):
	if node:
		nii_dir = getcwd()
	else:
		nii_dir = dcm_dir.replace("dicom", "nii")
		if not path.exists(nii_dir):
			makedirs(nii_dir)
	dcm_dir = dcm_dir+"/"
	stacker = dcmstack.DcmStack()

	results=[]
	if group_by:
		dicom_files = listdir(dcm_dir)
		echo_times=[]
		for dicom_file in dicom_files:
			meta = minimal_extractor(read_file(dcm_dir+dicom_file, stop_before_pixels=True, force=True))
			echo_times += [float(meta[group_by])]

		echo_time_set = list(set(echo_times))
		for echo_time in echo_time_set:
			echo_indices = [i for i, j in enumerate(echo_times) if j == echo_time]
			stacker.inputs.embed_meta = True
			stacker.inputs.dicom_files = [dcm_dir+dicom_files[index] for index in echo_indices]
			stacker.inputs.out_path = nii_dir+"/"
			stacker.inputs.out_format = "EPI"+str(echo_time)[:2]
			result = stacker.run()
			results += [result.outputs.out_file]

	else:
		stacker.inputs.dicom_files = dcm_dir
		stacker.inputs.out_path = nii_dir+"/"
		result = stacker.run()
		results += [result.outputs.out_file]

	return results, echo_time_set

def print_tags(nii_file):
	nii_img = nb.load(nii_file)
	print nii_img.header

def edit_tags(nii_files):
	for nii_file in nii_files:
		nii_img = nb.load(nii_file)
		nii_img.header["pixdim"][1:4] = nii_img.header["pixdim"][1:4]*10
		nii_img.header["pixdim"][4] = 1
		nii_img.header["pixdim"][4] = 1.5
		nii_img.header["xyzt_units"] = 0
		nii_img.header["xyzt_units"] = 10
		nii_img.header["dim_info"] = 0
		print nii_img.header


if __name__ == "__main__":
	for nr in [4460]:
		convert_dcm_to_nifti("/home/chymera/data/dc.rs/export_ME/dicom/"+str(nr)+"/1/EPI/")
