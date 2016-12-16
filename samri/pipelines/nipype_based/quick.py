#!/usr/bin/python

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2
from nipype.interfaces.fsl import MELODIC, BET
from os import path, listdir, remove, getcwd
from preprocessing import bruker_lite
import nipype.interfaces.io as nio
import shutil
import re
import argh

# set of files by which to identify a  Bruker measurement directory
bruker_files = {"AdjStatePerStudy", "ResultState", "subject"}

@argh.arg('-f', '--functional_scan_types', nargs='+', type=str)
@argh.arg('--structural_scan_types', nargs='+', type=str)
@argh.arg('--sessions', nargs='+', type=str)
@argh.arg('--subjects', nargs='+', type=str)
@argh.arg('--exclude-subjects', nargs='+', type=str)
@argh.arg('--measurements', nargs='+', type=str)
@argh.arg('--exclude_measurements', nargs='+', type=str)
def diagnostic(measurements_base,
	structural_scan_types=[],
	functional_scan_types=[],
	workflow_base=False,
	tr=1,
	sessions=[],
	workflow_denominator="DIAGNOSTIC",
	subjects=[],
	exclude_subjects=[],
	measurements=[],
	exclude_measurements=[],
	keep_work=False,
	actual_size=False,
	realign=False,
	loud=False,
	dimensions=8,
	n_procs=8,
	):

	"""Runs a diagnostic analysis, returning MELODIC (ICA) results and structural scans.

	Mandatory Arguments:
	measurements_base -- path in which to look for data to be processed

	Keyword Arguments:
	structural_scan_types -- structural scan identifiers for which to perform the diafnostic (default: all structural scan type values from the scan_type_classification.csv file)
	functional_scan_types -- functional scan identifiers for which to perform the diafnostic (default: all structural scan type values from the scan_type_classification.csv file)
	workflow_base -- path in which to place the workflow and results
	tr -- repetition time (default: 1)
	sessions -- session (e.g. operation, substance administration) identifiers for which to perform the diafnostic (default: all sessions are selected)
	workflow_denominator -- name of main workflow directory (default "DIAGNOSTIC")
	subjects -- subject identifiers for which to perform the diagnostic (default: all subjects are selected)
	exclude_subjects -- subject identifiers for which not to perform diagnostic (default None)
	measurements -- measurement directory names on which to selectively perform diagnostic (default: all measurement directories in measurements_base are seected)
	exclude_measurements -- measurement directory for which not to perform diagnostic (default None)
	debug -- do not delete work directory, which contains all except the final results (default False)
	loud -- reports missing scan errors, and does not delete their corresponding crash files (default False)
	dimensions -- number of dimensions to extract from MELODIC (default 8)
	"""

	#make measurements_base absolute (this has to be here to allow the check below)
	measurements_base = path.abspath(path.expanduser(measurements_base))

	#check if a bruker measurement directory was specified as the measurements_base. If so, set the root directories one level up and add the basename to `measurements`
	if bruker_files.issubset(listdir(measurements_base)):
		measurements = [path.basename(measurements_base)]
		measurements_base += "/.."
		measurements_base = path.abspath(measurements_base)

	#make workflow_base absolute (this has to be here to catch the measurements_base change that might have occured earlier)
	if workflow_base:
		workflow_base = path.expanduser(workflow_base)
	else:
		workflow_base = measurements_base

	bruker_workflow = bruker_lite(measurements_base, functional_scan_types=functional_scan_types, structural_scan_types=structural_scan_types, tr=tr, sessions=sessions, subjects=subjects, exclude_subjects=exclude_subjects, exclude_measurements=exclude_measurements, measurements=measurements, actual_size=actual_size)

	melodic = pe.Node(interface=MELODIC(), name="melodic")
	melodic.inputs.tr_sec = tr
	melodic.inputs.report = True
	melodic.inputs.dim = dimensions

	datasink = pe.Node(nio.DataSink(), name='datasink')
	datasink.inputs.base_directory = path.join(workflow_base,workflow_denominator)

	#SET UP ANALYSIS WORKFLOW:
	analysis_workflow = pe.Workflow(name="ICA")

	analysis_workflow.connect([
		(melodic, datasink, [('report_dir', 'MELODIC_reports')])
		])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline_connections = [
		(bruker_workflow, datasink, [('infosource.session','container')]),
		(bruker_workflow, datasink, [('s_bru2nii.nii_file','structural')]),
		]

	if realign:
		pipeline_connections.extend([
			(bruker_workflow, analysis_workflow, [('realigner.out_file','melodic.in_files')])
			])
	else:
		pipeline_connections.extend([
		(bruker_workflow, analysis_workflow, [('f_bru2nii.nii_file','melodic.in_files')])
		])

	pipeline.connect(pipeline_connections)
	pipeline.write_graph(graph2use="flat")

	if not loud:
		try:
			pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : n_procs})
		except RuntimeError:
			print("WARNING: Some expected scans have not been found (or another RuntimeError has occured).")
		for f in listdir(getcwd()):
			if re.search("crash.*?get_s_scan|get_f_scan.*", f):
				remove(path.join(getcwd(), f))
	else:
		pipeline.run(plugin="MultiProc",  plugin_args={'n_procs' : n_procs})

	#delete all fles but final results
	if not keep_work:
		shutil.rmtree(path.join(workflow_base,workflow_denominator+"_work"))
