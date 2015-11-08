import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC
from os import path, listdir
from preprocessing import bg_preproc
import nipype.interfaces.io as nio

def quick_melodic(workflow_base, functional_scan_type, workflow_denominator="QuickMELODIC", omit_ID=[]):
	workflow_base = path.expanduser(workflow_base)
	bru2_preproc_workflow = bru2_preproc(workflow_base, functional_scan_type, omit_ID=omit_ID, resize=False)

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
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

	pipeline.connect([(bru2_preproc_workflow, analysis_workflow, [('bru2_functional.nii_file','MELODIC.in_files')])
		])

	pipeline.write_graph(graph2use="orig")
	pipeline.run(plugin="MultiProc")

if __name__ == "__main__":
	quick_melodic(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", omit_ID=["20151026_135856_4006_1_1"])
