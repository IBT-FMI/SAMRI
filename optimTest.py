# testing of optimization of hyperparams for registration


import numpy as np
from scipy import optimize

from samri.pipelines.reposit import bru2bids
from os import path

from samri.pipelines.preprocess import bruker
from hyperopt import fmin, tpe

from bids.grabbids import BIDSLayout
from bids.grabbids import BIDSValidator

from hyperopt import fmin, tpe, hp

from samri.pipelines.registration import measure_sim_bids

def objective(args):
    #parameters = {"smoothing_sigmas": np.asarray(args
    _pa = {'smoothing_sigmas': [args['sigma1'], args['sigma2'], args['sigma3']]}
    print(_pa['smoothing_sigmas'])
    bruker(bids_base,
	"mouse",
	functional_match={'task':['JogB','CoglB','CogB2m'],},
	structural_match={'acquisition':['TurboRARE', 'TurboRARElowcov']},
	subjects = ['5667'],
	sessions = ['ofMr1'],
	actual_size=True,
	functional_registration_method="composite",
	params = {'smoothing_sigmas': [float(args['sigma1']), float(args['sigma2']), float(args['sigma3'])]},
	)
       # somehow grab results

    layout = BIDSLayout(results)
    df = layout.as_data_frame()

    df = df[df['modality'] == 'anat']

    similarity = 0
    for res in df:
    	path = res['path']
	_similarity = measure_sim_bids(path, template)
	similarity += _similarity

    return -similarity

# parameterspace
# only one for proof of principle now
# TODO: extend

space = {
	'sigma1': hp.randint('sigma1',5),
	'sigma2': hp.randint('sigma2',5),
	'sigma3': hp.randint('sigma3',5),
	}

global bids_base
global template
global results_dir

bids_base = '/media/nexus/storage/ni_data/ofmTest/'
results = bids_base + 'preprocessing/generic/'
template = '/home/nexus/.samri_files/templates/mouse/DSURQE/DSURQEc_200micron_average.nii'
#bids_base = '~/ni_data/oFM'

# initialize parameters

# do the preprocessing with params

# measure similarity
best = fmin(objective, space, algo=tpe.suggest, max_evals=10)

# result for optimizer
