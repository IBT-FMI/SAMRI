import hashlib
import multiprocessing as mp
import pandas as pd
from os import path
from joblib import Parallel, delayed

from nipype.interfaces import ants, fsl

def measure_sim_bids(template, moving_image,
	metric="MI",
	radius_or_number_of_bins = 8,
	sampling_strategy = "None",
	sampling_percentage=0.3,
	mask="",
	):
	"""Return a similarity metric score for two 3d images"""

	image_path = path.abspath(path.expanduser(moving_image))
	reference = path.abspath(path.expanduser(template))

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
	#sim.inputs.moving_image_mask = 'mask.nii.gz'
	sim_res = sim.run()

	return sim_res.outputs.similarity



def measure_sim(path_template, substitutions, reference,
	metric="MI",
	radius_or_number_of_bins = 8,
	sampling_strategy = "None",
	sampling_percentage=0.3,
	mask="",
	):
	"""Return a similarity metric score for two 3d images"""

	image_path = path_template.format(**substitutions)
	image_path = path.abspath(path.expanduser(image_path))

	#some BIDS identifier combinations may not exist:
	if not path.isfile(image_path):
		return {}

	file_data = {}
	file_data["path"] = image_path
	file_data["session"] = substitutions["session"]
	file_data["subject"] = substitutions["subject"]
	file_data["acquisition"] = substitutions["acquisition"]

	if "/func/" in path_template or "/dwi/" in path_template:
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
	#sim.inputs.moving_image_mask = 'mask.nii.gz'
	sim_res = sim.run()
	file_data["similarity"] = sim_res.outputs.similarity

	return file_data

def get_scores(file_template, substitutions, reference,
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
		substitutions,
		[reference]*len(substitutions),
		[metric]*len(substitutions),
		[radius_or_number_of_bins]*len(substitutions),
		[sampling_strategy]*len(substitutions),
		[sampling_percentage]*len(substitutions),
		[mask]*len(substitutions),
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
