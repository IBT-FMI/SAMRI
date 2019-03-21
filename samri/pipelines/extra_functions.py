# -*- coding: utf-8 -*-

import csv
import inspect
import os
import re
import json
import shutil

from copy import deepcopy
import pandas as pd
from bids.grabbids import BIDSLayout

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

def reset_background(in_file,
	bg_value=0,
	out_file='background_reset_complete.nii.gz',
	restriction_range='auto',
	):
	"""
	Set the background voxel value of a 4D NIfTI time series to a given value.
	It is sometimes necessary to perform this function, as some workflows may populate the background with values which may confuse statistics further downstream.
	Background voxels are not specifically highlighted, we define the background as the mode of any image, assuming there is decisively more background than any other one level of the contrast.
	If your data for some reason does not satisfy this assumption, the function will not behave correctly.

	Parameters
	----------

	in_file : string
		File for which to reset background values.
	bg_value : float, optional
		What value to insert in voxels identified as background.
	out_file : str, optional
		Path where the background reset NIfTI image will be written.
	restriction_range : int or string, optional
		What restricted range (if any) to use as the bounding box for the image area on which the mode is actually determined.
		If auto, the mode is determined on a bounding box the size of the smallest spatial axis.
		If the variable evaluates as false, no restriction will be used and the mode will be calculated given all spatial data --- which can be extremely time-consuming.
	"""

	import nibabel as nib
	import numpy as np
	from scipy import stats

	img = nib.load(in_file)
	data = img.get_data()
	number_of_slices = np.shape(data)[3]
	if restriction_range == 'auto':
		restriction_range = min(np.shape(data)[:3])
	for i in range(number_of_slices):
		if not restriction_range:
			old_bg_value = stats.mode(data[:,:,:,i])
		else:
			old_bg_value = stats.mode(data[:restriction_range,:restriction_range,:restriction_range,i].flatten())
		old_bg_value = old_bg_value.mode[0]
		data[:,:,:,i][data[:,:,:,i]==old_bg_value] = bg_value
	img_ = nib.Nifti1Image(data, img.affine, img.header)
	nib.save(img_,out_file)

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
	in_file_dir = path.dirname(in_file)
	in_file_name = path.basename(in_file)
	in_file_noext = in_file_name.split('.', 1)[0]
	metadata_file = path.join(in_file_dir, in_file_noext+'.json')

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
	"""Create a sidecar JSON file according to the BIDS standard.

	Parameters
	----------

	scan_dir : str
		Path to the scan directory containing the acquisition protocol files.
	extraction_dicts : str
		A list of dictionaries which contain keys including `query_file` (which specifies the file, relative to `scan dir`, which to query), `regex` (which gives a regex expression which will be tested against each rowin the file until a match is found), and `field_name` (which specifies under what field name to record this value in the JSON file).
		Additionally, the following keys are also supported: `type` (a python class operator, e.g. `str` to which the value should be converted), and `scale` (a float with which the value is multiplied before recording in JSON).
	out_file : str, optional
		Path under which to save the resulting JSON.
	task_name : str, optional
		String value to assign to the "TaskName" field in the BIDS JSON.
		If this parameter evaluates to false, no "TaskName" will be recorded.
	"""

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

def eventfile_add_habituation(in_file,
	amplitude_column='',
	discriminant_column='samri_l1_regressors',
	original_stimulation_value='stim',
	habituation_value='habituation',
	out_file="events.tsv",
	):
	"""Add habituation events to be used as regressors in BIDS file.

	Parameters
	----------

	in_file : str
		Path to TSV file with columns including 'onset' (formatted e.g. according to the BIDS specification).
	out_file : str, optional
		Path to which to write the adjusted events file

	Returns
	-------

	str : Path to which the adjusted events file was saved.
	"""

	import pandas as pd
	from copy import deepcopy
	from os import path

	in_file = path.abspath(path.expanduser(in_file))
	out_file = path.abspath(path.expanduser(out_file))

	df = pd.read_csv(in_file, sep="\t")
	# We need to ascertain events are listed in progressive chronological order.
	df = df.sort_values(by=['onset'], ascending=True)

	df[discriminant_column] = ""
	df[discriminant_column] = original_stimulation_value
	df_ = deepcopy(df)
	df_[discriminant_column] = habituation_value
	total_events=len(df)
	habituation_amplitudes = [i for i in range(total_events)[::-1]]
	if not amplitude_column:
		amplitude_column='samri_l1_amplitude'
	df_[amplitude_column] = habituation_amplitudes
	df[amplitude_column] = [1]*total_events

	df = pd.concat([df,df_], sort=False)

	df.to_csv(out_file, sep=str('\t'), index=False)

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
			sequence_files = [i for i in scan_dir_contents if ("sequence" in i and "tsv" in i)]
			if sequence_files:
				sequence_file = os.path.join(scan_dir, sequence_files[0])
			else:
				timecourse_dir = os.path.dirname(timecourse_file)
				timecourse_name = os.path.basename(timecourse_file)
				stripped_name = timecourse_name.split('.', 1)[0].rsplit('_', 1)[0]
				sequence_file = os.path.join(timecourse_dir,stripped_name+'_events.tsv')
			mydf = pd.read_csv(sequence_file, sep="\s", engine='python')
		except:
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
			sequence_files = [i for i in scan_dir_contents if ("sequence" in i and "tsv" in i)]
			if sequence_files:
				sequence_file = os.path.join(scan_dir, sequence_files[0])
			else:
				timecourse_dir = os.path.dirname(timecourse_file)
				timecourse_name = os.path.basename(timecourse_file)
				stripped_name = timecourse_name.split('.', 1)[0].rsplit('_', 1)[0]
				sequence_file = os.path.join(timecourse_dir,stripped_name+'_events.tsv')
			mydf = pd.read_csv(sequence_file, sep="\s", engine='python')

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

def corresponding_eventfile(timecourse_file, as_list=False):
	"""Based on a BIDS timecourse path, get the corresponding BIDS eventfile."""

	from os import path

	timecourse_dir = path.dirname(timecourse_file)
	timecourse_name = path.basename(timecourse_file)
	stripped_name = timecourse_name.split('.', 1)[0].rsplit('_', 1)[0]
	eventfile = path.join(timecourse_dir,stripped_name+'_events.tsv')

	if as_list:
		return [eventfile,]
	else:
		return eventfile

def get_bids_scan(data_selection,
	bids_base="",
	ind_type="",
	selector=None,
	subject=None,
	session=None,
	extra=['acq','run'],
	):

	"""Description...

	Parameters
	----------
	bids_base : str
		Path to the bids base path.
	data_selection : pandas.DataFrame
		A `pandas.DataFrame` object as produced by `samri.preprocessing.extra_functions.get_data_selection()`.
	selector : iterable, optional
		The first method of selecting the subject and scan, this value should be a length-2 list or tuple containing the subject and sthe session to be selected.
	subject : string, optional
		This has to be defined if `selector` is not defined. The subject for which to return a scan directory.
	session : string, optional
		This has to be defined if `selector` is not defined. The session for which to return a scan directory.
	"""
	import os #for some reason the import outside the function fails
	import pandas as pd
	from samri.pipelines.utils import bids_naming

	filtered_data = []

	if selector:
		subject = selector[0]
		session = selector[1]
		filtered_data = data_selection[(data_selection["session"] == session)&(data_selection["subject"] == subject)]
	else:
		filtered_data = data_selection[data_selection.index==ind_type]

	if filtered_data.empty:
		raise Exception("SAMRIError: Does not exist: " + str(selector[0]) + str(selector[1]) + str(ind_type))
	else:
		subject = filtered_data['subject'].item()
		session = filtered_data['session'].item()
		try:
			typ = filtered_data['type'].item()
		except:
			typ = ""
		try:
			task = filtered_data['task'].item()
		except:
			task = ""
		subject_session = [subject, session]
		#scan_path = os.path.join(bids_base, 'sub-' + subject + '/', 'ses-' + session + '/', typ )

		try:
			nii_path = filtered_data['path'].item()
		except KeyError:
			nii_path = filtered_data['measurement'].item()
			nii_path += '/'+filtered_data['scan'].item()
			nii_name = bids_naming(subject_session, filtered_data,
					extra=extra,
					extension='',
					)
			scan_path = nii_path
		else:
			scan_path = os.path.dirname(nii_path)
			nii_name = os.path.basename(nii_path)

		eventfile_name = bids_naming(subject_session, filtered_data,
				extra=extra,
				extension='.tsv',
				suffix='events'
				)
		metadata_filename = bids_naming(subject_session, filtered_data,
				extra=extra,
				extension='.json',
				)

		dict_slice = filtered_data.to_dict('records')[0]

		return scan_path, typ, task, nii_path, nii_name, eventfile_name, subject_session, metadata_filename, dict_slice

BIDS_KEY_DICTIONARY = {
	'acquisition':['acquisition','ACQUISITION','acq','ACQ'],
	'task':['task','TASK','stim','STIM','stimulation','STIMULATION'],
	}

def assign_modality(scan_type, record):
	"""
	Add a modality column with a corresponding value to a `pandas.DataFrame` object.

	Parameters
	----------
	scan_type: str
		A string potentially containing a modality identifier.
	record: pandas.DataFrame
		A `pandas.Dataframe` object.

	Returns
	-------
	An updated `pandas.DataFrame` obejct.

	Notes
	-----
	The term "modality" is ambiguous in BIDS; here we use it to mean what is better though of as "contrast":
	https://github.com/bids-standard/bids-specification/pull/119
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
	"""Return true if an entry is to be accepted based on the match and exclude criteria."""
	try:
		exclude_list = exclude[key]
	except KeyError:
		exclude_list = []
	try:
		match_list = match[key]
	except KeyError:
		match_list = []
	if entry not in exclude_list:
		if len(match_list) > 0 and (entry not in match_list or str(entry) not in match_list):
			return False
		record[key] = str(entry).strip(' ')
		return True
	else:
		return False

def get_data_selection(workflow_base,
	match={},
	exclude={},
	measurements=[],
	exclude_measurements=[],
	count_runs=False,
	fail_suffix='_failed',
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

	if not measurements:
		measurements = os.listdir(workflow_base)
	measurement_path_list = [os.path.join(workflow_base,i) for i in measurements]

	selected_measurements=[]
	#create a dummy path for bidsgrabber to parse file names from
	bids_temppath = '/var/tmp/samri_bids_temppaths/'
	try:
		os.mkdir(bids_temppath)
	except FileExistsError:
		pass
	layout = BIDSLayout(bids_temppath)
	#populate a list of lists with acceptable subject names, sessions, and sub_dir's
	for sub_dir in measurement_path_list:
		if sub_dir not in exclude_measurements:
			run_counter = 0
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
									line_considered = True
									measurement_copy = deepcopy(selected_measurement)
									if re.match(r'^[ \t]+<displayName>[a-zA-Z0-9-_]+? \(E\d+\)</displayName>[\r\n]+', line):
										if fail_suffix and re.match(r'^.+?{} \(E\d+\)</displayName>[\r\n]+'.format(fail_suffix), line):
											continue
										m = re.match(r'^[ \t]+<displayName>(?P<scan_type>.+?) \(E(?P<number>\d+)\)</displayName>[\r\n]+', line)
										number = m.groupdict()['number']
										scan_type = m.groupdict()['scan_type']
										bids_keys = layout.parse_file_entities('{}/{}'.format(bids_temppath,scan_type))
										for key in match:
											# Session and subject fields are not recorded in scan_type and were already checked at this point.
											if key in ['session', 'subject']:
												continue
											try:
												if bids_keys[key] not in match[key]:
													line_considered = False
													break
											except KeyError:
												line_considered = False
												break
										if line_considered:
											measurement_copy['scan_type'] = str(scan_type).strip(' ')
											measurement_copy['scan'] = str(int(number))
											measurement_copy['run'] = run_counter
											scan_type, measurement_copy= assign_modality(scan_type, measurement_copy)
											measurement_copy.update(bids_keys)
											run_counter += 1
											selected_measurements.append(measurement_copy)
											scan_dir_resolved = True
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
											line_considered = True
											if scan_subdir_resolved:
												break
											if re.match(r'^(?!/)<[a-zA-Z0-9-_]+?>[\r\n]+', line):
												if fail_suffix and re.match(r'^.+?{}$'.format(fail_suffix), line):
													continue
												number = sub_sub_dir
												m = re.match(r'^(?!/)<(?P<scan_type>.+?)>[\r\n]+', line)
												scan_type = m.groupdict()['scan_type']
												bids_keys = layout.parse_file_entities('{}/{}'.format(bids_temppath,scan_type))
												for key in match:
													# Session and subject fields are not recorded in scan_type and were already checked at this point.
													if key in ['session', 'subject']:
														continue
													try:
														if bids_keys[key] not in match[key]:
															line_considered = False
															break
													except KeyError:
														line_considered = False
														break
												if line_considered:
													measurement_copy['scan_type'] = str(scan_type).strip(' ')
													measurement_copy['scan'] = str(int(number))
													measurement_copy['run'] = run_counter
													scan_type, measurement_copy= assign_modality(scan_type, measurement_copy)
													measurement_copy.update(bids_keys)
													run_counter += 1
													selected_measurements.append(measurement_copy)
													scan_subdir_resolved = True
										else:
											pass
								except IOError:
									pass
						break #prevent loop from going on forever
			except IOError:
				print('Could not open {}'.format(os.path.join(workflow_base,sub_dir,"subject")))
				pass
	data_selection = pd.DataFrame(selected_measurements)
	shutil.rmtree(bids_temppath)
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
			if key in override:
				continue
			elif isinstance(bids_dictionary[key], (float, int, str)):
				df=df[df[key]==bids_dictionary[key]]
			else:
				df=df[df[key].isin(bids_dictionary[key])]
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

