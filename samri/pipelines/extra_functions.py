import csv
import inspect
import os
import re
import json

from copy import deepcopy
import pandas as pd

BEST_GUESS_MODALITY_MATCH = {
	('FLASH',):'T1w',
	('TurboRARE','TRARE'):'T2w',
	}
BIDS_METADATA_EXTRACTION_DICTS = [
	{'field_name':'EchoTime',
		'query_file':'method',
		'regex':r'^##\$EchoTime=(?P<value>.*?)$',
		'scale': 1./1000.,
		'type': float,
		},
	{'field_name':'FlipAngle',
		'query_file':'visu_pars',
		'regex':r'^##\$VisuAcqFlipAngle=(?P<value>.*?)$',
		'type': float,
		},
	{'field_name':'Manufacturer',
		'query_file':'configscan',
		'regex':r'^##ORIGIN=(?P<value>.*?)$',
		},
	{'field_name':'NumberOfVolumesDiscardedByScanner',
		'query_file':'method',
		'regex':r'^##\$PVM_DummyScans=(?P<value>.*?)$',
		'type': int,
		},
	{'field_name':'ReceiveCoilName',
		'query_file':'configscan',
		'regex':r'.*?,COILTABLE,1#\$Name,(?P<value>.*?)#\$Id.*?',
		},
	{'field_name':'RepetitionTime',
		'query_file':'method',
		'regex':r'^##\$PVM_RepetitionTime=(?P<value>.*?)$',
		'scale': 1./1000.,
		'type': float,
		},
	{'field_name':'PulseSequenceType',
		'query_file':'method',
		'regex':r'^##\$Method=<Bruker:(?P<value>.*?)>$',
		},
	]
MODALITY_MATCH = {
	('BOLD','bold','Bold'):'bold',
	('CBV','cbv','Cbv'):'cbv',
	('T1','t1'):'T1w',
	('T2','t2'):'T2w',
	('MTon','MtOn'):'MTon',
	('MToff','MtOff'):'MToff',
	}

def force_dummy_scans(in_file,
	desired_dummy_scans=10,
	out_file="forced_dummy_scans_file.nii.gz",
	):
	"""Take a scan and crop initial timepoints depending upon the number of dummy scans (determined from a Bruker scan directory) and the desired number of dummy scans.

	in_file : string
	BIDS-compliant path to the 4D NIfTI file for which to force dummy scans.

	desired_dummy_scans : int , optional
	Desired timepoints dummy scans.
	"""

	import json
	import nibabel as nib
	from os import path

	out_file = path.abspath(path.expanduser(out_file))
	in_file = path.abspath(path.expanduser(in_file))
	in_file_base = path.splitext(in_file)[0]
	metadata_file = in_file_base+'.json'

	metadata = json.load(open(metadata_file))

	dummy_scans = 0
	try:
		dummy_scans = metadata['NumberOfVolumesDiscardedByScanner']
	except:
		pass

	delete_scans = desired_dummy_scans - dummy_scans

	img = nib.load(in_file)
	if delete_scans <= 0:
		nib.save(img,out_file)
	else:
		img_ = nib.Nifti1Image(img.get_data()[...,delete_scans:], img.affine, img.header)
		nib.save(img_,out_file)
	deleted_scans = delete_scans

	return out_file, deleted_scans

def get_tr(in_file,
	ndim=4,
	):
	"""Return the repetiton time of a NIfTI file.

	Parameters
	----------

	in_file : str
		Path to NIfTI file
	ndim : int
		Dimensionality of NIfTI file

	Returns
	-------

	float :
		Repetition Time
	"""

	import nibabel as nib
	from os import path

	in_file = path.abspath(path.expanduser(in_file))

	img = nib.load(in_file)
	header = img.header
	tr = header.get_zooms()[ndim-1]

	return tr

def write_bids_metadata_file(scan_dir, extraction_dicts,
	out_file="bids_metadata.json",
	task_name=False,
	):

	import json
	import re
	from os import path
	from samri.pipelines.utils import parse_paravision_date

	out_file = path.abspath(path.expanduser(out_file))
	scan_dir = path.abspath(path.expanduser(scan_dir))
	metadata = {}

	# Extract nice parameters:
	for extraction_dict in extraction_dicts:
		query_file = path.abspath(path.join(scan_dir,extraction_dict['query_file']))
		with open(query_file) as search:
			for line in search:
				if re.match(extraction_dict['regex'], line):
					m = re.match(extraction_dict['regex'], line)
					value = m.groupdict()['value']
					try:
						value = extraction_dict['type'](value)
					except KeyError:
						pass
					try:
						value = value * extraction_dict['scale']
					except KeyError:
						pass
					metadata[extraction_dict['field_name']] = value
					break
	# Extract DelayAfterTrigger
	try:
		query_file = path.abspath(path.join(scan_dir,'AdjStatePerScan'))
		read_line = False
		with open(query_file) as search:
			for line in search:
				if '##$AdjScanStateTime=( 2 )' in line:
					read_line = True
					continue
				if read_line:
					m = re.match(r'^<(?P<value>.*?)> <.*?>$', line)
					adjustments_start = m.groupdict()['value']
					adjustments_start = parse_paravision_date(adjustments_start)
					break
	except IOError:
		pass
	else:
		query_file = path.abspath(path.join(scan_dir,'acqp'))
		with open(query_file) as search:
			for line in search:
				if re.match(r'^##\$ACQ_time=<.*?>$', line):
					m = re.match(r'^##\$ACQ_time=<(?P<value>.*?)>$', line)
					adjustments_end = m.groupdict()['value']
					adjustments_end = parse_paravision_date(adjustments_end)
					break
		adjustments_duration = adjustments_end - adjustments_start
		metadata['DelayAfterTrigger'] = adjustments_duration.total_seconds()

	if task_name:
		metadata['TaskName'] = task_name

	with open(out_file, 'w') as out_file_writeable:
		json.dump(metadata, out_file_writeable, indent=1)
		out_file_writeable.write("\n")  # `json.dump` does not add a newline at the end; we do it here.

	return out_file

def write_bids_events_file(scan_dir,
	db_path="~/syncdata/meta.db",
	metadata_file='',
	out_file="events.tsv",
	prefer_labbookdb=False,
	timecourse_file='',
	task='',
	forced_dummy_scans=0.,
	):
	"""Adjust a BIDS event file to reflect delays introduced after the trigger and before the scan onset.

	Parameters
	----------

	scan_dir : str
		ParaVision scan directory path.
	db_path : str, optional
		LabbookDB database file path from which to source the evets profile for the identifier assigned to the `task` parameter.
	metadata_file : str, optional
		Path to a BIDS metadata file.
	out_file : str, optional
		Path to which to write the adjusted events file
	prefer_labbookdb : bool, optional
		Whether to query the events file in the LabbookDB database file first (rather than look for the events file in the scan directory).
	timecourse_file : str, optional
		Path to a NIfTI file.
	task : str, optional
		Task identifier from a LabbookDB database.

	Returns
	-------

	str : Path to which the adjusted events file was saved.
	"""

	import csv
	import sys
	import json
	import os
	import pandas as pd
	import nibabel as nib
	import numpy as np
	from datetime import datetime

	out_file = os.path.abspath(os.path.expanduser(out_file))
	scan_dir = os.path.abspath(os.path.expanduser(scan_dir))
	db_path = os.path.abspath(os.path.expanduser(db_path))

	if not prefer_labbookdb:
		try:
			scan_dir_contents = os.listdir(scan_dir)
			sequence_files = [i for i in scan_dir_contents if ("sequence" in i and "tsv" in i) or ('events' and 'tsv' in i)]
			sequence_file = os.path.join(scan_dir, sequence_files[0])
			mydf = pd.read_csv(sequence_file, sep="\s", engine='python')
		except IndexError:
			if os.path.isfile(db_path):
				from labbookdb.report.tracking import bids_eventsfile
				mydf = bids_eventsfile(db_path, task)
			else:
				return '/dev/null'
	else:
		try:
			if os.path.isfile(db_path):
				from labbookdb.report.tracking import bids_eventsfile
				mydf = bids_eventsfile(db_path, task)
			else:
				return '/dev/null'
		except ImportError:
			scan_dir_contents = os.listdir(scan_dir)
			sequence_files = [i for i in scan_dir_contents if "sequence" in i and "tsv" in i]
			sequence_file = os.path.join(scan_dir, sequence_files[0])
			mydf = pd.read_csv(sequence_file, sep="\s")

	timecourse_file = os.path.abspath(os.path.expanduser(timecourse_file))
	timecourse = nib.load(timecourse_file)
	zooms = timecourse.header.get_zooms()
	tr = float(zooms[-1])
	delay = 0.
	if forced_dummy_scans:
		delay = forced_dummy_scans * tr
	elif metadata_file:
		metadata_file = os.path.abspath(os.path.expanduser(metadata_file))

		with open(metadata_file) as metadata:
			    metadata = json.load(metadata)
		try:
			delay += metadata['NumberOfVolumesDiscardedByScanner'] * tr
		except:
			pass
		try:
			delay += metadata['DelayAfterTrigger']
		except:
			pass
	mydf['onset'] = mydf['onset'] - delay

	mydf.to_csv(out_file, sep=str('\t'), index=False)

	return out_file

def get_scan(measurements_base, data_selection,
	scan_type="",
	selector=None,
	subject=None,
	session=None,
	task=None,
	):
	"""Return the path to a Bruker scan selected by subject, session, and scan type, based on metadata previously extracted with `samri.preprocessing.extra_functions.get_data_selection()`.

	Parameters
	----------
	measurements_base : str
		Path to the measurements base path (this is simply prepended to the variable part of the path).
	data_selection : pandas.DataFrame
		A `pandas.DataFrame` object as produced by `samri.preprocessing.extra_functions.get_data_selection()`.
	scan_type : str
		The type of scan for which to determine the directory.
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
	if task:
		filtered_data = filtered_data[filtered_data["task"] == task]
	if scan_type:
		filtered_data = filtered_data[filtered_data["scan_type"] == scan_type]
	measurement_path = filtered_data["measurement"].item()
	scan_subdir = filtered_data["scan"].item()
	if measurement_path[0] == '/':
		scan_path = os.path.join(measurement_path,scan_subdir)
	else:
		scan_path = os.path.join(measurements_base,measurement_path,scan_subdir)

	if not task:
		try:
			task = filtered_data['task'].item()
		except KeyError:
			pass

	return scan_path, scan_type, task

def getSesAndData(grouped_df=None,
	):

	subject_session, data_selection = grouped_df
	return subject_session, data_selection

def get_bids_scan(bids_base, data_selection,
	ind_type = "",
	selector=None,
	subject=None,
	session=None,
	task=False,
	):

	"""Description...

	Parameters
	----------
	bids_base : str
		Path to the bids base path.
	data_selection : pandas.DataFrame
		A `pandas.DataFrame` object as produced by `samri.preprocessing.extra_functions.get_data_selection()`.
	scan_type : str
		The type of scan for which to determine the directory.
	selector : iterable, optional
		The first method of selecting the subject and scan, this value should be a length-2 list or tuple containing the subject and sthe session to be selected.
	subject : string, optional
		This has to be defined if `selector` is not defined. The subject for which to return a scan directory.
	session : string, optional
		This has to be defined if `selector` is not defined. The session for which to return a scan directory.
	"""
	import os #for some reason the import outside the function fails
	import pandas as pd

	filtered_data = []

	if(selector):
		subject = selector[0]
		session = selector[1]
		filtered_data = data_selection[(data_selection["session"] == session)&(data_selection["subject"] == subject)]
		filtered_data = filtered_data[filtered_data["modality"] == "anat"]
	else:
		filtered_data = data_selection[data_selection.index==ind_type]

	if(filtered_data.empty):
		raise Exception("SAMRIError: Does not exist" + str(selector[0]) + str(selector[1]) + str(ind_type))
	else:
		acq = filtered_data['acq'].item()
		typ = filtered_data['type'].item()
		subject = filtered_data['subject'].item()
		session = filtered_data['session'].item()
		modality = filtered_data['modality'].item()
		scan_type = filtered_data['scan_type'].item()
		subject_session = [subject, session]

		scan_path = os.path.join(bids_base, 'sub-' + subject + '/', 'ses-' + session + '/', modality )


		file_name = ''
		events_name = ''
		if(modality == 'func'):
			task = filtered_data['task'].item()
			file_name = 'sub-' + subject + '_' + 'ses-' + session + '_' + 'task-' + task + '_' + 'acq-' + acq + '_' + typ
			events_name = 'sub-' + subject + '_' + 'ses-' + session + '_' + 'task-' + task + '_' + 'acq-' + acq + '_' + 'events.tsv'
		else:
			file_name = 'sub-' + subject + '_' + 'ses-' + session + '_' + 'acq-' + acq + '_' + typ

		nii_name = file_name + '.nii.gz'
		nii_path = scan_path + '/' + file_name + '.nii'

		return scan_path, modality, task, nii_path, nii_name, file_name, events_name, subject_session

BIDS_KEY_DICTIONARY = {
	'acquisition':['acquisition','ACQUISITION','acq','ACQ'],
	'task':['task','TASK','stim','STIM','stimulation','STIMULATION'],
	}

def assign_modality(scan_type, record):
	"""Add a modality column with a corresponding value to a `pandas.DataFrame` object.

	Parameters
	----------
	scan_type: str
		A string potentially containing a modality identifier.
	record: pandas.DataFrame
		A `pandas.Dataframe` object.

	Returns
	-------
	An updated `pandas.DataFrame` obejct.
	"""
	for modality_group in MODALITY_MATCH:
		for modality_string in modality_group:
			if modality_string in scan_type:
				record['modality'] = MODALITY_MATCH[modality_group]
				return scan_type, record
	for modality_group in BEST_GUESS_MODALITY_MATCH:
		for modality_string in modality_group:
			if modality_string in scan_type:
				record['modality'] = BEST_GUESS_MODALITY_MATCH[modality_group]
				return scan_type, record
	return scan_type, record

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
					scan_type, record = assign_modality(scan_type, record)
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
	Return a `pandas.DaaFrame` object of the Bruker measurement directories located under a given base directory, and their respective scans, subjects, and tasks.

	Parameters
	----------
	workflow_base : str
		The path in which to query for Bruker measurement directories.
	match : dict
		A dictionary of matching criteria.
		The keys of this dictionary must be full BIDS key names (e.g. "task" or "acquisition"), and the values must be strings (e.g. "CogB") which, combined with the respective BIDS key, identify scans to be included (e.g. scans, the names of which containthe string "task-CogB" - delimited on either side by an underscore or the limit of the string).
	exclude : dict, optional
		A dictionary of exclusion criteria.
		The keys of this dictionary must be full BIDS key names (e.g. "task" or "acquisition"), and the values must be strings (e.g. "CogB") which, combined with the respective BIDS key, identify scans to be excluded(e.g. a scans, the names of which contain the string "task-CogB" - delimited on either side by an underscore or the limit of the string).
	measurements : list of str, optional
		A list of measurement directory names to be included exclusively (i.e. whitelist).
		If the list is empty, all directories (unless explicitly excluded via `exclude_measurements`) will be queried.
	exclude_measurements : list of str, optional
		A list of measurement directory names to be excluded from querying (i.e. a blacklist).

	Notes
	-----
	This data selector function is robust to `ScanProgram.scanProgram` files which have been truncated before the first detected match, but not to files truncated after at least one match.
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
						scan_dir_resolved = False
						try:
							with open(scan_program_file) as search:
								for line in search:
									measurement_copy = deepcopy(selected_measurement)
									if re.match(r'^[ \t]+<displayName>[a-zA-Z0-9-_]+? \(E\d+\)</displayName>[\r\n]+', line):
										m = re.match(r'^[ \t]+<displayName>(?P<scan_type>.+?) \(E(?P<number>\d+)\)</displayName>[\r\n]+', line)
										number = m.groupdict()['number']
										scan_type = m.groupdict()['scan_type']
										for key in match:
											if match_exclude_bids(key, match[key], measurement_copy, scan_type, number):
												selected_measurements.append(measurement_copy)
												scan_dir_resolved = True
												break
							if not scan_dir_resolved:
								raise IOError()
						except IOError:
							for sub_sub_dir in os.listdir(os.path.join(workflow_base,sub_dir)):
								measurement_copy = deepcopy(selected_measurement)
								acqp_file_path = os.path.join(workflow_base,sub_dir,sub_sub_dir,"acqp")
								scan_subdir_resolved = False
								try:
									with open(acqp_file_path,'r') as search:
										for line in search:
											if scan_subdir_resolved:
												break
											if re.match(r'^(?!/)<[a-zA-Z0-9-_]+?>[\r\n]+', line):
												number = sub_sub_dir
												m = re.match(r'^(?!/)<(?P<scan_type>.+?)>[\r\n]+', line)
												scan_type = m.groupdict()['scan_type']
												for key in match:
													if match_exclude_bids(key, match[key], measurement_copy, scan_type, number):
														selected_measurements.append(measurement_copy)
														scan_subdir_resolved = True
														break
										else:
											pass
								except IOError:
									pass
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

