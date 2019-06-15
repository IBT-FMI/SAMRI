import numpy as np
from sklearn.mixture import GMM

def assign_gaussian(data, n_components, covariance_type,
	init_params='wc',
	n_iter=50,
	):
	classifier = GMM(
		n_components=n_components,
		covariance_type=covariance_type,
		init_params=init_params,
		n_iter=n_iter,
		)
	classifier.fit(data)
	assignment = classifier.predict(data)
	return assignment, classifier

