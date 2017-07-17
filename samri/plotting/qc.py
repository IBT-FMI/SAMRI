import nibabel as nib
from matplotlib import pyplot as plt
import matplotlib.mlab as mlab
import numpy as np
from scipy.stats import norm
import os.path 

def plot_t_value_hist(img_path='/home/chymera/ni_data/ofM.dr/l1/as_composite/sub-5703/ses-ofM/sub-5703_ses-ofM_trial-EPI_CBV_chr_longSOA_tstat.nii.gz',
	roi_path='/home/chymera/ni_data/templates/roi/DSURQEc_ctx.nii.gz',
	mask_path='/home/chymera/ni_data/templates/DSURQEc_200micron_mask.nii.gz',
	save_as='~/qc_tvalues.pdf',
	):
	"""Make t-value histogram plot"""
	f, axarr = plt.subplots(1, sharex=True)

	roi = nib.load(os.path.expanduser(roi_path))
	roi_data = roi.get_data()
	mask = nib.load(os.path.expanduser(mask_path))
	mask_data = mask.get_data()
	idx = np.nonzero(np.multiply(roi_data,mask_data))
	img = nib.load(os.path.expanduser(img_path))
	data = img.get_data()[idx]
	(mu, sigma) = norm.fit(data)
	n, bins, patches = axarr.hist(data,'auto',normed=1, facecolor='green', alpha=0.75)
	y = mlab.normpdf(bins, mu, sigma)

	axarr.plot(bins, y, 'r--', linewidth=2)
	axarr.set_title('Histogram of t-values $\mathrm{(\mu=%.3f,\ \sigma=%.3f}$)' %(mu, sigma))
	axarr.set_xlabel('t-values')
	plt.savefig(os.path.expanduser(save_as))
