def dr_seed_fc():
	import numpy as np
	from os import path
	from labbookdb.report.tracking import treatment_group, append_external_identifiers
	from samri.plotting.overview import multiplot_matrix, multipage_plot
	from samri.utilities import bids_substitution_iterator
	from samri.analysis import fc

	db_path = '~/syncdata/meta.db'
	groups = treatment_group(db_path, ['cFluDW','cFluDW_'], 'cage')
	groups = append_external_identifiers(db_path, groups, ['Genotype_code'])
	all_subjects = groups['ETH/AIC'].unique()

	substitutions = bids_substitution_iterator(
		["ofM","ofMaF","ofMcF1","ofMcF2","ofMpF"],
		all_subjects,
		["CogB",],
		"~/ni_data/ofM.dr/",
		"composite",
		acquisitions=["EPI",],
		check_file_format='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz')

	fc_results = fc.seed_based(substitutions, "~/ni_data/templates/roi/DSURQEc_dr.nii.gz", "/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		ts_file_template='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz',
		save_results="~/ni_data/ofM.dr/fc/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz",
		)
def drp_seed_fc():
	import numpy as np
	from os import path
	#from labbookdb.report.tracking import treatment_group, append_external_identifiers
	from samri.plotting.overview import multiplot_matrix, multipage_plot
	from samri.utilities import bids_substitution_iterator
	from samri.analysis import fc
	from samri.utilities import N_PROCS

	N_PROCS=max(N_PROCS-8, 2)

	from bids.grabbids import BIDSLayout
	from bids.grabbids import BIDSValidator
	import os

	base = '~/ni_data/ofM.dr/bids/preprocessing/generic/'
	base = os.path.abspath(os.path.expanduser(base))
	validate = BIDSValidator()
	for x in os.walk(base):
		print(x[0])
		print(validate.is_bids(x[0]))
	layout = BIDSLayout(base)
	df = layout.as_data_frame()
	df = df[df.type.isin(['cbv'])]
	print(df)

	#substitutions = bids_substitution_iterator(
	#	list(df['session'].unique()),
	#	all_subjects,
	#	["CogB",],
	#	"~/ni_data/ofM.dr/",
	#	"composite",
	#	acquisitions=["EPI",],
	#	check_file_format='~/ni_data/ofM.dr/preprocessing/{preprocessing_dir}/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz')

	#substitutions = df.T.to_dict().values()[:2]
	substitutions = df.T.to_dict().values()
	print(substitutions)

	fc_results = fc.seed_based(substitutions, "~/ni_data/templates/roi/DSURQEc_drp.nii.gz", "/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii",
		ts_file_template='~/ni_data/ofM.dr/bids/preprocessing/generic/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv.nii.gz',
		save_results="~/ni_data/ofM.dr/bids/fc/DSURQEc_drp/sub-{subject}/ses-{session}/func/sub-{subject}_ses-{session}_acq-{acquisition}_task-{task}_cbv_zstat.nii.gz",
		n_procs=N_PROCS,
		cachedir='/mnt/data/joblib')

def segmentation():
	import matplotlib.pyplot as plt
	import matplotlib as mpl
	import numpy as np

	from sklearn import datasets
	from sklearn.cross_validation import StratifiedKFold
	from samri.analysis.segmentation import assign_gaussian

	def make_ellipses(gmm, ax,
		colors='rgb',
		):
		for n, color in enumerate(colors):
			#print(gmm._get_covars()[n])
			#print(gmm._get_covars()[n][:2, :2])
			v, w = np.linalg.eigh(gmm._get_covars()[n][:2, :2])
			u = w[0] / np.linalg.norm(w[0])
			angle = np.arctan2(u[1], u[0])
			angle = 180 * angle / np.pi  # convert to degrees
			v *= 9
			ell = mpl.patches.Ellipse(gmm.means_[n, :2], v[0], v[1],
									  180 + angle, color=color)
			ell.set_clip_box(ax.bbox)
			ell.set_alpha(0.5)
			ax.add_artist(ell)

	iris = datasets.load_iris()
	iris_data = iris.data[:,:3]

	skf = StratifiedKFold(iris.target, n_folds=5, shuffle=False)
	train_index, test_index = next(iter(skf))

	X_train = iris_data[train_index]
	X_test = iris_data[test_index]

	covariances = ['spherical', 'diag', 'tied', 'full']
	n_covariances = len(covariances)

	n_components = 4
	plt.figure(figsize=(3 * n_covariances / 2, 6))

	for index, covariance in enumerate(covariances):
		h = plt.subplot(2, n_covariances / 2, index + 1)

		assignments, classifier = assign_gaussian(X_train, n_components, covariance)

		weights = classifier.weights_
		mysort = np.argsort(weights)
		print(weights)
		weights = weights[mysort]
		print(weights)
		labels = np.array(list(set(assignments)))
		labels_ = labels[mysort]
		convert = dict(zip(labels, labels_))
		u,inv = np.unique(assignments,return_inverse = True)
		assignments = np.array([convert[x] for x in u])[inv].reshape(assignments.shape)

		for n, color in enumerate('rgby'):
			data = X_train[assignments == n]
			plt.plot(data[:, 0], data[:, 1], 'x', color=color,
						label=list(set(assignments))[n])
		assignments_, classifier_ = assign_gaussian(X_train, n_components, covariance)

		weights = classifier_.weights_
		mysort = np.argsort(weights)
		weights = weights[mysort]
		labels = np.array(list(set(assignments_)))
		labels_ = labels[mysort]
		convert = dict(zip(labels, labels_))
		u,inv = np.unique(assignments_,return_inverse = True)
		assignments_ = np.array([convert[x] for x in u])[inv].reshape(assignments_.shape)

		for n, color in enumerate('rgby'):
			data = X_train[assignments_ == n]
			plt.plot(data[:, 0], data[:, 1], 'o', color=color)
		test_accuracy = np.mean(assignments_.ravel() == assignments.ravel()) * 100
		plt.text(0.05, 0.9, 'Test accuracy: %.1f' % test_accuracy,
				 transform=h.transAxes)

		make_ellipses(classifier, h, colors='rgby')
		plt.xticks(())
		plt.yticks(())
		plt.title(covariance)

	plt.legend()
	plt.savefig('segmentation.pdf')
