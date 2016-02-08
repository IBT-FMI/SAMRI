import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC, BET
from os import path, listdir
from preprocessing import bru2_preproc
import nipype.interfaces.io as nio

def quick_melodic(workflow_base, functional_scan_type, experiment_type=None, workflow_denominator="QuickMELODIC", omit_ID=[], inclusion_filter=""):
	workflow_base = path.expanduser(workflow_base)
	bru2_preproc_workflow = bru2_preproc_lite(workflow_base, functional_scan_type, experiment_type=experiment_type, omit_ID=omit_ID, inclusion_filter=inclusion_filter)

	melodic = pe.Node(interface=MELODIC(), name="melodic")
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

	pipeline.connect([(bru2_preproc_workflow, analysis_workflow, [('realigner.out_file','melodic.in_files')])
		])

	pipeline.write_graph(graph2use="flat")
	pipeline.run(plugin="MultiProc")

if __name__ == "__main__":
	quick_melodic(workflow_base="~/NIdata/ofM.erc/", functional_scan_type="7_EPI_CBV", experiment_type="<ERC_ofM>", inclusion_filter="")
	# experiment type, e.g. "<ofM>"
