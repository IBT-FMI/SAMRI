import os
import re

from samri.utilities import iter_collapse_by_path

def collapse_nifti(in_dir, out_dir):
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
	out_files = [re.sub(r'^' + re.escape(in_dir), '', i) for i in in_files]
	out_files = [os.path.join(out_dir,i[1:]) for i in out_files]
	out_files = iter_collapse_by_path(in_files, out_files)
