import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.fsl import GLM

def fsl_glm(workflow_base, scan_type, workflow_denominator="FSL_GLM", omit_ID=[]):
	workflow_base = path.expanduser(workflow_base)
	bg_preproc_workflow = bg_preproc(workflow_base, scan_type, omit_ID=omit_ID)

if __name__ == "__main__":
	quick_melodic(workflow_base="~/NIdata/ofM.dr/", scan_type="7_EPI_CBV", omit_ID=["measurement_id_20151026_135856_4006_1_1"])
