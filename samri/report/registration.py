import hashlib
import multiprocessing as mp
import nibabel as nib
import pandas as pd
from os import path
from joblib import Parallel, delayed

from nipype.interfaces import ants, fsl

def measure_sim(image_path, reference,
	substitutions=False,
	mask='',
	metric='MI',
	radius_or_number_of_bins=8,
	sampling_strategy='None',
	sampling_percentage=0.3,
	):
	"""Return a similarity metric score for two 3d images

	Parameters
	----------

	image_path : str
		Path to moving image (moving and fixed image assignment is arbitrary for this function).
	reference : str
		Path to fixed image (moving and fixed image assignment is arbitrary for this function).
	substitutions : dict, optional
		Dictionary with keys which include 'subject', 'session', and 'acquisition', which will be applied to format the image_path string.
	mask : str
		Path to mask which selects a subregionfor which to compute the similarity.
	metric : {'CC', 'MI', 'Mattes', 'MeanSquares', 'Demons', 'GC'}
		Similarity metric, as accepted by `nipype.interfaces.ants.registration.MeasureImageSimilarity` (which wraps the ANTs command `MeasureImageSimilarity`).
	"""

	if substitutions:
		image_path = image_path.format(**substitutions)
	image_path = path.abspath(path.expanduser(image_path))

	#some BIDS identifier combinations may not exist:
	if not path.isfile(image_path):
		return {}

	file_data = {}
	file_data["path"] = image_path
	if substitutions:
		file_data["subject"] = substitutions["subject"]
		file_data["session"] = substitutions["session"]
		file_data["acquisition"] = substitutions["acquisition"]

	img = nib.load(image_path)
	if img.header['dim'][0] > 3:
		image_name = path.basename(file_data["path"])
		merged_image_name = "merged_"+image_name
		merged_image_path = path.join("/tmp",merged_image_name)
		if not path.isfile(merged_image_path):
			temporal_mean = fsl.MeanImage()
			temporal_mean.inputs.in_file = image_path
			temporal_mean.inputs.out_file = merged_image_path
			temporal_mean_res = temporal_mean.run()
			image_path = temporal_mean_res.outputs.out_file
		else:
			image_path = merged_image_path

	sim = ants.MeasureImageSimilarity()
	sim.inputs.dimension = 3
	sim.inputs.metric = metric
	sim.inputs.fixed_image = reference
	sim.inputs.moving_image = image_path
	sim.inputs.metric_weight = 1.0
	sim.inputs.radius_or_number_of_bins = radius_or_number_of_bins
	sim.inputs.sampling_strategy = sampling_strategy
	sim.inputs.sampling_percentage = sampling_percentage
	if mask:
		sim.inputs.fixed_image_mask = mask
	sim_res = sim.run()
	file_data["similarity"] = sim_res.outputs.similarity

	return file_data

def iter_measure_sim(file_template, reference, substitutions,
	metric="MI",
	radius_or_number_of_bins = 8,
	sampling_strategy = "None",
	sampling_percentage=0.3,
	save_as="",
	mask="",
	):
	"""Create a `pandas.DataFrame` (optionally savable as `.csv`), containing the similarity scores and BIDS identifier fields for images from a BIDS directory.
	"""

	reference = path.abspath(path.expanduser(reference))

	n_jobs = mp.cpu_count()-2
	similarity_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(measure_sim),
		[file_template]*len(substitutions),
		[reference]*len(substitutions),
		substitutions,
		[mask] * len(substitutions),
		[metric]*len(substitutions),
		[radius_or_number_of_bins]*len(substitutions),
		[sampling_strategy]*len(substitutions),
		[sampling_percentage]*len(substitutions),
		))

	df = pd.DataFrame.from_dict(similarity_data)
	df.dropna(axis=0, how='any', inplace=True) #some rows will be emtpy

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		if save_as.lower().endswith('.csv'):
			df.to_csv(save_as)
		else:
			raise ValueError("Please specify an output path ending in any one of "+",".join((".csv",))+".")
	return df
