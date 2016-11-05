import preprocessing, glm


if __name__ == '__main__':
	glm.l1("~/NIdata/ofM.dr/preprocessing/composite", workflow_name="composite", include={"subjects":[i for i in range(4001,4010)]+[4011,4012]}, habituation="confound",mask="/home/chymera/NIdata/templates/roi/f_dr_chr_bin.nii.gz",)
