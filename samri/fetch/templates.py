from sklearn.datasets.base import Bunch
from nilearn.datasets.utils import _fetch_files

def fetch_rat_waxholm(data_dir="~/.samri_files/templates/rat/", verbose=1):
	"""Download and load waxholm atlas for Sprague Dawley rat

	Returns:
	data:	sklearn.datasets.base.Bunch
		Dictionary-like object, interest attributes are:


	References:
	'Papp, Eszter A., et al. "Waxholm Space atlas of the Sprague Dawley rat brain." NeuroImage 97 (2014): 374-386.'
	
	more information:
	https://www.nitrc.org/projects/whs-sd-atlas

	"""
	#TODO: check for files in standard directory (~/.samri_files) and just load if existing

	# Get template
	url_template = 'https://www.nitrc.org/frs/download.php/9423/WHS_SD_rat_T2star_v1.01.nii.gz'
	template = _fetch_files(data_dir, [('WHS_SD_rat_T2star_v1.01.nii.gz', url_template, {})],
			verbose=verbose)[0]

	# Get atlas
	url_atlas = 'https://www.nitrc.org/frs/download.php/9438/WHS_SD_rat_atlas_v2.nii.gz'
	atlas = _fetch_files(data_dir, [('WHS_SD_rat_atlas_v2.nii.gz', url_atlas, {})],
                        verbose=verbose)[0]

	# Get labels
	url_labels = 'https://www.nitrc.org/frs/download.php/9439/WHS_SD_rat_atlas_v2.label'
	labels = _fetch_files(data_dir, [('WHS_SD_rat_atlas_v2.label', url_labels, {})],
                        verbose=verbose)[0]
	

	return Bunch(
			template=template,
			atlas=atlas,
			labels=labels)
