from extra_interfaces import 3dBlurToFWHM
mybet = fsl.BET()
mybet.inputs.in_file = 'foo.nii'
mybet.inputs.out_file = 'bar.nii'
result = mybet.run()
