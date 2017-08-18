import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util		# utility
import pandas as pd
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, Level1Design, FEATModel, Merge, L2Model, FLAMEO
from nipype.interfaces.base import Bunch
from nipype.algorithms.modelgen import SpecifyModel
from os import path

import matplotlib.pyplot as plt
import matplotlib


def get_subjectinfo(subject_delay, scan_type, scan_types):
	import pandas as pd
	from copy import deepcopy
	import sys
	sys.path.append('/home/chymera/src/LabbookDB/db/')
	from query import loadSession
	from common_classes import LaserStimulationProtocol
	db_path="~/meta.db"

	session, engine = loadSession(db_path)

	sql_query=session.query(LaserStimulationProtocol).filter(LaserStimulationProtocol.code==scan_types[scan_type])
	mystring = sql_query.statement
	mydf = pd.read_sql_query(mystring,engine)
	delay = int(mydf["stimulation_onset"][0])
	inter_stimulus_duration = int(mydf["inter_stimulus_duration"][0])
	stimulus_duration = mydf["stimulus_duration"][0]
	stimulus_repetitions = mydf["stimulus_repetitions"][0]

	onsets=[]
	names=[]
	for i in range(stimulus_repetitions):
		onset = delay+(inter_stimulus_duration+stimulus_duration)*i
		onsets.append([onset])
		names.append("s"+str(i+1))
	output = []
	for idx_a, a in enumerate(onsets):
		for idx_b, b in enumerate(a):
			onsets[idx_a][idx_b] = round(b-subject_delay, 2) #floating point values don't add up nicely, so we have to round (https://docs.python.org/2/tutorial/floatingpoint.html)
	output.append(Bunch(conditions=names,
					onsets=deepcopy(onsets),
					durations=[[stimulus_duration]]*stimulus_repetitions
					))
	return output

def plotmodel(matfile):
	with open(matfile, 'r') as f:
		first_line = f.readline()
	length = first_line.split("\t")[1]
	column_names = range(int(length))
	df = pd.read_csv(matfile, skiprows=5, sep="\t", header=None, names=column_names, index_col=False)
	df.plot()
	plt.show()

def subjectinfo(subject_delay):
	from nipype.interfaces.base import Bunch
	from copy import deepcopy
	onsets=[]
	for i in range(6):
		onsets.append([range(222,222+180*6,180)[i]])
	output = []
	names = ['s1', 's2', 's3', 's4', 's5', 's6']
	for idx_a, a in enumerate(onsets):
		for idx_b, b in enumerate(a):
			onsets[idx_a][idx_b] = b-subject_delay
	output.append(Bunch(conditions=names,
					onsets=deepcopy(onsets),
					durations=[[20.0], [20.0], [20.0], [20.0], [20.0], [20.0]],
					))
	return output

def test_model(base_dir, plot=False, workflow_name="test_model_wf"):

	specify_model = pe.Node(interface=SpecifyModel(), name="specify_model")
	specify_model.inputs.input_units = 'secs'
	specify_model.inputs.functional_runs = ["/home/chymera/ni_data/ofM.dr/level1/Preprocessing/_condition_ofM_subject_4011/functional_bandpass/corr_16_trans_filt.nii.gz"]
	specify_model.inputs.time_repetition = 1
	specify_model.inputs.high_pass_filter_cutoff = 0 #switch to 240
	specify_model.inputs.subject_info = subjectinfo(49.55)

	level1design = pe.Node(interface=Level1Design(), name="level1design")
	level1design.inputs.interscan_interval = 1
	level1design.inputs.bases = {'gamma': {'derivs': False}}
	level1design.inputs.model_serial_correlations = True
	level1design.inputs.contrasts = [('allStim','T', ["s1","s2","s3","s4","s5","s6"],[1,1,1,1,1,1])]

	modelgen = pe.Node(interface=FEATModel(), name='modelgen')

	test_model_wf = pe.Workflow(name=workflow_name)
	test_model_wf.base_dir = base_dir

	test_model_wf.connect([
		(specify_model,level1design,[('session_info','session_info')]),
		(level1design, modelgen, [('ev_files', 'ev_files')]),
		(level1design, modelgen, [('fsf_files', 'fsf_file')]),
		])

	# test_model_wf.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})
	test_model_wf.run()
	test_model_wf.write_graph(dotfilename="graph.dot", graph2use="hierarchical", format="png")

	if plot:
		matfile = path.join(base_dir,workflow_name,"modelgen/run0.mat")
		plotmodel(matfile)

def get_scan(c,s,d):
	result = str(c)+str(s)+str(d)
	return result, d
def firstfunction(c,s,d):
	result = str(c)+str(s)+str(d)
	return result
def secondfunction(e,f):
	result = str(e)+"|"+str(f)
	return result
def bru2nii(input_dir,f):
	result = str(input_dir)+str(f)
	return result
def final_function(inp):
	result = "final"+str(inp)
	return result

def test_multiconnection():
	infosource = pe.Node(interface=util.IdentityInterface(fields=['condition','subject']), name="infosource")
	infosource.iterables = [('condition',["a","b","c"]), ('subject',[1,2,3])]

	firstfunctionA = pe.Node(name='firstfunctionA', interface=util.Function(function=firstfunction,input_names=["c","s","d"], output_names=['result']))
	firstfunctionA.iterables = ("d", ["x","y","z"])
	firstfunctionB = pe.Node(name='firstfunctionB', interface=util.Function(function=firstfunction,input_names=["c","s","d"], output_names=['result']))
	firstfunctionB.iterables = ("d", ["X","Y","Z"])

	secondfunctionX = pe.Node(name='secondfunctionX', interface=util.Function(function=secondfunction,input_names=["e","f"], output_names=['myresult']))

	workflow = pe.Workflow(name="test_connections")

	workflow_connections = [
		(infosource, firstfunctionA, [('condition', 'c'),('subject', 's')]),
		(infosource, firstfunctionB, [('condition', 'c'),('subject', 's')]),
		(firstfunctionA, secondfunctionX, [('result', 'e')]),
		(firstfunctionB, secondfunctionX, [('result', 'f')]),
		]
	workflow.connect(workflow_connections)
	workflow.write_graph(dotfilename="graph.dot", graph2use="flat", format="png")

	workflow.base_dir = "/home/chymera/test"
	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})

def test_connections():
	infosource = pe.Node(interface=util.IdentityInterface(fields=['condition','subject']), name="infosource")
	infosource.iterables = [('condition',["a","b","c"]), ('subject',[1,2,3])]

	get_functional_scan = pe.Node(name='get_functional_scan', interface=util.Function(function=get_scan,input_names=["c","s","d"], output_names=['scan_path','d']))
	get_functional_scan.iterables = ("d", ["x","y","z"])
	# functional_bru2nii = pe.Node(name='functional_bru2nii', interface=util.Function(function=bru2nii,input_names=["input_dir","f"], output_names=['myresult']))
	finalI = pe.Node(name='finalI', interface=util.Function(function=final_function,input_names=["inp"], output_names=['myfinalresult']))
	# functional_bru2nii.inputs.f = 1

	def concat(first):
		result = str(first)+"second"
		return result
	# def concat(first,second):
	# 	result = str(first)+str(second)
	# 	return result

	workflow = pe.Workflow(name="test_connections")

	workflow_connections = [
		(infosource, get_functional_scan, [('condition', 'c'),('subject', 's')]),
		(('get_functional_scan.scan_path',concat),'final.inp'),
		]
		# (get_functional_scan, functional_bru2nii, [('scan_path', 'input_dir')]),
		# (get_functional_scan, functional_bru2nii, [('d', 'f')]),
	workflow.connect(workflow_connections)
	workflow.write_graph(dotfilename="graph.dot", graph2use="flat", format="png")

	workflow.base_dir = "/home/chymera/test"
	workflow.run(plugin="MultiProc",  plugin_args={'n_procs' : 4})


if __name__ == '__main__':
	# plotmodel("/home/chymera/src/chyMRI/tests/test_model_wf/level1design/run0.mat")
	# test_model("/home/chymera/src/chyMRI/tests", plot=True)
	test_multiconnection()
	# scan_type = "EPI_CBV_jin10"
	# scan_types = {'EPI_CBV_jin10': 'jin10', 'EPI_CBV_jin60': 'jin60'}
	# subject_delay = 49.35
	# print get_subjectinfo(subject_delay, scan_type, scan_types)
