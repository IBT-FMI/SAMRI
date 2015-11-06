import nipype.pipeline.engine as pe
from extra_interfaces import Bru2
from nipype.interfaces.fsl import MELODIC
from os import path

def quick_melodic(series_dir, workflow_base="."):
	workflow_base = path.expanduser(workflow_base)
	series_dir = path.expanduser(series_dir)

	Bru2_converter = pe.Node(interface=Bru2(), name="convert_resize")
	Bru2_converter.inputs.input_dir = series_dir

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 10

	workflow = pe.Workflow(name='QuickMELODIC')
	workflow.base_dir = workflow_base

	workflow.connect([
		(Bru2_converter, melodic, [('nii_file', 'in_files')])
		])

	workflow.write_graph(graph2use="orig")
	workflow.run(plugin="MultiProc")

if __name__ == "__main__":
	series_dir="~/NIdata/ofM.dr/20151027_141609_4011_ofM_1_1/16"
	quick_melodic(workflow_base="~/NIdata/ofM.dr/", series_dir=series_dir)
