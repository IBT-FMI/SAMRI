import hashlib
import multiprocessing as mp
import pandas as pd
from os import path
from joblib import Parallel, delayed

import nipype.interfaces.io as nio
from nipype.interfaces import ants, fsl

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
	file_data["ses"] = substitutions["session"]
	file_data["sub"] = substitutions["subject"]
	file_data["trial"] = substitutions["trial"]

	image_name = path.basename(file_data["path"])

	if "/func/" in path_template or "/dwi/" in path_template:
		temporal_mean = fsl.MeanImage()
		temporal_mean.inputs.in_file = image_path
		temporal_mean.inputs.out_file = path.join("/tmp",image_name)
		temporal_mean_res = temporal_mean.run()
		image_path = temporal_mean_res.outputs.out_file

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

# This should be reimplemented as a sort of autofind utility to be used in order to auto-generate a template string andsubstitutions list.
#	#ideally at some point, we would also support dwi
#	allowed_modalities = ("func","anat")
#	if modality not in allowed_modalities:
#		raise ValueError("modality parameter needs to be one of "+", ".join(allowed_modalities)+".")
#
#	bids_dir = path.abspath(path.expanduser(bids_dir))
#	reference = path.abspath(path.expanduser(reference))
#
#	if modality in ("func","dwi"):
#		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/'+modality+'/.*?_trial-(?P<trial>.+)\.nii.gz'
#	elif modality == "anat":
#		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/anat/.*?_(?P<trial>.+)\.nii.gz'
#
#	datafind = nio.DataFinder()
#        datafind.inputs.root_paths = bids_dir
#        datafind.inputs.match_regex = match_regex
#	datafind_res = datafind.run()

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

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		if save_as.lower().endswith('.csv'):
			df.to_csv(save_as)
		else:
			raise ValueError("Please specify an output path ending in any one of "+",".join((".csv",))+".")
	return df

if __name__ == '__main__':
	get_scores("~/ni_data/ofM.dr/preprocessing/composite", "~/ni_data/templates/DSURQEc_200micron_average.nii",
		#modality="anat",
		save_as="f_reg_quality.csv"
		)
