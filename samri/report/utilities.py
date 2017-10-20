import numpy as np
import nibabel as nib
import pandas as pd
from copy import deepcopy
from os import path

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass
def add_roi_data(img_path,masker,
	substitution=False,
	):
	"""Return a per-subject and a per-voxel dataframe containing the mean and voxelwise ROI t-scores"""
	subject_data={}
	if substitution:
		img_path = img_path.format(**substitution)
	img_path = path.abspath(path.expanduser(img_path))
	try:
		img = nib.load(img_path)
		img = masker.fit_transform(img)
		img = img.flatten()
		mean = np.nanmean(img)
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		subject_data["session"]=substitution["session"]
		subject_data["subject"]=substitution["subject"]
		voxel_datas=[]
		for ix, i in enumerate(img):
			voxel_data = deepcopy(subject_data)
			voxel_data["voxel"]=ix
			voxel_data["t"]=i
			voxel_data = pd.DataFrame(voxel_data, index=[None])
			voxel_datas.append(voxel_data)
		vdf = pd.concat(voxel_datas)
		subject_data["t"]=mean
		sdf = pd.DataFrame(subject_data, index=[None])
		return sdf, vdf

def add_pattern_data(substitution,img_path,pattern,
	voxels=False,
	):
	"""Return a per-subject and a per-voxel dataframe containing the mean and voxelwise multivariate patern scores"""
	subject_data={}
	if substitution:
		img_path = img_path.format(**substitution)
	img_path = path.abspath(path.expanduser(img_path))
	try:
		img = nib.load(img_path)
		img_data = img.get_data()
	except (FileNotFoundError, nib.py3k.FileNotFoundError):
		return pd.DataFrame({}), pd.DataFrame({})
	else:
		pattern_evaluation = img_data*pattern
		pattern_evaluation = pattern_evaluation.flatten()
		pattern_score = np.nanmean(pattern_evaluation)
		subject_data["session"]=substitution["session"]
		subject_data["subject"]=substitution["subject"]
		if voxels:
			voxel_datas=[]
			for ix, i in enumerate(pattern_evaluation):
				voxel_data = deepcopy(subject_data)
				voxel_data["voxel"]=ix
				voxel_data["t"]=i
				voxel_data = pd.DataFrame(voxel_data, index=[None])
				voxel_datas.append(voxel_data)
			vdf = pd.concat(voxel_datas)
		else:
			vdf = False
		subject_data["t"]=pattern_score
		sdf = pd.DataFrame(subject_data, index=[None])
		return sdf, vdf

