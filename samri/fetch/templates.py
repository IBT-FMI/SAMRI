from sklearn.datasets.base import Bunch
from nilearn.datasets.utils import _fetch_files

from os import path

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
        # Get template
	url_template = 'https://www.nitrc.org/frs/download.php/9423/WHS_SD_rat_T2star_v1.01.nii.gz'
	template = _fetch_files(path.abspath(path.expanduser(data_dir)), [('WHS_SD_rat_T2star_v1.01.nii.gz', url_template, {})],
			verbose=verbose)[0]

	# Get atlas
	url_atlas = 'https://www.nitrc.org/frs/download.php/9438/WHS_SD_rat_atlas_v2.nii.gz'
	atlas = _fetch_files(path.abspath(path.expanduser(data_dir)), [('WHS_SD_rat_atlas_v2.nii.gz', url_atlas, {})],
			verbose=verbose)[0]

	# Get labels
	url_labels = 'https://www.nitrc.org/frs/download.php/9439/WHS_SD_rat_atlas_v2.label'
	labels = _fetch_files(path.abspath(path.expanduser(data_dir)), [('WHS_SD_rat_atlas_v2.label', url_labels, {})],
			verbose=verbose)[0]
        
	return Bunch(
			template=template,
			atlas=atlas,
			labels=labels)


def fetch_mouse_DSURQE(data_dir="~/.samri_files/templates/mouse/DSURQE", verbose=1):                                   
        """Download and load waxholm atlas for Sprague Dawley rat

        Returns:
        data:   sklearn.datasets.base.Bunch
                Dictionary-like object, interest attributes are:

        References:
        'A.E. Dorr, et al, High resolution three-dimensional brain atlas using an average magnetic resonance image of 40 adult C57Bl/6J mice, NeuroImage, vol 42, Aug. 2008, pp. 60-69'

        more information:
        https://wiki.mouseimaging.ca/display/MICePub/Mouse+Brain+Atlases
	
	"""

	# Get template
	url_template = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron_nifti/DSURQE_40micron_average.nii'
	template = _fetch_files(path.abspath(path.expanduser(data_dir)), [('DSURQE_40micron_average.nii', url_template, {})],
			verbose=verbose)[0]

	# Get atlas
	url_atlas = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron_nifti/DSURQE_40micron_mask.nii'
	atlas = _fetch_files(path.abspath(path.expanduser(data_dir)), [('DSURQE_40micron_mask.nii', url_atlas, {})],
			verbose=verbose)[0]

	# Get labels
	url_labels = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron_nifti/DSURQE_40micron_labels.nii'
	labels = _fetch_files(path.abspath(path.expanduser(data_dir)), [('DSURQE_40micron_labels.nii', url_labels, {})],
			verbose=verbose)[0]

        return Bunch(                                      
                        template=template,                 
                        atlas=atlas,                       
                        labels=labels) 
