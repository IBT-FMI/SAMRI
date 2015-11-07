import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC
from os import path, listdir
from preprocessing import bg_preproc
import nipype.interfaces.io as nio

def quick_melodic(workflow_base=".", workflow_denominator="QuickMELODIC", scan_type="7_EPI_CBV"):

	print workflow_base
	bg_preproc_workflow = bg_preproc(workflow_base=workflow_base, workflow_denominator=workflow_denominator, scan_type=scan_type)

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	datasink = pe.Node(nio.DataSink(), name='sinker')
	datasink.inputs.base_directory = workflow_base+"/"+workflow_denominator+"_results"

	#SET UP ANALYSIS WORKFLOW:
	analysis_workflow = pe.Workflow(name="ICA")
	analysis_workflow.base_dir = workflow_base+"/"+workflow_denominator

	analysis_workflow.connect([
		(melodic, datasink, [('report_dir', 'reports')])
		])

	#SET UP COMBINED WORKFLOW:
	pipeline = pe.Workflow(name=workflow_denominator+"_work")
	pipeline.base_dir = workflow_base

	pipeline.connect([(bg_preproc_workflow, analysis_workflow, [('Bru2_converter.nii_file','melodic.in_files')])
		])

	pipeline.write_graph(graph2use="orig")
	pipeline.run(plugin="MultiProc")

if __name__ == "__main__":
	quick_melodic(workflow_base="~/NIdata/ofM.dr/")
