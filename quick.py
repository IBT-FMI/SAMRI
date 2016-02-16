import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC, BET
from os import path, listdir
from preprocessing import bru_preproc_lite
import nipype.interfaces.io as nio
import shutil

# set of files by which to identify a  Bruker measurement directory
bruker_files = {"AdjStatePerStudy", "ResultState", "subject"}

def quick_melodic(measurements_base, functional_scan_type, workflow_base=False, tr=1, conditions=[], workflow_denominator="QuickMELODIC", include_subjects=[], exclude_subjects=[], exclude_measurements=[], include_measurements=[], debug_mode=False):

	#make measurements_base absolute (this has to be here to allow the check below)
	measurements_base = path.expanduser(measurements_base)

	#check if a bruker measurement directory was specified as the measurements_base. If so, set the root directories one level up and add the basename to include_measurements
	if bruker_files.issubset(listdir(measurements_base)):
		include_measurements = [path.basename(measurements_base)]
		measurements_base += "/.."

	#make workflow_base absolute (this has to be here to catch the measurements_base change that might have occured earlier)
	if workflow_base:
		workflow_base = path.expanduser(workflow_base)
	else:
		workflow_base = measurements_base

	bru_preproc_workflow = bru_preproc_lite(measurements_base, functional_scan_type, tr=tr, conditions=conditions, include_subjects=include_subjects, exclude_subjects=exclude_subjects, exclude_measurements=exclude_measurements, include_measurements=include_measurements)

	melodic = pe.Node(interface=MELODIC(), name="melodic")
	melodic.inputs.tr_sec = tr
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	datasink = pe.Node(nio.DataSink(), name='sinker')
	datasink.inputs.base_directory = workflow_base+"/"+workflow_denominator+"_results"

	#SET UP ANALYSIS WORKFLOW:
	analysis_workflow = pe.Workflow(name="ICA")

	analysis_workflow.connect([
		(melodic, datasink, [('report_dir', 'MELODIC_reports')])
		])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([
		(bru_preproc_workflow, analysis_workflow, [('realigner.out_file','melodic.in_files')])
		])

	# pipeline.write_graph(graph2use="flat")
	pipeline.run(plugin="MultiProc")

	#delete all fles but final results
	if not debug_mode:
		shutil.rmtree(workflow_base+"/"+workflow_denominator+"_work")

if __name__ == "__main__":
	quick_melodic("~/NIdata/ofM.dr/20151027_141609_4011_1_1", "7_EPI_CBV", conditions=[], include_subjects=[], exclude_subjects=[], exclude_measurements=["20151026_135856_4006_1_1", "20151027_121613_4013_1_1"], debug_mode=True)
