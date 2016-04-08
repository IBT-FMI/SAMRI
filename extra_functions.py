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



def get_data_selection(workflow_base, conditions=[], scan_types=[], subjects=[], exclude_subjects=[], measurements=[], exclude_measurements=[]):

	if measurements:
		measurement_path_list = [path.join(workflow_base,i) for i in measurements]
	else:
		measurement_path_list = listdir(workflow_base)

	selected_measurements=[]
	#populate a list of lists with acceptable subject names, conditions, and sub_dir's
	for sub_dir in measurement_path_list:
		if sub_dir not in exclude_measurements:
			selected_measurement = []
			try:
				state_file = open(path.join(workflow_base,sub_dir,"subject"), "r")
				read_variables=0 #count variables so that breaking takes place after both have been read
				while True:
					current_line = state_file.readline()
					if "##$SUBJECT_name_string=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if entry not in exclude_subjects:
							if len(subjects) > 0 and entry not in subjects:
								break
							else:
								selected_measurement.append(entry)
						else:
							break
						read_variables +=1 #count recorded variables
					if "##$SUBJECT_study_name=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if entry in conditions or len(conditions) == 0:
							selected_measurement.append(entry)
						else:
							break
						read_variables +=1 #count recorded variables
					if read_variables == 2:
						selected_measurement.append(sub_dir)
						#if the directory passed both the subject and conditions tests, append a line for it
						if not scan_types:
							#add two empty entries to fill columns otherwise dedicated to the scan program
							selected_measurement.extend(["",""])
							selected_measurements.append(selected_measurement)
						#if various scan types are selected extend and copy lines to accommodate:
						else:
							for scan_type in scan_types:
								#make a shallow copy of the list:
								measurement_copy = selected_measurement[:]
								scan_number=None
								try:
									scan_program_file = open(path.join(workflow_base,sub_dir,"ScanProgram.scanProgram"), "r")
									syntax_adjusted_scan_type = scan_type+" "
									while True:
										current_line = scan_program_file.readline()
										if syntax_adjusted_scan_type in current_line:
											scan_number = current_line.split(syntax_adjusted_scan_type)[1].strip("(E").strip(")</displayName>\n")
											measurement_copy.extend([scan_type, scan_number])
											selected_measurements.append(measurement_copy)
											break
										#avoid infinite while loop:
										if current_line == "</de.bruker.mri.entities.scanprogram.StudyScanProgramEntity>":
											break
								except IOError:
									pass
								#sometimes the ScanProgram.scanProgram file can be incomplete. We also chack the individual scan acquisition parameters
								if not scan_number:
									for sub_sub_dir in listdir(path.join(workflow_base,sub_dir)):
										try:
											acqp_file = path.join(workflow_base,sub_dir,sub_sub_dir,"acqp")
											if scan_type in open(acqp_file).read():
												scan_number = sub_sub_dir
												measurement_copy.extend([scan_type, scan_number])
												selected_measurements.append(measurement_copy)
										except IOError:
											pass
						break #prevent loop from going on forever
			except IOError:
				pass

	data_selection = pd.DataFrame(selected_measurements, columns=["subject", "condition", "measurement", "scan_type", "scan"])

	#drop subjects which do not have measurements for all conditions
	if len(conditions) > 1:
		for subject in set(data_selection["subject"]):
			if len(data_selection[(data_selection["subject"] == subject)]) < len(conditions):
				data_selection = data_selection[(data_selection["subject"] != subject)]

	return data_selection

if __name__ == "__main__":
	for nr in [4460]:
		convert_dcm_to_nifti("/home/chymera/data/dc.rs/export_ME/dicom/"+str(nr)+"/1/EPI/")
