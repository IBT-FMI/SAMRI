from itertools import product

def bids_substitution_iterator(sessions, subjects, scans, preprocessing_dir,
	l1_dir=None,
	l1_workdir=None,
	):
	"""A convenience layer to the SAMRI data structure"""
	if not l1_dir:
		l1_dir = preprocessing_dir
	if not l1_workdir:
		l1_workdir = l1_dir+"_work"
	substitutions=[]
	for subject, session, scan in product(subjects, sessions, scans):
		substitution={}
		substitution["subject"] = subject
		substitution["session"] = session
		substitution["scan"] = scan
		substitution["preprocessing_dir"] = preprocessing_dir
		substitution["l1_dir"] = l1_dir
		substitution["l1_workdir"] = l1_workdir
		substitutions.append(substitution)
	return substitutions
