from extra_interfaces import BlurToFWHM
blur = BlurToFWHM()
blur.inputs.in_file = '/home/chymera/utils/3dblur/trans_10.nii.gz'
blur.inputs.out_file = '/home/chymera/utils/3dblur/b_10.nii.gz'
blur.inputs.fwhm = 5.6
print blur.cmdline
blur.run()
