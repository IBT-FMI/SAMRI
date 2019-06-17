import numpy as np
from sklearn.mixture import GaussianMixture

def assign_gaussian(data, n_components, covariance_type,
	init_params='kmeans',
	n_init=50,
	):
	classifier = GaussianMixture(
		n_components=n_components,
		covariance_type=covariance_type,
		init_params=init_params,
		n_init=n_init,
		)
	classifier.fit(data)
	assignment = classifier.predict(data)
	return assignment, classifier

def sort_by_occurence(assignments):
	"""Change unique values in array to ordinal integers based on the number of occurences.
	Parameters
	----------

	assignments: array
		1-D array of values.
	"""

	labels, counts = np.unique(assignments, return_counts=True)
	mysort = np.argsort(counts)[::-1]
	counts = counts[mysort]
	labels_ = labels[mysort]
	new_labels = [i for i in range(len(labels))]
	convert = dict(zip(labels_, new_labels))
	keys,inv = np.unique(assignments,return_inverse = True)
	assignments = np.array([convert[x] for x in keys])[inv].reshape(assignments.shape)
	return assignments
