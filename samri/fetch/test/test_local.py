import numpy as np

def test_summary_atlas():
	from samri.fetch.local import summary_atlas

	mapping='/usr/share/mouse-brain-atlases/dsurqe_labels.csv'
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii'
	summary={
		1:{
			'structure':'Hippocampus',
			'summarize':['CA'],
			'laterality':'right',
			},
		2:{
			'structure':'Hippocampus',
			'summarize':['CA'],
			'laterality':'left',
			},
		3:{
			'structure':'Cortex',
			'summarize':['cortex'],
			'laterality':'right',
			},
		4:{
			'structure':'Cortex',
			'summarize':['cortex'],
			'laterality':'left',
			},
		}

	new_atlas, new_mapping = summary_atlas(atlas,mapping,
		summary=summary,
		)
	new_atlas_data = new_atlas.get_data()
	output_labels = np.unique(new_atlas_data).tolist()
	target_labels = [0,]
	target_labels.extend([i for i in summary.keys()])
	assert output_labels == target_labels

def test_roi_from_atlaslabel():
	from samri.fetch.local import roi_from_atlaslabel

	mapping='/usr/share/mouse-brain-atlases/dsurqe_labels.csv'
	atlas='/usr/share/mouse-brain-atlases/dsurqec_40micron_labels.nii'

	my_roi = roi_from_atlaslabel(atlas,
		mapping=mapping,
		label_names=['cortex'],
		)
	roi_data = my_roi.get_data()
	output_labels = np.unique(roi_data).tolist()
	assert output_labels == [0, 1]

	my_roi = roi_from_atlaslabel(atlas,
		mapping=mapping,
		label_names=['cortex'],
		output_label=3,
		)
	roi_data = my_roi.get_data()
	output_labels = np.unique(roi_data).tolist()
	assert output_labels == [0, 3]

