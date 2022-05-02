import numpy as np

def test_prepare_abi_connectivity_maps():
	from samri.fetch.local import prepare_abi_connectivity_maps
	prepare_abi_connectivity_maps('ventral_tegmental_area',
		invert_lr_experiments=[
			"127651139",
			"127796728",
			"127798146",
			"127867804",
			"156314762",
			"160539283",
			"160540751",
			"165975096",
			"166054222",
			"171021829",
			"175736945",
			"278178382",
			"292958638",
			"301062306",
			"304337288",
			],
		)

def test_prepare_feature_map(tmp_path):
	from samri.fetch.local import prepare_feature_map

	prepare_feature_map('/usr/share/ABI-connectivity-data/ventral_tegmental_area-127651139/',
		invert_lr=True,
		save_as=f'{tmp_path}/vta_127651139.nii.gz',
		)

def test_summary_atlas():
	from samri.fetch.local import summary_atlas

	mapping='/usr/share/mouse-brain-templates/dsurqe_labels.csv'
	atlas='/usr/share/mouse-brain-templates/dsurqec_40micron_labels.nii'
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

	mapping='/usr/share/mouse-brain-templates/dsurqe_labels.csv'
	atlas='/usr/share/mouse-brain-templates/dsurqec_40micron_labels.nii'

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

