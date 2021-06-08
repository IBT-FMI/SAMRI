import nibabel as nib
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

	assignments : array
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

def assignment_from_paths(path_list,
	components=4,
	covariance='spherical',
	mask='/usr/share/mouse-brain-templates/dsurqec_200micron_mask.nii',
	save_as='',
	):
	"""Segment list of paths into Gaussian mixtures
	Parameters
	----------

	path_list : list
		List of strings which are paths to existing NIfTI files.
	components : int, optional
		Number of components to segment into.
	covariance : {'spherical', 'diag', 'tied', 'full'}, optional
		Covariance model to use for the gaussian mixture model.
	mask : str, optional
		Path to a mask in which to segment data.

	Returns
	-------

	assignment_img : nibabel.Nifti1Image
		NIfTI image of assignment.
	retest_accuracy : float
		Accuracy of single retest (percentage of assignments which overlap)
	"""
	mask = nib.load(mask)
	data = []
	affine = mask.affine
	header = mask.header
	mask_data = mask.get_data()
	shape = mask.shape
	mask_data = mask_data.flatten()
	mask_data = mask_data.astype(bool)
	all_data = []
	for i in path_list:
		img = nib.load(i)
		data = img.get_data()
		data = data.flatten()
		data = data[mask_data]
		all_data.append(data)
	all_data = np.array(all_data)
	assignments, classifier = assign_gaussian(all_data.T,components,covariance)
	assignments = sort_by_occurence(assignments)

	assignments_, classifier = assign_gaussian(all_data.T,4,'spherical')
	assignments_ = sort_by_occurence(assignments_)
	retest_accuracy = np.mean(assignments_.ravel() == assignments.ravel()) * 100

	assignments += 1
	new_data = mask_data.astype(int)
	new_data[mask_data] = assignments
	new_data[~mask_data] = 0
	new_data = new_data.reshape(shape)
	assignment_img = nib.Nifti1Image(new_data, affine, header)
	if save_as:
		nib.save(assignment_img, save_as)

	return assignment_img, retest_accuracy
