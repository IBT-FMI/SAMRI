import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util		# utility
from extra_interfaces import Bru2, FindScan
from nipype.interfaces.fsl import MELODIC
from os import path, listdir
import nipype.interfaces.io as nio

def quick_melodic(workflow_base=".", workflow_denominator="QuickMELODIC"):
	workflow_base = path.expanduser(workflow_base)
	IDs=[]
	for sub_dir in listdir(workflow_base):
		if sub_dir[:3] == "201":
			IDs.append(sub_dir)

	infosource = pe.Node(interface=util.IdentityInterface(fields=['measurement_id']), name="measurement_info_source")
	#define the list of subjects your pipeline should be executed on
	infosource.iterables = ('measurement_id', IDs)

	datasource1 = pe.Node(interface=nio.DataGrabber(infields=['measurement_id'], outfields=['measurement_path']), name='data_source1')
	datasource1.inputs.template = workflow_base+"/%s"
	datasource1.inputs.template_args['measurement_id'] = [['measurement_id']]
	datasource1.inputs.sort_filelist = True

	find_scan = pe.Node(interface=FindScan(), name="find_scan")
	find_scan.inputs.query = "7_EPI_CBV"
	find_scan.inputs.query_file = "acqp"

	Bru2_converter = pe.MapNode(interface=Bru2(), name="convert_resize", iterfield=['input_dir'])

	melodic = pe.Node(interface=MELODIC(), name="MELODIC")
	melodic.inputs.report = True
	melodic.inputs.dim = 8

	datasink = pe.Node(nio.DataSink(), name='sinker')
	datasink.inputs.base_directory = workflow_base+"/"+workflow_denominator+".results"

	#SET UP WORKFLOW:
	workflow = pe.Workflow(name=workflow_denominator+".work")
	workflow.base_dir = workflow_base

	workflow.connect([
		(infosource, datasource1, [('measurement_id', 'measurement_id')]),
		(datasource1, find_scan, [('measurement_path', 'scans_directory')]),
		(find_scan, Bru2_converter, [('positive_scans', 'input_dir')]),
		(Bru2_converter, melodic, [('nii_file', 'in_files')]),
		(melodic, datasink, [('report_dir', 'reports')])
		])

	workflow.write_graph(graph2use="orig")
	workflow.run(plugin="MultiProc")

if __name__ == "__main__":
	quick_melodic(workflow_base="~/NIdata/ofM.dr/")
