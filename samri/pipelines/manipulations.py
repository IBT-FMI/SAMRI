import multiprocessing
import os
import re

from samri.utilities import collapse, N_PROCS

N_PROCS=max(N_PROCS-2, 1)

def collapse_nifti(in_dir, out_dir,
	n_procs=N_PROCS,
	):
	in_dir = os.path.abspath(os.path.expanduser(in_dir))
	out_dir = os.path.abspath(os.path.expanduser(out_dir))
	in_files = []
	for root, dirs, files in os.walk(in_dir):
		_in_files = [os.path.join(root,f) for f in files]
		_in_files = [i for i in _in_files if os.path.isfile(i)]
		# Only NIfTI files:
		_in_files = [i for i in _in_files if '.nii' in i]
		in_files.extend(_in_files)
	# Make relative to `in_dir`:
	out_files = [re.sub(r'^' + re.escape(in_dir), '', i) for i in _in_files]
	out_files = [re.sub(out_dir,i) for i in _in_files]
	file_paths = zip(in_files, out_files)
	pool = multiprocessing.Pool(n_procs)
	out = pool.map(collapse, file_paths)
	print(out)
