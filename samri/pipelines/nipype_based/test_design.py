from extra_interfaces import SpecifyModel, Level1Design
from nipype.interfaces.fsl import GLM, FEATModel, Merge, L2Model, FLAMEO, model
if not __package__:
	import sys
	from os import path
	plotting_dir = path.abspath(path.join(path.dirname(path.realpath(__file__)),"../.."))
	sys.path.insert(0, plotting_dir)
	from plotting import timeseries

specify_model = SpecifyModel()
specify_model.inputs.input_units = 'secs'
specify_model.inputs.time_repetition = 1
specify_model.inputs.high_pass_filter_cutoff = 270
specify_model.inputs.event_files = ["/home/chymera/events.tsv"]
specify_model.inputs.functional_runs = ["/home/chymera//NIdata/ofM.dr/preprocessing/generic/sub-4007/ses-ofM_cF2/func/sub-4007_ses-ofM_cF2_trial-7_EPI_CBV.nii.gz"]
specify_model.inputs.one_condition_file = True
specify_model.inputs.habituation_regressor = True
specify_model_res = specify_model.run()

# print(specify_model_res.outputs.session_info)

level1design = Level1Design()
level1design.inputs.session_info = specify_model_res.outputs.session_info
level1design.inputs.interscan_interval = 1
level1design.inputs.bases = {'gamma': {'derivs':False, 'gammasigma':10, 'gammadelay':5}}
level1design.inputs.orthogonalization = {1: {0:0,1:0,2:0}, 2: {0:1,1:1,2:0}}
level1design.inputs.model_serial_correlations = True
level1design.inputs.contrasts = [('allStim','T', ["e0"],[1])] #condition names as defined in specify_model
level1design_res = level1design.run()

modelgen = FEATModel()
# modelgen.inputs.ev_files = ["/home/chymera/src/SAMRI/_ev_e0_0_1.txt",]
# modelgen.inputs.ev_files = ["/home/chymera/src/SAMRI/_ev_e0_0_1.txt", "/home/chymera/src/SAMRI/_ev_e1_0_1.txt"]
modelgen.inputs.ev_files = level1design_res.outputs.ev_files
# modelgen.inputs.fsf_file = "/home/chymera/src/SAMRI/_run0.fsf"
modelgen.inputs.fsf_file = level1design_res.outputs.fsf_files
modelgen_res = modelgen.run()


# print(modelgen_res.__dict__)
print(modelgen_res.outputs.design_file)
print(modelgen_res.outputs.con_file)

timeseries.roi_based(subject=4007, roi="ctx", workflows=["generic"])
