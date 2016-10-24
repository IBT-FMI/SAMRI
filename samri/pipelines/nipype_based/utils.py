STIM_PROTOCOL_DICTIONARY={
	"EPI_CBV_jin6":"jin6",
	"EPI_CBV_jin10":"jin10",
	"EPI_CBV_jin20":"jin20",
	"EPI_CBV_jin40":"jin40",
	"EPI_CBV_jin60":"jin60",
	"EPI_CBV_alej":"alej",
	"7_EPI_CBV_jin6":"jin6",
	"7_EPI_CBV_jin10":"jin10",
	"7_EPI_CBV_jin20":"jin20",
	"7_EPI_CBV_jin40":"jin40",
	"7_EPI_CBV_jin60":"jin60",
	"7_EPI_CBV_alej":"alej",
	"7_EPI_CBV":"6_20_jb",
	}

def datasource_exclude(in_files, excludes, output="files"):
	"""Exclude file names from a list that match a BIDS-style specifications from a dictionary.

	Parameters
	----------

	in_files : list
	A list of flie names.

	excludes : dictionary
	A dictionary with keys which are "subjects", "sessions", or "scans", and values which are lists giving the subject, session, or scan identifier respectively.

	output : string
	Either "files" or "len". The former outputs the filtered file names, the latter the length of the resulting list.
	"""

	if not excludes:
		return in_files
	exclude_criteria=[]
	for key in excludes:
		if key in "subjects":
			for i in excludes[key]:
				exclude_criteria.append("sub-"+str(i))
		if key in "sessions":
			for i in excludes[key]:
				exclude_criteria.append("ses-"+str(i))
		if key in "scans":
			for i in excludes[key]:
				exclude_criteria.append("trial-"+str(i))
	out_files = [in_file for in_file in in_files if not any(criterion in in_file for criterion in exclude_criteria)]
	if output == "files":
		return out_files
	elif output == "len":
		return len(out_files)


def ss_to_path(subject_session):
	"""Concatenate a (subject, session) or (subject, session, scan) tuple to a BIDS-style path"""
	subject = "sub-" + subject_session[0]
	session = "ses-" + subject_session[1]
	return "/".join([subject,session])

def sss_to_source(source_format, subject=False, session=False, scan=False, subject_session_scan=False, base_directory=False, groupby=False):
	import os

	if any(a is False for a in [subject,session,scan]):
		(subject,session,scan) = subject_session_scan

	if groupby == "session":
		source = source_format.format("*", session, "*")
	else:
		source = source_format.format(subject, session, scan)
	if base_directory:
		source = os.path.join(base_directory, source)
	return source

def scs_filename(subject_condition, scan, scan_prefix="trial", suffix="", extension=".nii.gz"):
	"""Concatenate subject-condition and scan inputs to a BIDS-style filename

	Parameters
	----------

	subject_condition : list
	Length-2 list of subject and session identifiers

	scan : string
	Scan identifier

	suffix : string, optional
	Measurement type suffix (commonly "bold" or "cbv")
	"""
	# we do not want to modify the subject_condition iterator entry
	from copy import deepcopy
	subject_condition = deepcopy(subject_condition)

	subject_condition[0] = "sub-" + subject_condition[0]
	subject_condition[1] = "ses-" + subject_condition[1]
	if suffix:
		suffix = "_"+suffix
	if scan_prefix:
		scan = "".join([scan_prefix,"-",scan,suffix,extension])
	else:
		scan = "".join([scan,suffix,extension])
	subject_condition.append(scan)
	return "_".join(subject_condition)
