import nipype.pipeline.engine as pe				# pypeline engine
from extra_interfaces import Bru2

def quick_melodic(workflow_base=".", series_dir):
	Bru2_converter = pe.Node(interface=Bru2(), name="convert_resize")
	Bru2_converter.inputs.input_dir = series_dir

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.report = True

	workflow.connect([
		(Bru2_converter, melodic, [('nii_files', 'in_files')])
		])

	workflow.write_graph(graph2use="orig")
	workflow.run(plugin="MultiProc")

if __name__ == "__main__":
	series_dir="~/NIdata/ofM.dr/20151027_141609_4011_ofM_1_1/16"
	preproc_workflow(workflow_base="~/NIdata/ofM.dr/", series_dir=series_dir)
