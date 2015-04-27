import nipype.interfaces.dcmstack as dcmstack
from dcmstack.extract import default_extractor
from dicom import read_file
from os import listdir, path, makedirs

def convert_dcm_dir(dicom_dir, multi_epi_check=True):
	nii_dir = dicom_dir.replace("dicom", "nii")
	# if not path.exists(nii_dir):
		# makedirs(nii_dir)
	stacker = dcmstack.DcmStack()

	if multi_epi_check:
		dicom_files = listdir(dicom_dir)
		echo_times=[]
		for dicom_file in dicom_files:
			meta = default_extractor(read_file(dicom_dir+dicom_file, stop_before_pixels=True, force=True))
			echo_times += [meta["EchoTime"]]

		for echo_time in list(set(echo_times)):
			echo_indices = [i for i, j in enumerate(echo_times) if j == echo_time]
			stacker.inputs.embed_meta = True
			stacker.inputs.dicom_files = [dicom_dir+dicom_files[index] for index in echo_indices]
			stacker.inputs.out_path = nii_dir+"/"
			stacker.inputs.out_format = "EPI"+str(echo_time[:2])

	else:
		stacker.inputs.dicom_files = dicom_dir
		file_name = "EPI"
		stacker.inputs.out_format = file_name
		destination_file_name = nii_dir+"/"+file_name+".nii.gz"
		move(result.outputs.out_file, destination_file_name)

	result = stacker.run()
	return nii_dir

if __name__ == "__main__":
	for nr in [4457, 4459, 4460]:
		convert_dcm_dir("/home/chymera/data2/dc.rs/export_ME/dicom/"+str(nr)+"/1/EPI/")
