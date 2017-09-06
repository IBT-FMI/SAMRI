import hashlib
import multiprocessing as mp
import pandas as pd
from os import path
from joblib import Parallel, delayed

import nipype.interfaces.io as nio
from nipype.interfaces import ants, fsl

def measure_sim(image, ses, sub, trial, modality, reference):
	file_data = {}
	file_data["path"] = image
	file_data["ses"] = ses
	file_data["sub"] = sub
	file_data["trial"] = trial

	if modality in ("func", "dwi"):
		temporal_mean = fsl.MeanImage()
		temporal_mean.inputs.in_file = image
		temporal_mean.inputs.out_file = "/tmp/"+hashlib.md5(image).hexdigest()[:8]+".nii.gz"
		temporal_mean_res = temporal_mean.run()
		image = temporal_mean_res.outputs.out_file

	sim = ants.MeasureImageSimilarity()
	sim.inputs.dimension = 3
	sim.inputs.metric = 'MI'
	sim.inputs.fixed_image = reference
	sim.inputs.moving_image = image
	sim.inputs.metric_weight = 1.0
	sim.inputs.radius_or_number_of_bins = 8
	sim.inputs.sampling_strategy = 'None'
	sim.inputs.sampling_percentage = 0.3
	#sim.inputs.fixed_image_mask = 'mask.nii'
	#sim.inputs.moving_image_mask = 'mask.nii.gz'
	sim_res = sim.run()
	file_data["similarity"] = sim_res.outputs.similarity

	return file_data

def get_scores(bids_dir, reference,
	modality="func",
	save_as=False,
	):

	#ideally at some point, we would also support dwi
	allowed_modalities = ("func","anat")
	if modality not in allowed_modalities:
		raise ValueError("modality parameter needs to be one of "+", ".join(allowed_modalities)+".")

	bids_dir = path.abspath(path.expanduser(bids_dir))
	reference = path.abspath(path.expanduser(reference))

	if modality in ("func","dwi"):
		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/'+modality+'/.*?_trial-(?P<trial>.+)\.nii.gz'
	elif modality == "anat":
		match_regex = '.+/sub-(?P<sub>.+)/ses-(?P<ses>.+)/anat/.*?_(?P<trial>.+)\.nii.gz'

	datafind = nio.DataFinder()
        datafind.inputs.root_paths = bids_dir
        datafind.inputs.match_regex = match_regex
	datafind_res = datafind.run()
	files_data = []

	n_jobs = mp.cpu_count()-2
        similarity_data = Parallel(n_jobs=n_jobs, verbose=0, backend="threading")(map(delayed(measure_sim),
                datafind_res.outputs.out_paths,
                datafind_res.outputs.ses,
                datafind_res.outputs.sub,
                datafind_res.outputs.trial,
                [modality]*len(datafind_res.outputs.out_paths),
                [reference]*len(datafind_res.outputs.out_paths),
                ))

	df = pd.DataFrame.from_dict(similarity_data)

	if save_as:
		save_as = path.abspath(path.expanduser(save_as))
		if save_as.lower().endswith('.csv'):
			df.to_csv(save_as)
		else:
			raise ValueError("Please specify an output path ending in any one of "+",".join((".csv",))+".")

if __name__ == '__main__':
	get_scores("~/composite", "~/ni_data/templates/DSURQEc_200micron_average.nii",
		#modality="anat",
		save_as="f_reg_quality.csv"
		)
