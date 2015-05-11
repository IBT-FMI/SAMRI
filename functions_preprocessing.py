import nipype.interfaces.dcmstack as dcmstack
from dcmstack.extract import default_extractor
from dicom import read_file
from os import listdir, path, makedirs
from multiprocessing.dummy import Pool as ThreadPool
import itertools

def echo_time_list(dicom_dir, dicom_file):
	meta = default_extractor(read_file(dicom_dir+dicom_file, stop_before_pixels=True, force=True))
	return [meta["EchoTime"]]

def echo_time_list_star(a_b):
	"""Convert `echo_time_list([a,b])` to `echo_time_list(a,b)``"""
	return echo_time_list(*a_b)

def convert_dcm_dir(dicom_dir, multi_epi_check=True, poolsize=1):
	pool = ThreadPool(poolsize)

	if multi_epi_check:
		dicom_files = listdir(dicom_dir)
		echo_times = pool.map(echo_time_list_star, zip(itertools.repeat(dicom_dir), dicom_files))
		pool.close()
		pool.join()

	return echo_times

	nii_dir = dicom_dir.replace("dicom", "nii")
	stacker = dcmstack.DcmStack()
	# 	for echo_time in list(set(echo_times)):
	# 		echo_indices = [i for i, j in enumerate(echo_times) if j == echo_time]
	# 		stacker.inputs.embed_meta = True
	# 		stacker.inputs.dicom_files = [dicom_dir+dicom_files[index] for index in echo_indices]
	# 		stacker.inputs.out_path = nii_dir+"/"
	# 		stacker.inputs.out_format = "EPI"+str(echo_time[:2])
	#
	# else:
	# 	stacker.inputs.dicom_files = dicom_dir
	# 	file_name = "EPI"
	# 	stacker.inputs.out_format = file_name
	# 	destination_file_name = nii_dir+"/"+file_name+".nii.gz"
	# 	move(result.outputs.out_file, destination_file_name)
	#
	# result = stacker.run()
	# return nii_dir

if __name__ == "__main__":
	for nr in [4460]:
		print convert_dcm_dir("/home/chymera/data2/dc.rs/export_ME/dicom/"+str(nr)+"/1/EPI/")
