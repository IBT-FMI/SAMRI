import numpy as np
from os import path
from matplotlib import rcParams
from samri.utilities import bids_substitution_iterator
from samri.plotting import maps

def multipage_plot(results, subjects,
	page_rows=4,
	template='/usr/share/mouse-brain-atlases/dsurqec_40micron_masked.nii',
	base_cut_coords=[None],
	save_as="",
	overlays=[],
	scale=0.6,
	threshold=0.1,
	dim=0.8,
	figure_title="",
	):

	rcParams['axes.titlepad'] = 200

	save_as_base, save_as_ext = path.splitext(save_as)
	valid_subjects = list(set([i['subject'] for i in results if bool(i['result']) and i['subject'] in subjects]))
	subjects_paginated = [valid_subjects[i:i+page_rows] for i in range(0, len(valid_subjects), page_rows)]
	for ix, subjects_page in enumerate(subjects_paginated):
		results_page = [i for i in results if i['subject'] in subjects_page]
		my_maps, subplot_titles, cut_coords = multiplot_matrix(results_page, 'result', base_cut_coords=base_cut_coords)
		save_as_page = save_as_base+str(ix)+save_as_ext
		maps.stat(my_maps,
			figure_title=figure_title,
			template=template,
			threshold=threshold,
			cut_coords=cut_coords,
			overlays=overlays,
			save_as=save_as_page,
			scale=scale,
			subplot_titles=subplot_titles,
			dim=dim,
			)


def multiplot_matrix(results, plottable_element_label,
	base_cut_coords=[],
	):
	"""
	Transform results list which contain subject and session info into arrays suitable as input for multiple-plotting-compatible functions, in which the sessions represent columns, and the subjects represent rows.

	Parameters
	----------

	results : list of dict
		A list of dictionaries keys of which include "subject", "session", and he value of `plottable_element_label`.
	plottable_element_label : str
		A string which specifies under what key of the dictionaries from `results` the plottable elements can be found.
	base_cut_coords : list, optional
		A list of cut coordinates (which are themselves either `None` or a list of floats or a list of ints). This is only relevant for statistic map plotting.
	"""
	fc_maps = []
	subplot_titles = []
	cut_coords = []
	subjects = set([i["subject"] for i in results])
	for ix, sub in enumerate(subjects):
		row = [i for i in results if i["subject"]==sub]
		fc_maps_row = [i[plottable_element_label] for i in row]
		subplot_titles_row = ["{}-{}".format(i["subject"],i["session"]) for i in row]
		for map_cut_coords in base_cut_coords:
			cut_coords_row = [map_cut_coords for i in row]
			cut_coords.append(cut_coords_row)
			fc_maps.append(fc_maps_row)
			subplot_titles.append(subplot_titles_row)
	fc_maps = np.array(fc_maps)
	subplot_titles = np.array(subplot_titles)
	cut_coords = np.array(cut_coords)

	return fc_maps, subplot_titles, cut_coords
