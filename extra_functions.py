import nipype.interfaces.dcmstack as dcmstack
import nibabel as nb
from dcmstack.extract import minimal_extractor
from dicom import read_file
from os import listdir, path, makedirs, getcwd
import pandas as pd
import re

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

def get_data_selection(workflow_base, conditions, include_subjects, exclude_subjects, exclude_measurements):

	measurements=[]
	#populate a list of lists with acceptable subject names, conditions, and sub_dir's
	for sub_dir in listdir(workflow_base):
		if sub_dir not in exclude_measurements:
			try:
				state_file = open(workflow_base+"/"+sub_dir+"/subject", "r")
				measurement = []
				read_variables=0 #count variables so that breaking takes place after both have been read
				while True:
					current_line = state_file.readline()
					if "##$SUBJECT_name_string=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if entry not in exclude_subjects:
							if len(include_subjects) > 0 and entry not in include_subjects:
								break
							else:
								measurement.append(entry)
						else:
							break
						read_variables +=1 #count recorded variables
					if "##$SUBJECT_study_name=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if entry in conditions or len(conditions) == 0:
							measurement.append(entry)
						else:
							break
						read_variables +=1 #count recorded variables
					if read_variables == 2:
						measurement.append(sub_dir)
						measurements.append(measurement)
						break #prevent loop from going on forever
			except IOError:
				pass

	data_selection = pd.DataFrame(measurements, columns=["subject", "condition", "measurement"])

	#drop subjects which do not have measurements for all conditions
	if len(conditions) > 1:
		for subject in set(data_selection["subject"]):
			if len(data_selection[(data_selection["subject"] == subject)]) < len(conditions):
				data_selection = data_selection[(data_selection["subject"] != subject)]

	return data_selection

if __name__ == "__main__":
	for nr in [4460]:
		convert_dcm_to_nifti("/home/chymera/data/dc.rs/export_ME/dicom/"+str(nr)+"/1/EPI/")
