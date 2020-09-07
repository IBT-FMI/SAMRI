import shutil
import getpass
from os import path
from samri.pipelines import glm
from samri.fetch.local import prepare_abi_connectivity_maps

def abi_connectivity_map(identifier,
	exclude_experiments=[],
	keep_work=False,
	mask='/usr/share/mouse-brain-atlases/dsurqec_200micron_mask.nii',
	prepare_root='/var/tmp/{user}/samri/abi_connectivity/',
	prepare_subdirs='sub-{experiment}/ses-1/anat/sub-{experiment}_ses-1_desc-cope.nii.gz',
	save_as_cope='',
	save_as_zstat='',
	save_as_tstat='',
	tmp_dir='/var/tmp/{user}/samri/abi_connectivity/l2',
	abi_data_root='/usr/share/ABI-connectivity-data/',
	invert_lr_experiments=[],
	):
	"""Create statistical summary maps (any subset of COPE, t-statistics, and z-statistics) for an ABI connectivity identifier.

	Parameters
	----------

	identifier : str
		Experiment set identifier which corresponds to the data set paths from the ABI-connectivity-data package.
	exclude_experiments : list of str, optional
		List of strings, each string 9 characters long, identifying which experiments should be excluded from the modelling.
	keep_work : bool, optional
		Whether to keep the work files (including the prepared ABI experiment data, the work directory, results directory, and crash directory of the model).
	mask : string, optional
		Path to a NIfTI file containing ones and zeroes and specifying the mask for the modelling workflow.
		It is important that this data is in the same template space as the ABI-connectivity-data package, which is the DSURQEC space [1]_ .
	prepare_root : string, optional
		Python-formattable string, under which the prepared (e.g. flipped) data from ABI experiments is to be saved.
		Generally this should be a temporal and new path, containing either "{user}" or located under the user's home directory, in order to avoid race conditions between users.
		It will be deleted without request for confirmation if this function is executed with `keep_work=False` (which is the default).
	prepare_subdirs : string, optional
		Python-formattable string, containing "{experiment}" according to which the prepared (e.g. flipped) data from ABI experiments is to be organized inside the `prepare_root` directory.
	save_as_cope : str, optional
		Path under which to save the COPE result of the modelling.
	save_as_tstat : str, optional
		Path under which to save the t-statistic result of the modelling.
	save_as_zstat : str, optional
		Path under which to save the z-statistic result of the modelling.
	tmp_dir : string, optional
		Temporary directory inside which to execute the modelling workflow.
		Generally this should be a temporal and new path, containing either "{user}" or located under the user's home directory, in order to avoid race conditions between users.
	abi_data_root : str, optional
		Root path for the ABI-connectivity-data package installation on the current machine.
	invert_lr_experiments : list of str, optional
		List of strings, each string 9 characters long, identifying which experiments need to be inverted with respect to the left-right orientation.

	Notes
	-----
		If neither of the `save_as_cope`, `save_as_tstat`, and `save_as_zstat` parameters are specified, all of the results are saved in the current work directory as `{identifier}_{statistic}.nii.gz`.

	References
	----------
	.. [1] H. I. Ioanas and M. Marks and M. F. Yanik and M. Rudin "An Optimized Registration Workflow and Standard Geometric Space for Small Animal Brain Imaging" https://doi.org/10.1101/619650
	"""

	# Prepend user name to SAMRI temp directories to prevent users from overwriting each other's work.
	current_user = getpass.getuser()
	prepare_root = prepare_root.format(user=current_user)
	tmp_dir = tmp_dir.format(user=current_user)

	reposit_path = path.join(prepare_root,'{identifier}',prepare_subdirs)
	prepare_abi_connectivity_maps(identifier,
		abi_data_root=abi_data_root,
		reposit_path=reposit_path,
		invert_lr_experiments=invert_lr_experiments,
		)
	prepare_root=prepare_root.format(identifier=identifier)
	glm.l2_common_effect(prepare_root,
		workflow_name=identifier,
		mask=mask,
		n_jobs_percentage=.33,
		out_base=tmp_dir,
		exclude={'subject':exclude_experiments},
		run_mode='fe',
		keep_work=keep_work,
		)
	if save_as_zstat:
		zstat_path = path.join(tmp_dir,identifier,'_zstat.nii.gz')
		shutil.copyfile(zstat_path, save_as_zstat)
	if save_as_tstat:
		tstat_path = path.join(tmp_dir,identifier,'_tstat.nii.gz')
		shutil.copyfile(tstat_path, save_as_tstat)
	if save_as_cope:
		cope_path = path.join(tmp_dir,identifier,'_cope.nii.gz')
		shutil.copyfile(cope_path, save_as_cope)
	if not any([save_as_zstat,save_as_tstat,save_as_cope]):
		zstat_path = path.join(tmp_dir,identifier,'_zstat.nii.gz')
		shutil.copyfile(zstat_path, '{identifier}_zstat.nii.gz')
		tstat_path = path.join(tmp_dir,identifier,'_tstat.nii.gz')
		shutil.copyfile(tstat_path, '{identifier}_tstat.nii.gz')
		cope_path = path.join(tmp_dir,identifier,'_cope.nii.gz')
		shutil.copyfile(cope_path, '{identifier}_cope.nii.gz')

	if not keep_work:
		results_dir = path.join(tmp_dir,identifier)
		shutil.rmtree(results_dir)
		shutil.rmtree(prepare_root)
