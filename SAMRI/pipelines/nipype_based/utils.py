STIM_PROTOCOL_DICTINARY={
	"EPI_CBV_jin6":"jin6",
	"EPI_CBV_jin10":"jin10",
	"EPI_CBV_jin20":"jin20",
	"EPI_CBV_jin40":"jin40",
	"EPI_CBV_jin60":"jin60",
	"7_EPI_CBV":"6_20_jb"
	}

def subject_condition_to_path(subject_condition):
	# we do not want to modify the subject_condition iterator entry
	from copy import deepcopy
	subject_condition = deepcopy(subject_condition)
	subject_condition[0] = "sub-" + subject_condition[0]
	subject_condition[1] = "ses-" + subject_condition[1]
	return "/".join(subject_condition)

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
