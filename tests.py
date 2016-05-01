import nipype.pipeline.engine as pe
import pandas as pd
from nipype.interfaces.fsl import GLM, MELODIC, FAST, BET, MeanImage, FLIRT, ApplyMask, ImageMaths, Level1Design, FEATModel, Merge, L2Model, FLAMEO
from nipype.interfaces.base import Bunch
from nipype.algorithms.modelgen import SpecifyModel
from os import path

import matplotlib.pyplot as plt
import matplotlib
matplotlib.style.use('ggplot')


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
	specify_model.inputs.functional_runs = ["/home/chymera/NIdata/ofM.dr/level1/Preprocessing/_condition_ofM_subject_4011/functional_bandpass/corr_16_trans_filt.nii.gz"]
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


if __name__ == '__main__':
	# plotmodel("/home/chymera/src/chyMRI/tests/test_model_wf/level1design/run0.mat")
	test_model("/home/chymera/src/chyMRI/tests", plot=False)
