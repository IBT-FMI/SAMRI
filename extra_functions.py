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



def get_data_selection(workflow_base, conditions=[], scan_types=[], subjects=[], exclude_subjects=[], include_measurements=[], exclude_measurements=[]):

	if include_measurements:
		measurement_path_list = [workflow_base+"/"+i for i in include_measurements]
	else:
		measurement_path_list = listdir(workflow_base)

	measurements=[]
	#populate a list of lists with acceptable subject names, conditions, and sub_dir's
	for sub_dir in measurement_path_list:
		if sub_dir not in exclude_measurements:
			measurement = []
			try:
				state_file = open(workflow_base+"/"+sub_dir+"/subject", "r")
				read_variables=0 #count variables so that breaking takes place after both have been read
				while True:
					current_line = state_file.readline()
					if "##$SUBJECT_name_string=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if entry not in exclude_subjects:
							if len(subjects) > 0 and entry not in subjects:
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
						#if the directory passed both the subject and conditions tests, append a line for it
						if not scan_types:
							#add two empty entries to fill columns otherwise dedicated to the scan program
							measurement.extend(["",""])
							measurements.append(measurement)
						#if various scan types are selected extend and copy lines to accommodate:
						else:
							for scan_type in scan_types:
								#make a shallow copy of the list:
								measurement_copy = measurement[:]
								try:
									scan_program_file = open(workflow_base+"/"+sub_dir+"/ScanProgram.scanProgram", "r")
									syntax_adjusted_scan_type = scan_type+" "
									while True:
										current_line = scan_program_file.readline()
										if syntax_adjusted_scan_type in current_line:
											scan_number = current_line.split(syntax_adjusted_scan_type)[1].strip("(E").strip(")</displayName>\n")
											measurement_copy.extend([scan_type, scan_number])
											measurements.append(measurement_copy)
											break
										#avoid infinite while loop:
										if current_line == "</de.bruker.mri.entities.scanprogram.StudyScanProgramEntity>":
											break
								except IOError:
									pass
						break #prevent loop from going on forever
			except IOError:
				pass


	data_selection = pd.DataFrame(measurements, columns=["subject", "condition", "measurement", "scan_type", "scan"])

	#drop subjects which do not have measurements for all conditions
	if len(conditions) > 1:
		for subject in set(data_selection["subject"]):
			if len(data_selection[(data_selection["subject"] == subject)]) < len(conditions):
				data_selection = data_selection[(data_selection["subject"] != subject)]

	return data_selection

if __name__ == "__main__":
	for nr in [4460]:
		convert_dcm_to_nifti("/home/chymera/data/dc.rs/export_ME/dicom/"+str(nr)+"/1/EPI/")
