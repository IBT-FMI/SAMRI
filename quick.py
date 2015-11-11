import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC, BET
from os import path, listdir
from preprocessing import bru2_preproc
import nipype.interfaces.io as nio

def quick_melodic(workflow_base, functional_scan_type, experiment_type=None, workflow_denominator="QuickMELODIC", omit_ID=[]):
	workflow_base = path.expanduser(workflow_base)
	bru2_preproc_workflow = bru2_preproc(workflow_base, functional_scan_type, experiment_type=None, omit_ID=omit_ID)

	skullstripping = pe.Node(interface=BET(), name="fslBET")
	skullstripping.inputs.functional = True

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	datasink = pe.Node(nio.DataSink(), name='sinker')
	datasink.inputs.base_directory = workflow_base+"/"+workflow_denominator+"_results"

	#SET UP ANALYSIS WORKFLOW:
	analysis_workflow = pe.Workflow(name="ICA")

	analysis_workflow.connect([
		(skullstripping, melodic, [('out_file', 'in_files')]),
		(melodic, datasink, [('report_dir', 'MELODIC_reports')])
		])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([(bru2_preproc_workflow, analysis_workflow, [('bru2_functional.nii_file','fslBET.in_file')])
		])

	pipeline.write_graph(graph2use="orig")
	pipeline.run(plugin="MultiProc")

if __name__ == "__main__":
	quick_melodic(workflow_base="~/NIdata/ofM.dr/", functional_scan_type="7_EPI_CBV", experiment_type="<ofM>",omit_ID=["20151026_135856_4006_1_1"])
