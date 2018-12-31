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
data_path = path.join(data_dir,'DSURQEc_dr.csv')
subjectdf = pd.read_csv(data_path)
subjectdf = full_subsets(subjectdf, 5)

cmap = plt.get_cmap('tab20').colors

qualitative_times(subjectdf[subjectdf['treatment']=="Vehicle"],
        x='Session',
        y='t',
        unit=None,
        condition='subject',
        palette=cmap[1::2],
        #palette=cmap_grey[::2],
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
qualitative_times(subjectdf[subjectdf['treatment']=="Fluoxetine"],
        x='Session',
        y='t',
        unit=None,
        condition='subject',
        palette=cmap[::2],
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
plt.savefig('dr_activity_ind.pdf')
