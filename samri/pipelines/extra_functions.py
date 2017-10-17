import csv
import inspect
import os
import re

from copy import deepcopy
import nibabel as nb
import pandas as pd
try:
	from utils import STIM_PROTOCOL_DICTIONARY
except ImportError:
	from .utils import STIM_PROTOCOL_DICTIONARY

def force_dummy_scans(in_file, scan_dir,
	desired_dummy_scans=10,
	out_file="forced_dummy_scans_file.nii.gz",
	):
	"""Take a scan and crop initial timepoints depending upon the number of dummy scans (determined from a Bruker scan directory) and the desired number of dummy scans.

	in_file : string
	Path to the 4D NIfTI file for which to force dummy scans.

	scan_dir : string
	Path to the corresponding Bruker directory of the scan_dir.

	desired_dummy_scans : int , optional
	Desired timepoints dummy scans.
	"""

	import nibabel as nib
	from os import path

	out_file = path.abspath(path.expanduser(out_file))

	method_file_path = path.join(scan_dir,"method")
	method_file = open(method_file_path, "r")
	dummy_scans = 0
	while True:
		current_line = method_file.readline()
		if "##$PVM_DummyScans=" in current_line:
			dummy_scans = int(current_line.split("=")[1])
			break

	delete_scans = desired_dummy_scans - dummy_scans

	if delete_scans <= 0:
		out_file = in_file
	else:
		img = nib.load(in_file)
		img_ = nib.Nifti1Image(img.get_data()[...,delete_scans:], img.affine, img.header)
		nib.save(img_,out_file)

	return out_file

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

def write_events_file(scan_dir, scan_type,
	stim_protocol_dictionary={},
	db_path="~/syncdata/meta.db",
	out_file="events.tsv",
	dummy_scans_ms="determine",
	subject_delay=False,
	very_nasty_bruker_delay_hack=False,
	):

	import csv
	import sys
	from datetime import datetime
	from os import path
	import pandas as pd
	import numpy as np

	out_file = path.abspath(path.expanduser(out_file))

	if not subject_delay:
		scan_dir = path.abspath(path.expanduser(scan_dir))
		state_file_path = path.join(scan_dir,"AdjStatePerScan")

		#Here we read the `AdjStatePerScan` file, which may be missing if no adjustments were run at the beginning of this scan
		try:
			state_file = open(state_file_path, "r")
		except IOError:
			delay_seconds = 0
		else:
			while True:
				current_line = state_file.readline()
				if "AdjScanStateTime" in current_line:
					delay_datetime_line = state_file.readline()
					break

			trigger_time, scanstart_time = [datetime.utcnow().strptime(i.split("+")[0], "<%Y-%m-%dT%H:%M:%S,%f") for i in delay_datetime_line.split(" ")]
			delay = scanstart_time-trigger_time
			delay_seconds=delay.total_seconds()
			if very_nasty_bruker_delay_hack:
				delay_seconds += 12

		#Here we read the `method` file, which contains info about dummy scans
		method_file_path = path.join(scan_dir,"method")
		method_file = open(method_file_path, "r")

		read_variables=0 #count variables so that breaking takes place after both have been read

		if dummy_scans_ms == "determine":
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

		subject_delay = delay_seconds + dummy_scans_ms/1000
	try:
		trial_code = stim_protocol_dictionary[scan_type]
	except KeyError:
		trial_code = scan_type

	from labbookdb.report.tracking import bids_eventsfile
	mydf = bids_eventsfile(db_path, trial_code)
	mydf['onset'] = mydf['onset'] - subject_delay
	mydf.to_csv(out_file, sep=str('\t'), index=False)

	return out_file

def get_subjectinfo(subject_delay, scan_type, scan_types):
	from nipype.interfaces.base import Bunch
	import pandas as pd
	import numpy as np
	from copy import deepcopy
	import sys
	sys.path.append('/home/chymera/src/LabbookDB/db/')
	from query import load_session
	from common_classes import StimulationProtocol
	db_path="~/syncdata/meta.db"

	session, engine = load_session(db_path)

	sql_query=session.query(StimulationProtocol).filter(StimulationProtocol.code==scan_types[scan_type])
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

def stimulus_protocol_bunch(eventfile_path):
	eventfile_df = pd.read_csv(eventfile_path)

def bids_inputs(input_root, categories=[], participants=[], scan_types=[]):
	import os
	l2_inputs = []
	for dirName, subdirList, fileList in os.walk(input_root, topdown=False):
		if subdirList == []:
			for my_file in fileList:
				candidate_l2_input = os.path.join(dirName,my_file)
				#the following string additions are performed to not accidentally match longer identifiers which include the shorter identifiers actually queried for. The path formatting is taken from the glm.py level1() datasync node, and will not work if that is modified.
				if not "/anat/" in candidate_l2_input and candidate_l2_input[-11:] != "_events.tsv":
					if (any("ses-"+c in candidate_l2_input for c in categories) or not categories) and (any("sub-"+p in candidate_l2_input for p in participants) or not participants) and (any("scan_type_"+s+"/" in candidate_l2_input for s in scan_types) or not scan_types):
						l2_inputs.append(candidate_l2_input)

	return l2_inputs


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

def get_scan(measurements_base, data_selection, scan_type, selector=None, subject=None, session=None):
	import os #for some reason the import outside the function fails
	import pandas as pd
	scan_paths = []
	if not subject:
		subject = selector[0]
	if not session:
		session = selector[1]
	filtered_data = data_selection[(data_selection["session"] == session)&(data_selection["subject"] == subject)&(data_selection["scan_type"] == scan_type)]
	measurement_path = filtered_data["measurement"].tolist()[0]
	scan_subdir = filtered_data["scan"].tolist()[0]
	scan_path = os.path.join(measurements_base,measurement_path,scan_subdir)
	return scan_path, scan_type

#contrast_matchings = {
#	('EPI','epi'):'EPI',
#	('seEPI','se_EPI','se-EPI','spinechoEPI','spinecho_EPI','spinecho-EPI','spinEPI','spin_EPI','spin-EPI'):'seEPI',
#	('geEPI','ge_EPI','ge-EPI','gradientechoEPI','gradientecho_EPI','gradientecho-EPI','gradientEPI','gradient_EPI','gradient-EPI'):'seEPI',
#	('','epi','Epi'):'EPI',
#	}
contrast_matching = {
	('BOLD','bold','Bold'):'bold',
	('CBV','cbv','Cbv'):'cbv',
	}

def get_data_selection(workflow_base,
	sessions=[],
	scan_types=[],
	subjects=[],
	exclude_subjects=[],
	measurements=[],
	exclude_measurements=[],
	):
	"""
	Return a `pandas.DaaFrame` object of the Bruker measurement directories located under a given base directory, and their respective scans, subjects, and trials.

	Parameters
	----------
	workflow_base : str
		The path in which to query for Bruker measurement directories.
	"""

	workflow_base = os.path.abspath(os.path.expanduser(workflow_base))

	if measurements:
		measurement_path_list = [os.path.join(workflow_base,i) for i in measurements]
	else:
		measurement_path_list = os.listdir(workflow_base)

	selected_measurements=[]
	#populate a list of lists with acceptable subject names, sessions, and sub_dir's
	for sub_dir in measurement_path_list:
		if sub_dir not in exclude_measurements:
			selected_measurement = {}
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
								selected_measurement['subject'] = entry
						else:
							break
						read_variables +=1 #count recorded variables
					if "##$SUBJECT_study_name=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if entry in sessions or len(sessions) == 0:
							selected_measurement['session'] = entry
						else:
							break
						read_variables +=1 #count recorded variables
					if read_variables == 2:
						selected_measurement['measurement'] = sub_dir
						#if the directory passed both the subject and sessions tests, append a line for it
						if not scan_types:
							#add two empty entries to fill columns otherwise dedicated to the scan program
							selected_measurements.append(selected_measurement)
						#if various scan types are selected extend and copy lines to accommodate:
						else:
							for scan_type in scan_types:
								measurement_copy = deepcopy(selected_measurement)
								scan_number=None
								try:
									scan_program_file_path = os.path.join(workflow_base,sub_dir,"ScanProgram.scanProgram")
									scan_program_file = open(scan_program_file_path, "r")
									indicator_line_matches = ['<displayName>', '</displayName>\n', '(', ')']
									suffix_scan_type = scan_type+' '
									while True:
										current_line = scan_program_file.readline()
										if all(i in current_line for i in indicator_line_matches) and suffix_scan_type in current_line:
											acquisition, paravision_numbering = current_line.split(suffix_scan_type)
											scan_number = paravision_numbering.strip("(E").strip(")</displayName>\n")
											measurement_copy['scan_type'] = scan_type
											measurement_copy['scan'] = scan_number
											for key in contrast_matching:
												if any(i in acquisition for i in key):
													measurement_copy['contrast'] = contrast_matching[key]
											selected_measurements.append(measurement_copy)
											break
										#avoid infinite while loop:
										if "</de.bruker.mri.entities.scanprogram.StudyScanProgramEntity>" in current_line:
											break
								except IOError:
									pass
								#If the ScanProgram.scanProgram file is small in size and the scan_type could not be matched, that may be because ParaVision failed
								#to write all the information into the file. This happens occasionally.
								#Thus we scan the individual acquisition protocols as well. These are a suboptimal and second choice, because acqp scans **also**
								#keep the original names the sequences had on import (and may thus be misleading, if the name was changed by the user after import).
								if os.stat(scan_program_file_path).st_size <= 700 and not scan_number:
									for sub_sub_dir in os.listdir(os.path.join(workflow_base,sub_dir)):
										try:
											acqp_file = os.path.join(workflow_base,sub_dir,sub_sub_dir,"acqp")
											if "<"+scan_type+">" in open(acqp_file).read():
												scan_number = sub_sub_dir
												measurement_copy['scan_type'] = scan_type
												measurement_copy['scan'] = scan_number
												for key in contrast_matching:
													if any(i in acquisition for i in key):
														measurement_copy['contrast'] = contrast_matching[key]
												selected_measurements.append(measurement_copy)
										except IOError:
											pass
						break #prevent loop from going on forever
			except IOError:
				pass

	data_selection = pd.DataFrame(selected_measurements)

	#drop subjects which do not have measurements for all sessions
	if len(sessions) > 1:
		for subject in set(data_selection["subject"]):
			if len(data_selection[(data_selection["subject"] == subject)]) < len(sessions):
				data_selection = data_selection[(data_selection["subject"] != subject)]

	return data_selection
