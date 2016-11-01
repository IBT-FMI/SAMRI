from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker
import nibabel as nib
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from nilearn.input_data import NiftiMasker
sns.set_style("white", {'legend.frameon': True})
plt.style.use('ggplot')

from itertools import product

qualitative_colorset = ["#000000", "#E69F00", "#56B4E9", "#009E73","#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

try: FileNotFoundError
except NameError:
	class FileNotFoundError(OSError):
		pass

def roi_per_session(participants, legend_loc="best", roi="f_dr"):
	sessions = ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]
	df = pd.DataFrame({})
	roi_path = "/home/chymera/NIdata/templates/roi/{}_chr.nii.gz".format(roi)
	masker = NiftiMasker(mask_img=roi_path, standardize=True)
	for participant, session in product(participants, sessions):
		data={}
		try:
			session_participant_file = "/home/chymera/NIdata/ofM.dr/l1/dr_mask/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_tstat.nii.gz".format(participant,session)
			img = nib.load(session_participant_file)
			img = masker.fit_transform(img)
			# img = img[np.where(abs(img) >= 3 )]
			# value = np.nansum(img)
			img = img.flatten()
		except (FileNotFoundError, nib.py3k.FileNotFoundError):
			img=[None]
		data["session"]=session
		data["participant"]=participant
		for i in img:
			data["value"]=i
			df_ = pd.DataFrame(data, index=[None])
			df = pd.concat([df,df_])
	sns.pointplot(x="session", y="value", hue="participant", data=df, dodge=True, jitter=True, legend_out=False)
	# sns.violinplot(x="session", y="value", hue="participant", data=df, inner=None)
	# sns.swarmplot(x="session", y="value", hue="participant", data=df, split=True)

def fc_per_session(participants, legend_loc="best"):
	sessions = ["ofM","ofM_aF","ofM_cF1","ofM_cF2","ofM_pF"]
	df = pd.DataFrame({})
	for participant, session in product(participants, sessions):
		data={}
		try:
			session_participant_file = "/home/chymera/NIdata/ofM.dr/l1/dr_mask/sub-{0}/ses-{1}/sub-{0}_ses-{1}_trial-7_EPI_CBV_tstat.nii.gz".format(participant,session)
			img = nib.load(session_participant_file)
			value = np.nansum(img.get_data())
		except FileNotFoundError:
			value=None
		data["session"]=session
		data["participant"]=participant
		data["value"]=value
		# print(session,participant,value)
		df_ = pd.DataFrame(data, index=[None])
		df = pd.concat([df,df_])
	# sns.swarmplot(x="session", y="value", hue="participant", data=df)
	sns.factorplot(x="session", y="value", hue="participant", data=df)
	# sns.tsplot(time="session", value="value", condition="participant", data=df, err_style="unit_traces")
	# plt.legend(loc=legend_loc)

if __name__ == '__main__':
	roi_per_session(participants=[4007,4008,4009,4011,4012], legend_loc=2)
	plt.show()
