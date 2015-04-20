from nibabel.nifti1 import Nifti1Header
import nibabel as nib

example_filename = "50001-T2S_EP_Feb2015_multi.nii.gz"
example_filelist=[
	"/home/chymera/src/RS/EPI23.nii.gz",
	"/home/chymera/src/RS/EPI11.nii.gz",
	"/home/chymera/src/RS/EPI17.nii.gz"
]
example_filelist_joanes=[
	"/home/chymera/src/RS/1eME.nii",
	"/home/chymera/src/RS/2eME.nii",
	"/home/chymera/src/RS/3eME.nii"
]

# img = nib.load(example_filename)
# print img.header

for example_file in example_filelist_joanes:
	img=nib.load(example_file)
	text_file = open("Output_joanes.txt", "w")
	text_file.write(str(img.header))
	text_file.close()

# hdr = Nifti1Header("50001-T2S_EP_Feb2015_multi.nii.gz")
