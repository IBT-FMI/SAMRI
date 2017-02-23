import os
import matplotlib.pyplot as plt
import numpy as np

import design
import registration

plt.style.use(u'seaborn-darkgrid')
plt.style.use(u'ggplot')

def opto_fmri(save_as=False):
	irf = design.get_irf()
	print(design.period_padded_period_filtered(irf, 8, 20, 150))
	if save_as:
		save_as = os.path.expanduser(save_as)
		plt.savefig(save_as,dpi=300, transparent=False)
	else:
		plt.show()

def save_irf(filename="~/irf.txt"):
	filename = os.path.abspath(os.path.expanduser(filename))
	irf = design.get_irf(1.8,8,resolution=20)
	np.savetxt(filename, irf, delimiter='\n')

if __name__ == '__main__':
	# opto_fmri()
	# opto_fmri("~/design.png")
	# registration.structural_rigid(template="~/test_markus/template4.nii.gz", input_image="~/test_markus/source_add.nii.gz", output_image="~/test_markus/registered.nii.gz")
	save_irf()
