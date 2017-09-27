import numpy as np

def multiplot_matrix(results_df, plottable_element_label,
	per_map_cut_coords=[],
	):
	"""
	Transform results list into arrays suitable as input for multiple-plotting-compatible functions.

	Parameters
	----------

	results_df : list of dict
		A list of dictionaries keys of which include "subject", "session", and he value of `plottable_element_label`.
	plottable_element_label : str
		A string which specifies under what key of the dictionaries from `results_df` the plottable elements can be found.
	per_map_cut_coords : list, optional
		A list of cut coordinates (which are themselves either `None` or a list of floats or a list of ints). This is only relevant for statistic map plotting.
	"""
	fc_maps = []
	subplot_titles = []
	cut_coords = []
	subjects = set([i["subject"] for i in results_df])
	for ix, sub in enumerate(subjects):
		row = [i for i in results_df if i["subject"]==sub]
		fc_maps_row = [i[plottable_element_label] for i in row]
		subplot_titles_row = ["{}-{}".format(i["subject"],i["session"]) for i in row]
		for per_map_cut_coord in per_map_cut_coords:
			cut_coords_row = [per_map_cut_coord for i in row]
			cut_coords.append(cut_coords_row)
			fc_maps.append(fc_maps_row)
			subplot_titles.append(subplot_titles_row)
	fc_maps = np.array(fc_maps)
	subplot_titles = np.array(subplot_titles)
	cut_coords = np.array(cut_coords)

	return fc_maps, subplot_titles, cut_coords
