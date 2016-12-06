import os
import matplotlib.pyplot as plt

import design
import registration

def opto_fmri(save_as=False):
	irf = design.get_irf()
	print(design.period_padded_period_filtered(irf, 8, 20, 150))
	if save_as:
		save_as = os.path.expanduser(save_as)
		plt.savefig(save_as,dpi=300, transparent=False)
	else:
		plt.show()

if __name__ == '__main__':
	opto_fmri()
	# opto_fmri("~/design.png")
