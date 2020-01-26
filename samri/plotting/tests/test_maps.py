#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import samri.plotting.maps as maps
import seaborn as sns
from os import path
import pytest

def test_atlas_labels_longtime():
       maps.atlas_labels()

def test_atlas_labels():
       mapping = pd.read_csv('/usr/share/mouse-brain-atlases/dsurqe_labels.csv')
       mapping = mapping.iloc[::60, :]
       maps.atlas_labels(mapping=mapping)

def test_slices():
       bindata_dir = '/usr/share/samri_bidsdata'
       heatmap_image = '{}/l1/sub-4007/ses-ofM/sub-4007_ses-ofM_task-JogB_acq-EPIlowcov_run-1_cbv_tstat.nii.gz'.format(bindata_dir)
       contour_image = '{}/l1/sub-4007/ses-ofMaF/sub-4007_ses-ofMaF_task-JogB_acq-EPIlowcov_run-1_cbv_tstat.nii.gz'.format(bindata_dir)
       maps.slices(heatmap_image,
	      contour_image=contour_image,
	      save_as='test_slices.pdf',
	      )

def test_population_roi_over_time():
       # Style elements
       palette=["#56B4E9", "#E69F00"]

       data_dir = path.join(path.dirname(path.realpath(__file__)),"../../tests/data")
       data_path = path.join(data_dir,'drs_activity.csv')
       df = pd.read_csv(data_path)

       df = df.rename(columns={'t':'Mean t-Statistic'})
       df['Session']=df['Session'].map({
	       'ofM':'naïve',
	       'ofMaF':'acute',
	       'ofMcF1':'chronic/2w',
	       'ofMcF2':'chronic/4w',
	       'ofMpF':'post',
	       })


       # definitions for the axes
       left, width = 0.06, 0.9
       bottom, height = 0.06, 0.9

       session_coordinates = [left, bottom, width, height]
       roi_coordinates = [left+0.02, bottom+0.7, 0.3, 0.2]

       fig = plt.figure(1)

       ax1 = plt.axes(session_coordinates)
       sns.pointplot(
	      x='Session',
	      y='Mean t-Statistic',
	      units='subject',
	      data=df,
	      hue='treatment',
	      dodge=True,
	      palette=palette,
	      order=['naïve','acute','chronic/2w','chronic/4w','post'],
	      ax=ax1,
	      ci=95,
	      )

       ax2 = plt.axes(roi_coordinates)
       maps.atlas_label('/usr/share/mouse-brain-atlases/dsurqec_200micron_roi-dr.nii',
	       scale=0.3,
	       color="#E69F00",
	       ax=ax2,
	       annotate=False,
	       alpha=0.8,
	       )

       plt.savefig('_test_population_roi_over_time.png')
