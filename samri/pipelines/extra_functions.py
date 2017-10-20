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

STRUCTURAL_CONTRAST_MATCHING = {
	('T1','t1'):'T1w',
	('T2','t2'):'T2w',
	}
BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING = {
	('FLASH',):'T1w',
	('TurboRARE','TRARE'):'T2w',
	}
FUNCTIONAL_CONTRAST_MATCHING = {
	('BOLD','bold','Bold'):'bold',
	('CBV','cbv','Cbv'):'cbv',
	}

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

def get_scan(measurements_base, data_selection, scan_type,
	selector=None,
	subject=None,
	session=None,
	):
	"""Return the path to a Bruker scan selected by subject, session, and scan type, based on metadata previously extracted with `samri.preprocessing.extra_functions.get_data_selection()`.

	Parameters
	----------
	measurements_base : str
		Path to the measurements base path (this is simply prepended to the variable part of the path).
	data_selection : pandas.DataFrame
		A `pandas.DataFrame` object as produced by `samri.preprocessing.extra_functions.get_data_selection()`.
	scan_type : str
		The type of scan for which to determine the directory. This value will first be queried on the `data_selection` "trial" column, and if ounsuccesful on the "acq" column (corresponding to functional and structural scans respectively).
	selector : iterable, optional
		The first method of selecting the subject and scan, this value should be a length-2 list or tuple containing the subject and sthe session to be selected.
	subject : string, optional
		This has to be defined if `selector` is not defined. The subject for which to return a scan directory.
	session : string, optional
		This has to be defined if `selector` is not defined. The session for which to return a scan directory.
	"""
	import os #for some reason the import outside the function fails
	import pandas as pd
	scan_paths = []
	if not subject:
		subject = selector[0]
	if not session:
		session = selector[1]
	filtered_data = data_selection[(data_selection["session"] == session)&(data_selection["subject"] == subject)&(data_selection["scan_type"] == scan_type)]
	if filtered_data.empty:
		filtered_data = data_selection[(data_selection["session"] == session)&(data_selection["subject"] == subject)&(data_selection["acq"] == scan_type)]
	measurement_path = filtered_data["measurement"].item()
	scan_subdir = filtered_data["scan"].item()
	scan_path = os.path.join(measurements_base,measurement_path,scan_subdir)

	return scan_path, scan_type

def get_data_selection(workflow_base,
	sessions=[],
	scan_types=[],
	subjects=[],
	exclude_subjects=[],
	measurements=[],
	exclude_measurements=[],
	scan_type_category="functional",
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
									while True:
										current_line = scan_program_file.readline()
										if scan_type_category == 'functional':
											# we need to make sure that the trial identifier is a suffix, and not e.g. a subset of a different trial identifier string,
											# therefore we pad the string
											if all(i in current_line for i in indicator_line_matches) and scan_type+' ' in current_line:
												measurement_copy = scanprogram_functional_scan_info(scan_type, current_line, measurement_copy)
												selected_measurements.append(measurement_copy)
												break
										elif scan_type_category == 'structural':
											# we need to make sure that the acquisition identifier is a prefix, and not e.g. a subset of a different acquisition identifier string,
											# therefore we pad the string
											if all(i in current_line for i in indicator_line_matches) and '>'+scan_type in current_line:
												measurement_copy = scanprogram_structural_scan_info(scan_type, current_line, measurement_copy)
												selected_measurements.append(measurement_copy)
												break
										#avoid infinite while loop:
										if "</de.bruker.mri.entities.scanprogram.StudyScanProgramEntity>" in current_line:
											break
									#If the ScanProgram.scanProgram file is small in size and the scan_type could not be matched, that may be because ParaVision failed
									#to write all the information into the file. This happens occasionally.
									#Thus we scan the individual acquisition protocols as well. These are a suboptimal and second choice, because acqp scans **also**
									#keep the original names the sequences had on import (and may thus be misleading, if the name was changed by the user after import).
									if os.stat(scan_program_file_path).st_size <= 700 and not scan_number:
										raise(IOError)
								except IOError:
									for sub_sub_dir in os.listdir(os.path.join(workflow_base,sub_dir)):
										try:
											acqp_file_path = os.path.join(workflow_base,sub_dir,sub_sub_dir,"acqp")
											acqp_file = open(acqp_file_path,'r')
											while True:
												current_line = acqp_file.readline()
												if scan_type_category == 'functional':
													if scan_type+">" in current_line:
														scan_number = sub_sub_dir
														measurement_copy['scan'] = scan_number
														measurement_copy = acqp_functional_scan_info(scan_type, current_line, measurement_copy)
														selected_measurements.append(measurement_copy)
														break
												elif scan_type_category == 'structural':
													if "<"+scan_type in current_line:
														scan_number = sub_sub_dir
														measurement_copy['scan'] = scan_number
														measurement_copy = acqp_structural_scan_info(scan_type, current_line, measurement_copy)
														selected_measurements.append(measurement_copy)
														break
												if '##END=' in current_line:
													break
										except IOError:
											pass
										if scan_number:
											break
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


def scanprogram_structural_scan_info(scan_type, current_line, measurement_copy):
	acq = scan_type
	acquisition, paravision_numbering = current_line.split(" (E")
	scan_number = paravision_numbering.strip(")</displayName>\n")
	measurement_copy['scan'] = str(int(scan_number))
	measurement_copy['acq'] = acq
	measurement_copy['contrast'] = None
	for key in STRUCTURAL_CONTRAST_MATCHING:
		for i in key:
			if i in acquisition:
				measurement_copy['contrast'] = STRUCTURAL_CONTRAST_MATCHING[key]
				break
	if not measurement_copy['contrast']:
		for key in BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING:
			for i in key:
				if i in acquisition:
					measurement_copy['contrast'] = BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING[key]
					break
	return measurement_copy

def scanprogram_functional_scan_info(scan_type, current_line, measurement_copy):
	acquisition, paravision_numbering = current_line.split(scan_type)
	acquisition = acquisition.split('<displayName>')[1]
	scan_number = paravision_numbering.strip(" (E").strip(")</displayName>\n")
	measurement_copy['scan'] = str(int(scan_number))
	measurement_copy['scan_type'] = scan_type
	for key in FUNCTIONAL_CONTRAST_MATCHING:
		for i in key:
			if i in acquisition:
				measurement_copy['contrast'] = FUNCTIONAL_CONTRAST_MATCHING[key]
				acquisition = acquisition.replace(i,'')
				break
	acq = ''.join(ch for ch in acquisition if ch.isalnum())
	measurement_copy['acq'] = acq
	return measurement_copy

def acqp_structural_scan_info(scan_type, current_line, measurement_copy):
	measurement_copy['acq'] = scan_type
	measurement_copy['contrast'] = None
	for key in STRUCTURAL_CONTRAST_MATCHING:
		for i in key:
			if i in current_line:
				measurement_copy['contrast'] = STRUCTURAL_CONTRAST_MATCHING[key]
				break
	if not measurement_copy['contrast']:
		for key in BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING:
			for i in key:
				if i in current_line:
					measurement_copy['contrast'] = BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING[key]
					break
	return measurement_copy

def acqp_functional_scan_info(scan_type, current_line, measurement_copy):
	acquisition = current_line.split(scan_type+'>')[0]
	measurement_copy['scan_type'] = scan_type
	for key in FUNCTIONAL_CONTRAST_MATCHING:
		for i in key:
			if i in acquisition:
				measurement_copy['contrast'] = FUNCTIONAL_CONTRAST_MATCHING[key]
				acquisition = acquisition.replace(i,'')
				break
	acq = ''.join(ch for ch in acquisition if ch.isalnum())
	measurement_copy['acq'] = acq
	return measurement_copy
