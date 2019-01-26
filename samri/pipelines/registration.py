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
