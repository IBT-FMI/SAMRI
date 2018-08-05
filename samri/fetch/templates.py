# -*- coding: utf-8 -*-


import subprocess
from os import path
import os



def fetch_rat_waxholm(template_dir="~/.samri_files/templates/rat/waxholm/", verbose=1):
	"""Download and load waxholm atlas for Sprague Dawley rat

	Returns
	-------
	dict
		Dictionary containing template, atlas, labels
		template - mri anatomy file; nifti file
		atlas - pixelvalues of regions are grouped together, with corresponding labels in labels.ccv; nifti file
		labels - labels annotating brain regions for pixelgroups in atlas; csv file


	References
	----------
	.. [1] 'Papp, Eszter A., et al. "Waxholm Space atlas of the Sprague Dawley rat brain." NeuroImage 97 (2014): 374-386.'
	.. [2] https://www.nitrc.org/projects/whs-sd-atlas

	"""
	from nilearn.datasets.utils import _fetch_files
	# Get template
	url_template = 'https://www.nitrc.org/frs/download.php/9423/WHS_SD_rat_T2star_v1.01.nii.gz'
	template = _fetch_files(path.abspath(path.expanduser(template_dir)), [('WHS_SD_rat_T2star_v1.01.nii.gz', url_template, {})],
			verbose=verbose)[0]

	# Get atlas
	url_atlas = 'https://www.nitrc.org/frs/download.php/9438/WHS_SD_rat_atlas_v2.nii.gz'
	atlas = _fetch_files(path.abspath(path.expanduser(template_dir)), [('WHS_SD_rat_atlas_v2.nii.gz', url_atlas, {})],
			verbose=verbose)[0]

	# Get labels
	url_labels = 'https://www.nitrc.org/frs/download.php/9439/WHS_SD_rat_atlas_v2.label'
	labels = _fetch_files(path.abspath(path.expanduser(template_dir)), [('WHS_SD_rat_atlas_v2.label', url_labels, {})],
			verbose=verbose)[0]

	# resample template
	commands = ["ResampleImage 3 WHS_SD_rat_T2star_v1.01.nii.gz _200micron_WHS_SD_rat_T2star_v1.01.nii.gz 0.2x0.2x0.2 size=1 spacing=0 4",
		"SmoothImage 3 _200micron_WHS_SD_rat_T2star_v1.01.nii.gz 0.4 200micron_WHS_SD_rat_T2star_v1.01.nii.gz",
		"rm _200micron_WHS_SD_rat_T2star_v1.01.nii.gz",
		"ResampleImage 3 WHS_SD_rat_atlas_v2.nii.gz _200micron_WHS_SD_rat_atlas_v2.nii.gz 0.2x0.2x0.2 size=1 spacing=0 4",
		"SmoothImage 3 _200micron_WHS_SD_rat_atlas_v2.nii.gz 0.4 200micron_WHS_SD_rat_atlas_v2.nii.gz",
		"rm _200micron_WHS_SD_rat_atlas_v2.nii.gz",]

	for command in commands:
		p = subprocess.Popen(command.split(), cwd=path.abspath(path.expanduser(template_dir)), stdout=subprocess.PIPE)
		p.wait()

	return dict([
			("template", path.abspath(path.expanduser(template_dir)) + "200micron_WHS_SD_rat_T2star_v1.01.nii.gz"),
			("atlas", path.abspath(path.expanduser(template_dir)) + "200micron_WHS_SD_rat_atlas_v2.nii.gz"),
			("labels", labels)])
