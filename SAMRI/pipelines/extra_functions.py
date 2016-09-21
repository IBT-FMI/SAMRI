import csv
import inspect
import os
import re

import nibabel as nb
import pandas as pd
from nipype_based.utils import STIM_PROTOCOL_DICTIONARY

def read_bruker_timing(scan_directory):
	from datetime import datetime
	scan_directory = os.path.abspath(os.path.expanduser(scan_directory))
	state_file_path = os.path.join(scan_directory,"AdjStatePerScan")
	state_file = open(state_file_path, "r")

	delay_seconds = dummy_scans = dummy_scans_ms = 0

	while True:
		current_line = state_file.readline()
		if "AdjScanStateTime" in current_line:
			delay_datetime_line = state_file.readline()
			break

	trigger_time, scanstart_time = [datetime.utcnow().strptime(i.split("+")[0], "<%Y-%m-%dT%H:%M:%S,%f") for i in delay_datetime_line.split(" ")]
	delay = scanstart_time-trigger_time
	delay_seconds=delay.total_seconds()

	method_file_path = os.path.join(scan_directory,"method")
	method_file = open(method_file_path, "r")

	read_variables=0 #count variables so that breaking takes place after both have been read
	while True:
		current_line = method_file.readline()
		if "##$PVM_DummyScans=" in current_line:
			dummy_scans = int(current_line.split("=")[1])
			read_variables +=1 #count variables
		if "##$PVM_DummyScansDur=" in current_line:
			dummy_scans_ms = int(current_line.split("=")[1])
			read_variables +=1 #count variables
		if read_variables == 2:
			break #prevent loop from going on forever

	total_delay_s = delay_seconds + dummy_scans_ms/1000

	return delay_seconds, dummy_scans, dummy_scans_ms, total_delay_s

def write_function_call(frame, target_path):
	args, _, _, values = inspect.getargvalues(frame)
	function_name = inspect.getframeinfo(frame)[2]
	function_call = function_name+"("
	for arg in args:
		arg_value = values[arg]
		if isinstance(arg_value, str):
			arg_value = "\'"+arg_value+"\'"
		else:
			arg_value = str(arg_value)
		arg_entry=arg+"="+arg_value+","
		function_call+=arg_entry
	function_call+=")"
	target = open(target_path, 'w')
	target.write(function_call)
	target.close()

def write_events_file(scan_type, stim_protocol_dictionary,
	db_path="~/syncdata/meta.db",
	outfile="~/events.tsv",
	subject_delay=False,
	scan_directory=False,
	):
	import pandas as pd
	import numpy as np
	from copy import deepcopy
	import sys
	from labbookdb.db.query import loadSession
	from labbookdb.db.common_classes import LaserStimulationProtocol

	outfile = os.path.abspath(os.path.expanduser(outfile))

	if not subject_delay:
		_, _, _, subject_delay = read_bruker_timing(scan_directory)

	session, engine = loadSession(db_path)
	sql_query=session.query(LaserStimulationProtocol).filter(LaserStimulationProtocol.code==stim_protocol_dictionary[scan_type])
	mystring = sql_query.statement
	mydf = pd.read_sql_query(mystring,engine)
	delay = int(mydf["stimulation_onset"][0])
	inter_stimulus_duration = int(mydf["inter_stimulus_duration"][0])
	stimulus_duration = mydf["stimulus_duration"][0]
	stimulus_repetitions = mydf["stimulus_repetitions"][0]

	onsets=[]
	names=[]
	with open(outfile, 'w') as tsvfile:
		field_names =["onset","duration","stimulation_frequency"]
		writer = csv.DictWriter(tsvfile, fieldnames=field_names, delimiter="\t")

		writer.writeheader()
		for i in range(stimulus_repetitions):
			events={}
			onset = delay+(inter_stimulus_duration+stimulus_duration)*i
			events["onset"] = onset-subject_delay
			events["duration"] = stimulus_duration
			events["stimulation_frequency"] = stimulus_duration
			writer.writerow(events)

	return outfile

def get_subjectinfo(subject_delay, scan_type, scan_types):
	from nipype.interfaces.base import Bunch
	import pandas as pd
	import numpy as np
	from copy import deepcopy
	import sys
	sys.path.append('/home/chymera/src/LabbookDB/db/')
	from query import loadSession
	from common_classes import LaserStimulationProtocol
	db_path="~/syncdata/meta.db"

	session, engine = loadSession(db_path)

	sql_query=session.query(LaserStimulationProtocol).filter(LaserStimulationProtocol.code==scan_types[scan_type])
	mystring = sql_query.statement
	mydf = pd.read_sql_query(mystring,engine)
	delay = int(mydf["stimulation_onset"][0])
	inter_stimulus_duration = int(mydf["inter_stimulus_duration"][0])
	stimulus_duration = mydf["stimulus_duration"][0]
	stimulus_repetitions = mydf["stimulus_repetitions"][0]

	onsets=[]
	names=[]
	for i in range(stimulus_repetitions):
		onset = delay+(inter_stimulus_duration+stimulus_duration)*i
		onsets.append([onset])
		names.append("s"+str(i+1))
	output = []
	for idx_a, a in enumerate(onsets):
		for idx_b, b in enumerate(a):
			onsets[idx_a][idx_b] = round(b-subject_delay, 2) #floating point values don't add up nicely, so we have to round (https://docs.python.org/2/tutorial/floatingpoint.html)
	output.append(Bunch(conditions=names,
					onsets=deepcopy(onsets),
					durations=[[stimulus_duration]]*stimulus_repetitions
					))
	return output

def get_level2_inputs(input_root, categories=[], participants=[], scan_types=[]):
	import os
	l2_inputs = []
	for dirName, subdirList, fileList in os.walk(input_root, topdown=False):
		if subdirList == []:
			for my_file in fileList:
				candidate_l2_input = os.path.join(dirName,my_file)
				#the following string additions are performed to not accidentally match longer identifiers which include the shorter identifiers actually queried for. The path formatting is taken from the glm.py level1() datasync node, and will not work if that is modified.
				if (any(os.path.join(input_root,c)+"." in candidate_l2_input for c in categories) or not categories) and (any("."+p+"/" in candidate_l2_input for p in participants) or not participants) and (any("scan_type_"+s+"/" in candidate_l2_input for s in scan_types) or not scan_types):
					l2_inputs.append(candidate_l2_input)

	return l2_inputs

def get_scan(measurements_base, data_selection, selector, scan_type):
	import os #for some reason the import outside the function fails
	import pandas as pd
	scan_paths = []
	subject = selector[0]
	condition = selector[1]
	filtered_data = data_selection[(data_selection["condition"] == condition)&(data_selection["subject"] == subject)&(data_selection["scan_type"] == scan_type)]
	measurement_path = filtered_data["measurement"].tolist()[0]
	scan_subdir = filtered_data["scan"].tolist()[0]
	scan_path = os.path.join(measurements_base,measurement_path,scan_subdir)
	return scan_path, scan_type

def dcm_to_nii(dcm_dir, group_by="EchoTime", node=False):
	if node:
		nii_dir = os.getcwd()
	else:
		nii_dir = dcm_dir.replace("dicom", "nii")
		if not os.path.exists(nii_dir):
			os.makedirs(nii_dir)
	dcm_dir = dcm_dir+"/"
	stacker = dcmstack.DcmStack()

	results=[]
	if group_by:
		dicom_files = os.listdir(dcm_dir)
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
	import os

	if measurements:
		measurement_path_list = [os.path.join(workflow_base,i) for i in measurements]
	else:
		measurement_path_list = os.listdir(workflow_base)

	selected_measurements=[]
	#populate a list of lists with acceptable subject names, conditions, and sub_dir's
	for sub_dir in measurement_path_list:
		if sub_dir not in exclude_measurements:
			selected_measurement = []
			try:
				state_file = open(os.path.join(workflow_base,sub_dir,"subject"), "r")
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
									scan_program_file_path = os.path.join(workflow_base,sub_dir,"ScanProgram.scanProgram")
									scan_program_file = open(scan_program_file_path, "r")
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
								#If the ScanProgram.scanProgram file is small in size and the scan_type could not be matched, that may be because ParaVision failed
								#to write all the information into the file. This happens occasionally.
								#Thus we scan the individual acquisition protocols as well. These are a suboptimal and second choice, because acqp scans **also**
								#keep the original names the sequences had on import (ans may thus be misdetected, if the name was changed by the user after import).
								if os.stat(scan_program_file_path).st_size <= 700 and not scan_number:
									for sub_sub_dir in os.listdir(os.path.join(workflow_base,sub_dir)):
										try:
											acqp_file = os.path.join(workflow_base,sub_dir,sub_sub_dir,"acqp")
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

if __name__ == '__main__':
	write_events_file("EPI_CBV_jin40", STIM_PROTOCOL_DICTIONARY, scan_directory="~/NIdata/ofM.erc/20160421_124458_5500_1_2/13")
