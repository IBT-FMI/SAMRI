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

def write_events_file(scan_dir, trial,
	stim_protocol_dictionary={},
	db_path="~/syncdata/meta.db",
	out_file="events.tsv",
	dummy_scans_ms="determine",
	subject_delay=False,
	very_nasty_bruker_delay_hack=False,
	prefer_labbookdb=False,
	):

	import csv
	import sys
	from datetime import datetime
	import os
	import pandas as pd
	import numpy as np

	out_file =os.path.abspath(os.path.expanduser(out_file))
	scan_dir =os.path.abspath(os.path.expanduser(scan_dir))

	if not subject_delay:
		state_file_path = os.path.join(scan_dir,"AdjStatePerScan")

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
		method_file_path = os.path.join(scan_dir,"method")
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
		trial_code = stim_protocol_dictionary[trial]
	except KeyError:
		trial_code = trial

	if not prefer_labbookdb:
		try:
			scan_dir_contents = os.listdir(scan_dir)
			sequence_files = [i for i in scan_dir_contents if "sequence" in i and "tsv" in i]
			sequence_file = os.path.join(scan_dir, sequence_files[0])
			mydf = pd.read_csv(sequence_file, sep="\s")
		except IndexError:
			from labbookdb.report.tracking import bids_eventsfile
			mydf = bids_eventsfile(db_path, trial_code)
	else:
		try:
			from labbookdb.report.tracking import bids_eventsfile
			mydf = bids_eventsfile(db_path, trial_code)
		except ImportError:
			scan_dir_contents = os.listdir(scan_dir)
			sequence_files = [i for i in scan_dir_contents if "sequence" in i and "tsv" in i]
			sequence_file = os.path.join(scan_dir, sequence_files[0])
			mydf = pd.read_csv(sequence_file, sep="\s")

	mydf['onset'] = mydf['onset'] - subject_delay
	mydf.to_csv(out_file, sep=str('\t'), index=False)

	return out_file

def get_subjectinfo(subject_delay, scan_type, scan_types):
	from nipype.interfaces.base import Bunch
	import pandas as pd
	import numpy as np
	from copy import deepcopy
	import sys
	sys.path.append('~/src/LabbookDB/db/')
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

	scan_paths = []
	return l2_inputs

def get_scan(measurements_base, data_selection,
	scan_type=False,
	selector=None,
	subject=None,
	session=None,
	trial=False,
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

	if not subject:
		subject = selector[0]
	if not session:
		session = selector[1]
	filtered_data = data_selection[(data_selection["session"] == session)&(data_selection["subject"] == subject)]
	if trial:
		filtered_data = filtered_data[filtered_data["trial"] == trial]
	if scan_type:
		filtered_data = filtered_data[filtered_data["scan_type"] == scan_type]
	measurement_path = filtered_data["measurement"].item()
	scan_subdir = filtered_data["scan"].item()
	scan_path = os.path.join(measurements_base,measurement_path,scan_subdir)

	if not trial:
		trial = filtered_data['trial'].item()

	return scan_path, scan_type, trial

def _get_data_selection(workflow_base,
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
									indicator_line_matches = ['<displayName>', '</displayName>\n', '(', ')']
									with open(scan_program_file_path, "r") as scan_program_file:
										for current_line in scan_program_file:
											if scan_type_category == 'functional':
												# we need to make sure that the trial identifier is a suffix, and not e.g. a subset of a different trial identifier string,
												# therefore we pad the string
												if all(i in current_line for i in indicator_line_matches) and scan_type+' ' in current_line:
													measurement_copy_ = deepcopy(measurement_copy)
													measurement_copy_ = scanprogram_functional_scan_info(scan_type, current_line, measurement_copy_)
													selected_measurements.append(measurement_copy_)
											elif scan_type_category == 'structural':
												#t we need to make sure that the acquisition identifier is a prefix, and not e.g. a subset of a different acquisition identifier string,
												# therefore we pad the string
												if all(i in current_line for i in indicator_line_matches) and scan_type in current_line:
													measurement_copy_ = deepcopy(measurement_copy)
													measurement_copy_ = scanprogram_structural_scan_info(scan_type, current_line, measurement_copy_)
													selected_measurements.append(measurement_copy_)
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
											with open(acqp_file_path,'r') as acqp_file:
												for current_line in acqp_file:
													if scan_type_category == 'functional':
														if scan_type+">" in current_line:
															scan_number = sub_sub_dir
															measurement_copy['scan'] = scan_number
															measurement_copy = acqp_functional_scan_info(scan_type, current_line, measurement_copy)
															selected_measurements.append(measurement_copy)
															break
													elif scan_type_category == 'structural':
														if scan_type in current_line:
															scan_number = sub_sub_dir
															measurement_copy['scan'] = scan_number
															measurement_copy = acqp_structural_scan_info(scan_type, current_line, measurement_copy)
															selected_measurements.append(measurement_copy)
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

def match_exclude_ss(entry, match, exclude, record, key):
	try:
		exclude_list = exclude[key]
	except KeyError:
		exclude_list = []
	try:
		match_list = match[key]
	except KeyError:
		match_list = []
	if entry not in exclude_list:
		if len(match_list) > 0 and entry not in match_list:
			return False
		else:
			record[key] = str(entry).strip(' ')
		return True
	else:
		return False

BIDS_KEY_DICTIONARY = {
	'acquisition':['acquisition','ACQUISITION','acq','ACQ'],
	'trial':['trial','TRIAL','stim','STIM','stimulation','STIMULATION'],
	}

def assign_contrast(scan_type, record):
	"""Add a contrast column with a corresponding value to a `pandas.DataFrame` object.

	Parameters
	----------
	scan_type: str
		A string potentially containing a contrast identifier.
	record: pandas.DataFrame
		A `pandas.Dataframe` object.

	Returns
	-------
	An updated `pandas.DataFrame` obejct.
	"""
	for contrast_group in FUNCTIONAL_CONTRAST_MATCHING:
		for contrast_string in contrast_group:
			if contrast_string in scan_type:
				record['contrast'] = FUNCTIONAL_CONTRAST_MATCHING[contrast_group]
				scan_type = scan_type.replace(contrast_string,'')
				return scan_type, record
	for contrast_group in BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING:
		for contrast_string in contrast_group:
			if contrast_string in scan_type:
				record['contrast'] = BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING[contrast_group]
	BEST_GUESS_STRUCTURAL_CONTRAST_MATCHING

	return scan_type, record

def match_exclude_bids(key, values, record, scan_type, number):
	key_alternatives = BIDS_KEY_DICTIONARY[key]
	for alternative in key_alternatives:
		if alternative in scan_type:
			for value in values:
				match_string = r'(^|.*?_|.*? ){alternative}-{value}( .*?|_.*?|$)'.format(alternative=alternative,value=value)
				if re.match(match_string, scan_type):
					record['scan_type'] = str(scan_type).strip(' ')
					record['scan'] = str(int(number))
					record[key] = str(value).strip(' ')
					scan_type, record = assign_contrast(scan_type, record)
					for key_ in BIDS_KEY_DICTIONARY:
						for alternative_ in BIDS_KEY_DICTIONARY[key_]:
							if alternative_ in scan_type:
								match_string_ = r'(^|.*?_|.*? ){}-(?P<value>\w+?)( .*?|_.*?|$)'.format(alternative_)
								m = re.match(match_string_, scan_type)
								try:
									value_ = m.groupdict()['value']
								except AttributeError:
									pass
								else:
									record[key_] = str(value_).strip(' ')
					return True
	return False

def get_data_selection(workflow_base,
	match={},
	exclude={},
	measurements=[],
	exclude_measurements=[],
	):
	"""
	Return a `pandas.DaaFrame` object of the Bruker measurement directories located under a given base directory, and their respective scans, subjects, and trials.

	Parameters
	----------
	workflow_base : str
		The path in which to query for Bruker measurement directories.
	match : dict
		A dictionary of matching criteria.
		The keys of this dictionary must be full BIDS key names (e.g. "trial" or "acquisition"), and the values must be strings (e.g. "CogB") which, combined with the respective BIDS key, identify scans to be included (e.g. scans, the names of which containthe string "trial-CogB" - delimited on either side by an underscore or the limit of the string).
	exclude : dict, optional
		A dictionary of exclusion criteria.
		The keys of this dictionary must be full BIDS key names (e.g. "trial" or "acquisition"), and the values must be strings (e.g. "CogB") which, combined with the respective BIDS key, identify scans to be excluded(e.g. a scans, the names of which contain the string "trial-CogB" - delimited on either side by an underscore or the limit of the string).
	measurements : list of str, optional
		A list of measurement directory names to be included exclusively (i.e. whitelist).
		If the list is empty, all directories (unless explicitly excluded via `exclude_measurements`) will be queried.
	exclude_measurements : list of str, optional
		A list of measurement directory names to be excluded from querying (i.e. a blacklist).
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
						if not match_exclude_ss(entry, match, exclude, selected_measurement, 'subject'):
							break
						read_variables +=1 #count recorded variables
					if "##$SUBJECT_study_name=" in current_line:
						entry=re.sub("[<>\n]", "", state_file.readline())
						if not match_exclude_ss(entry, match, exclude, selected_measurement, 'session'):
							break
						read_variables +=1 #count recorded variables
					if read_variables == 2:
						selected_measurement['measurement'] = sub_dir
						scan_program_file = os.path.join(workflow_base,sub_dir,"ScanProgram.scanProgram")
						try:
							with open(scan_program_file) as search:
								for line in search:
									measurement_copy = deepcopy(selected_measurement)
									if re.match(r'^[ \t]+<displayName>.+?\(E\d+\)</displayName>[\r\n]+', line):
										m = re.match(r'^[ \t]+<displayName>(?P<scan_type>.*?)\(E(?P<number>\d+)\)</displayName>[\r\n]+', line)
										number = m.groupdict()['number']
										scan_type = m.groupdict()['scan_type']
										for key in match:
											if match_exclude_bids(key, match[key], measurement_copy, scan_type, number):
												selected_measurements.append(measurement_copy)
												break
						except IOError:
							for sub_sub_dir in os.listdir(os.path.join(workflow_base,sub_dir)):
								measurement_copy = deepcopy(selected_measurement)
								acqp_file_path = os.path.join(workflow_base,sub_dir,sub_sub_dir,"acqp")
								scan_dir_resolved = False
								while scan_dir_resolved == False:
									try:
										with open(acqp_file_path,'r') as search:
											for line in search:
												if re.match(r'^(?!/)<.+?>[\r\n]+', line):
													number = sub_sub_dir
													m = re.match(r'^(?!/)<(?P<scan_type>.+?)>[\r\n]+', line)
													scan_type = m.groupdict()['scan_type']
													for key in match:
														if match_exclude_bids(key, match[key], measurement_copy, scan_type, number):
															selected_measurements.append(measurement_copy)
															scan_dir_resolved = True
															break
												if scan_dir_resolved:
													break
											scan_dir_resolved = True
									except IOError:
										scan_dir_resolved = True
						break #prevent loop from going on forever
			except IOError:
				pass

	data_selection = pd.DataFrame(selected_measurements)
	return data_selection


def select_from_datafind_df(df,
	bids_dictionary=False,
	bids_dictionary_override=False,
	output_key='path',
	failsafe=False,
	list_output=False,
	):


	if bids_dictionary_override:
		override = [i for i in bids_dictionary_override.keys()]
	else:
		override = []
	override.append(output_key)

	if bids_dictionary:
		for key in bids_dictionary:
			if not key in override:
				df=df[df[key]==bids_dictionary[key]]
	if bids_dictionary_override:
		for key in bids_dictionary_override:
				df=df[df[key]==bids_dictionary_override[key]]

	if list_output:
		selection = df[output_key].tolist()
	else:
		if failsafe:
			df = df.iloc[0]
		selection = df[output_key].item()

	return selection


def scanprogram_structural_scan_info(scan_type, current_line, measurement_copy):
	acq = scan_type
	acquisition, paravision_numbering = current_line.split(" (E")
	acquisition = acquisition.split('<displayName>')[1]
	scan_number = paravision_numbering.strip(")</displayName>\n")
	measurement_copy['scan_type'] = acquisition
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
	acquisition, paravision_numbering = current_line.split(" (E")
	acquisition = acquisition.split('<displayName>')[1]
	scan_number = paravision_numbering.strip(")</displayName>\n")
	acq = acquisition.split(scan_type)[0]
	measurement_copy['scan_type'] = acquisition
	measurement_copy['scan'] = str(int(scan_number))
	measurement_copy['trial'] = scan_type
	for key in FUNCTIONAL_CONTRAST_MATCHING:
		for i in key:
			if i in acq:
				measurement_copy['contrast'] = FUNCTIONAL_CONTRAST_MATCHING[key]
				acq = acq.replace(i,'')
				break
	acq = ''.join(ch for ch in acq if ch.isalnum())
	measurement_copy['acq'] = acq
	return measurement_copy

def acqp_structural_scan_info(scan_type, current_line, measurement_copy):
	measurement_copy['scan_type'] = current_line.split('>')[0].split('<')[1]
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
	measurement_copy['scan_type'] = current_line.split('>')[0].split('<')[1]
	acquisition = current_line.split(scan_type+'>')[0]
	measurement_copy['trial'] = scan_type
	for key in FUNCTIONAL_CONTRAST_MATCHING:
		for i in key:
			if i in acquisition:
				measurement_copy['contrast'] = FUNCTIONAL_CONTRAST_MATCHING[key]
				acquisition = acquisition.replace(i,'')
				break
	acq = ''.join(ch for ch in acquisition if ch.isalnum())
	measurement_copy['acq'] = acq
	return measurement_copy
