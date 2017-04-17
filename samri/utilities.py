from itertools import product

def bids_substitution_iterator(sessions, subjects, scans, preprocessing_dir,
	l1_dir=None,
	l1_workdir=None,
	preprocessing_workdir=None,
	):
	"""A convenience layer to the SAMRI data structure"""
	if not l1_dir:
		l1_dir = preprocessing_dir
	if not l1_workdir:
		l1_workdir = l1_dir+"_work"
	if not preprocessing_workdir:
		preprocessing_workdir = preprocessing_dir+"_work"
	substitutions=[]
	for subject, session, scan in product(subjects, sessions, scans):
		substitution={}
		substitution["l1_dir"] = l1_dir
		substitution["l1_workdir"] = l1_workdir
		substitution["preprocessing_dir"] = preprocessing_dir
		substitution["preprocessing_workdir"] = preprocessing_workdir
		substitution["scan"] = scan
		substitution["session"] = session
		substitution["subject"] = subject
		substitutions.append(substitution)
	return substitutions
