#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import samri.plotting.maps as maps
from behaviopy.plotting import qualitative_times
from os import path

data_dir = path.join(path.dirname(path.realpath(__file__)),"../../example_data/ioanas2018")
data_path = path.join(data_dir,'pattern_summary.csv')
df = pd.read_csv(data_path)

df = df.rename(columns={'t':'Arbitrary Units'})

# definitions for the axes
left, width = 0.06, 0.9
bottom, height = 0.06, 0.9

session_coordinates = [left, bottom, width, height]
roi_coordinates = [left+0.45, bottom+0.7, 0.3, 0.2]

fig = plt.figure(1)

ax1 = plt.axes(session_coordinates)
qualitative_times(df,
        ax=ax1,
        x='Session',
        y='Arbitrary Units',
        condition='treatment',
        unit='subject',
        ci=90,
        palette=["#56B4E9", "#E69F00"],
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

ax2 = plt.axes(roi_coordinates)
stat_map = path.abspath(path.expanduser('~/ni_data/ofM.dr/bids/l2/best_responders/sessionofM/tstat1.nii.gz'))
template = path.abspath(path.expanduser('/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii'))
maps.stat(stat_maps=[stat_map],
        template=template,
        cut_coords=[(0,-4.3,-3.3)],
        annotate=False,
        scale=0.3,
        show_plot=False,
        interpolation=None,
        threshold=4,
        draw_colorbar=False,
        ax=ax2,
        )
