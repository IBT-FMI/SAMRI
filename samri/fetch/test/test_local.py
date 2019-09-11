import numpy as np

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

