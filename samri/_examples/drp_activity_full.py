#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import pandas as pd
from behaviopy.plotting import qualitative_times
from behaviopy.utils import full_subsets
from os import path
import matplotlib.pyplot as plt

data_dir = path.abspath(path.expanduser('~/ni_data/ofM.dr/bids/l1/generic'))
data_path = path.join(data_dir,'DSURQEc_drp.csv')
subjectdf = pd.read_csv(data_path)
subjectdf = full_subsets(subjectdf, 5)

cmap = plt.get_cmap('tab20').colors

qualitative_times(subjectdf,
        x='Session',
        y='t',
        condition='treatment',
        unit='subject',
        ci=90,
        palette=cmap,
        order=['naïve','acute','chronic (2w)','chronic (4w)','post'],
        bp_style=False,
        renames={
                'Session':{
                        'ofM':'naïve',
                        'ofMaF':'acute',
                        'ofMcF1':'chronic (2w)',
                        'ofMcF2':'chronic (4w)',
                        'ofMpF':'post',
                        },
                },
        )
plt.savefig('drp_activity_full.pdf')

import statsmodels.formula.api as smf
import numpy as np

model = smf.mixedlm("t ~ Session * treatment", subjectdf, groups=subjectdf["subject"])
fit = model.fit()
report = fit.summary()

print(report)
print(fit.params)
omnibus_tests = np.eye(len(fit.params))[1:-1]
omnibus_tests = omnibus_tests[:4]
omnibus_tests[0,6] = -1
omnibus_tests[1,7] = -1
omnibus_tests[2,8] = -1
omnibus_tests[3,9] = -1
print(omnibus_tests)
anova = fit.f_test(omnibus_tests)
print(anova)
