# testing of optimization of hyperparams for registration


import numpy as np
from scipy import optimize

from samri.pipelines.reposit import bru2bids
from os import path
import shutil

from samri.pipelines.preprocess import bruker
from hyperopt import fmin, tpe

from bids.grabbids import BIDSLayout
from bids.grabbids import BIDSValidator

from hyperopt import fmin, tpe, hp

from samri.pipelines.registration import measure_sim_bids

PHASES = {
        "f_rigid":{
                "transforms":"Rigid",
                "transform_parameters":(0.1,),
                "number_of_iterations":[40,20,10],
                "metric":"GC",
                "metric_weight":1,
                "radius_or_number_of_bins":32,
                "sampling_strategy":"Regular",
                "sampling_percentage":0.2,
                "convergence_threshold":1.e-2,
                "convergence_window_size":8,
                "smoothing_sigmas":[2,1,0],
                "sigma_units":"vox",
                "shrink_factors":[4,2,1],
                "use_estimate_learning_rate_once":False,
                "use_histogram_matching":False,
                },
        "s_rigid":{
                "transforms":"Rigid",
                "transform_parameters":(0.1,),
                "number_of_iterations":[6000,3000],
                "metric":"GC",
                "metric_weight":1,
                "radius_or_number_of_bins":64,
                "sampling_strategy":"Regular",
                "sampling_percentage":0.2,
                "convergence_threshold":1.e-16,
                "convergence_window_size":30,
                "smoothing_sigmas":[1,0],
                "sigma_units":"vox",
                "shrink_factors":[2,1],
                "use_estimate_learning_rate_once":False,
                "use_histogram_matching":True,
                },
        "affine":{
                "transforms":"Affine",
                "transform_parameters":(0.1,),
                "number_of_iterations":[500,250],
                "metric":"MI",
                "metric_weight":1,
                "radius_or_number_of_bins":8,
                "sampling_strategy":None,
                "sampling_percentage":0.3,
                "convergence_threshold":1.e-32,
                "convergence_window_size":30,
                "smoothing_sigmas":[1,0],
                "sigma_units":"vox",
                "shrink_factors":[1,1],
                "use_estimate_learning_rate_once":False,
                "use_histogram_matching":True,
                },
        "syn":{
                "transforms":"SyN",
                "transform_parameters":(0.1, 2.0, 0.2),
                "number_of_iterations":[500,250],
                "metric":"MI",
                "metric_weight":1,
                "radius_or_number_of_bins":16,
                "sampling_strategy":None,
                "sampling_percentage":0.3,
                "convergence_threshold":1.e-32,
                "convergence_window_size":30,
                "smoothing_sigmas":[1,0],
                "sigma_units":"vox",
                "shrink_factors":[1,1],
                "use_estimate_learning_rate_once":False,
                "use_histogram_matching":True,
                },
        }


def objective(args):
    #parameters = {"smoothing_sigmas": np.asarray(args
    _pa = {'smoothing_sigmas': [args['sigma1'], args['sigma2']]}
    print(_pa['smoothing_sigmas'])
    bruker(bids_base,
	"mouse",
	functional_match={'task':['JogB','CoglB','CogB2m'],},
	structural_match={'acquisition':['TurboRARE', 'TurboRARElowcov']},
	subjects = ['5667'],
	sessions = ['ofMr1'],
	actual_size=True,
	functional_registration_method="composite",
	params = {'smoothing_sigmas': [float(args['sigma1']), float(args['sigma2'])]},
	bandpass = False,
	)
       # somehow grab results

    layout = BIDSLayout(results)
    df = layout.as_data_frame()

    df = df[df['modality'] == 'anat']
    print('--df--')
    print(df)

    similarity = 0
    for res in df['path']:
	print('--res--')
	print(res)
	path = res
	_similarity = measure_sim_bids(path, template)
	similarity += float(_similarity)

    # remove preprocessing folder for next round
    shutil.rmtree(preprocess_path)

    return -similarity

# parameterspace
# only one for proof of principle now
# TODO: extend

space = {
	'sigma1': 1,
	'sigma2': 0,
	}

global bids_base
global template
global results_dir
global preprocess_path


bids_base = '/media/nexus/storage/ni_data/ofmTest/'
results = bids_base + 'preprocessing/generic/'
preprocess_path = bids_base + 'preprocessing/'
template = '/home/nexus/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii'
#bids_base = '~/ni_data/oFM'

# initialize parameters

# do the preprocessing with params
if __name__ == "__main__":
    best = fmin(objective, space, algo=tpe.suggest, max_evals=2)
    # measure similarity

    print(best[0])

    # result for optimizer
