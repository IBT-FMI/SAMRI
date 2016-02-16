import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC, BET
from os import path, listdir
from preprocessing import bru_preproc_lite
import nipype.interfaces.io as nio
import shutil

def quick_melodic(workflow_base, functional_scan_type, tr=1, conditions=[], workflow_denominator="QuickMELODIC", subjects_include=[], subjects_exclude=[], measurements_exclude=[]):
	workflow_base = path.expanduser(workflow_base)
	bru_preproc_workflow = bru_preproc_lite(workflow_base, functional_scan_type, tr=tr, conditions=conditions, subjects_include=subjects_include, subjects_exclude=subjects_exclude, measurements_exclude=measurements_exclude)

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
	quick_melodic(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", conditions=["ofM"], subjects_include=[], subjects_exclude=[], measurements_exclude=["20151026_135856_4006_1_1", "20151027_121613_4013_1_1"])
