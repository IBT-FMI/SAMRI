from nilearn.datasets.utils import _fetch_files

import subprocess
from os import path

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

	return dict([
			("template", template),
			("atlas", atlas),
			("labels", labels)])


def fetch_mouse_DSURQE(template_dir="~/.samri_files/templates/mouse/DSURQE/", verbose=1):
	"""Download and load waxholm atlas for Sprague Dawley rat


	Returns
	-------
	dict
		Dictionary containing template, atlas, labels, mask
		template - mri anatomy file; nifti file
		atlas - pixelvalues of regions are grouped together, with corresponding labels in labels.ccv; nifti file
		labels - labels annotating brain regions for pixelgroups in atlas; csv file
		mask - mri anatomy file, stripped off non-brain tissue; nifti file

	References
	----------
	.. [1] 'A.E. Dorr, et al, High resolution three-dimensional brain atlas using an average magnetic resonance image of 40 adult C57Bl/6J mice, NeuroImage, vol 42, Aug. 2008, pp. 60-69'
	.. [2] https://wiki.mouseimaging.ca/display/MICePub/Mouse+Brain+Atlases

	"""

	if(path.isfile(path.abspath(path.expanduser(template_dir + 'DSURQEc_40micron_labels.nii')))):
		return dict([
			        ("template", path.abspath(path.expanduser(template_dir)) + "/DSURQEc_40micron_average.nii"),
				("atlas", path.abspath(path.expanduser(template_dir)) + "/DSURQEc_40micron_labels.nii"),
				("mask", path.abspath(path.expanduser(template_dir)) + "/DSURQEc_40micron_mask.nii"),
				("labels", path.abspath(path.expanduser(template_dir)) + "/DSURQEc_40micron_itksnap_mapping.txt")])
	else:
		# Get template
		url_template = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron_nifti/DSURQE_40micron_average.nii'
		template = _fetch_files(path.abspath(path.expanduser(template_dir)), [('DSURQE_40micron_average.nii', url_template, {})],
				verbose=verbose)[0]

		# Get atlas
		url_atlas = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron_nifti/DSURQE_40micron_labels.nii'
		atlas = _fetch_files(path.abspath(path.expanduser(template_dir)), [('DSURQE_40micron_labels.nii', url_atlas, {})],
				verbose=verbose)[0]

		# Get mask

		url_mask = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron_nifti/DSURQE_40micron_mask.nii'
		mask = _fetch_files(path.abspath(path.expanduser(template_dir)), [('DSURQE_40micron_mask.nii', url_mask, {})],
				verbose=verbose)[0]

		# Get labels
		url_labels = 'http://repo.mouseimaging.ca/repo/DSURQE_40micron/DSURQE_40micron_itksnap_mapping.txt'
		labels = _fetch_files(path.abspath(path.expanduser(template_dir)), [('DSURQE_40micron_itksnap_mapping.txt', url_labels, {})],
				verbose=verbose)[0]

		# fix orientation issue in nii files - resulting in *c files, afterwards created downsampled atlas
		commands = ["fslorient -setsform -0.04 0 0 6.27 0 0.04 0 -10.6 0 0 0.04 -7.88 0 0 0 1 DSURQE_40micron_average.nii",
			"fslorient -copysform2qform DSURQE_40micron_average.nii",
			"mv DSURQE_40micron_average.nii DSURQEc_40micron_average.nii",
			"fslorient -setsform -0.04 0 0 6.27 0 0.04 0 -10.6 0 0 0.04 -7.88 0 0 0 1 DSURQE_40micron_mask.nii",
			"fslorient -copysform2qform DSURQE_40micron_mask.nii",
			"mv DSURQE_40micron_mask.nii DSURQEc_40micron_mask.nii",
			"fslorient -setsform -0.04 0 0 6.27 0 0.04 0 -10.6 0 0 0.04 -7.88 0 0 0 1 DSURQE_40micron_labels.nii",
			"fslorient -copysform2qform DSURQE_40micron_labels.nii",
			"mv DSURQE_40micron_labels.nii DSURQEc_40micron_labels.nii",
			"ResampleImage 3 DSURQEc_40micron_average.nii _DSURQEc_200micron_average.nii 0.2x0.2x0.2 size=1 spacing=0 4",
			"SmoothImage 3 _DSURQEc_200micron_average.nii 0.4 DSURQEc_200micron_average.nii",
			"rm _DSURQEc_200micron_average.nii",
			"ResampleImage 3 DSURQEc_40micron_labels.nii _DSURQEc_200micron_labels.nii 0.2x0.2x0.2 size=1 spacing=0 4",
			"SmoothImage 3 _DSURQEc_200micron_labels.nii 0.4 DSURQEc_200micron_labels.nii",
			"rm _DSURQEc_200micron_labels.nii",
			"ResampleImage 3 DSURQEc_40micron_mask.nii DSURQEc_200micron_mask.nii 0.2x0.2x0.2 size=1 spacing=0 1",
			"mv DSURQE_40micron_itksnap_mapping.txt DSURQEc_40micron_itksnap_mapping.txt"]


		print(path.isfile(path.abspath(path.expanduser(template_dir + 'DSURQE_40micron_labels.nii'))))

		for command in commands:
			p = subprocess.Popen(command.split(), cwd=path.abspath(path.expanduser(template_dir)), stdout=subprocess.PIPE)
			p.wait()

		return dict([
				("template", path.abspath(path.expanduser(template_dir)) + "DSURQEc_40micron_average.nii"),
				("atlas", path.abspath(path.expanduser(template_dir)) + "DSURQEc_40micron_labels.nii"),
				("mask", path.abspath(path.expanduser(template_dir)) + "DSURQEc_40micron_mask.nii"),
				("labels", labels)])
