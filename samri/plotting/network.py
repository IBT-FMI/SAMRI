from graph_tool.all import *
import matplotlib.pyplot as plt

CYAN = (0,0.9,0.9,1)
CYAN_ = (0,0.9,0.9,0.5)
CORAL = (0.9,0.4,0.2,1)
CORAL_ = (0.9,0.4,0.2,0.5)
ORANGE = (0.9,0.62,0.0,1)
ORANGE_ = (0.9,0.62,0.0,0.5)
GRAY = (0.6,0.6,0.6,1)
GRAY_ = (0.6,0.6,0.6,0.5)

def default_graph():
	g = Graph()
	vlabel = g.new_vertex_property('string')
	g.vertex_properties['vlabel'] = vlabel
	vcolor = g.new_vertex_property('vector<double>')
	g.vertex_properties['vcolor'] = vcolor
	vfillcolor = g.new_vertex_property('vector<double>')
	g.vertex_properties['vfillcolor'] = vfillcolor
	vtext_color = g.new_vertex_property('vector<double>')
	g.vertex_properties['vtext_color'] = vtext_color
	vposition = g.new_vertex_property('vector<double>')
	g.vertex_properties['vposition'] = vposition
	# vfontsize = g.new_vertex_property('double')
	# g.vertex_properties['font_size'] = vfontsize

	egradient = g.new_edge_property('vector<double>')
	g.edge_properties['egradient'] = egradient
	ewidth = g.new_edge_property('double')
	g.edge_properties['ewidth'] = ewidth
	elabel = g.new_edge_property("string")
	g.edge_properties['elabel'] = elabel
	# efontsize = g.new_edge_property("double")
	# g.edge_properties['font_size'] = efontsize
	return g

def add_nodes(g, which="basic"):
	v1 = g.add_vertex()
	g.vp.vposition[v1] = (1.5,1.5)
	g.vp.vlabel[v1] = "laser"
	g.vp.vcolor[v1] = CYAN
	g.vp.vfillcolor[v1] = CYAN_
	# g.vp.vfontsize[v1] = 3
	v2 = g.add_vertex()
	g.vp.vposition[v2] = (1,2)
	g.vp.vlabel[v2] = "DR"
	g.vp.vcolor[v2] = ORANGE_
	g.vp.vfillcolor[v2] = ORANGE
	# g.vp.vfontsize[v2] = 6
	v3 = g.add_vertex()
	g.vp.vposition[v3] = (2,2)
	g.vp.vlabel[v3] = "Cortex"
	g.vp.vcolor[v3] = CORAL_
	g.vp.vfillcolor[v3] = CORAL
	# g.vp.vfontsize[v3] = 9
	return g, (v1,v2,v3)

def plot_graph(g, output=None, fit_view=0.9, graphsize=500, scale=1):
	pos = fruchterman_reingold_layout(g, n_iter=1000)
	graph_draw(g,
		pos=g.vertex_properties['vposition'],
		vertex_text=g.vertex_properties['vlabel'],
		vertex_color=g.vertex_properties['vcolor'],
		vertex_fill_color=g.vertex_properties['vfillcolor'],
		vertex_font_size=16*scale,
		edge_gradient=g.ep.egradient,
		edge_pen_width=g.ep.ewidth,
		edge_text=g.ep.elabel,
		edge_font_size=30*scale,
		edge_text_distance=15*(scale/2),
		output_size=(graphsize, graphsize),
		output=output,
		)

def simple_dr(output=None, fit_view=0.9, graphsize=500, scale=1):
	g = default_graph()
	g, (v1,v2,v3) = add_nodes(g)

	e = g.add_edge(v1, v2)
	g.ep.egradient[e] = (1,)+CYAN
	g.ep.ewidth[e] = 16
	g.ep.elabel[e] = "u1"
	# g.ep.efontsize[e] = 10
	e = g.add_edge(v2, v3)
	g.ep.egradient[e] = (1,)+ORANGE
	g.ep.ewidth[e] = 8
	g.ep.elabel[e] = "u2"
	# g.ep.efontsize[e] = 10
	e = g.add_edge(v1, v3)
	g.ep.egradient[e] = (1,)+GRAY
	g.ep.ewidth[e] = 4
	g.ep.elabel[e] = "u3"
	# g.ep.efontsize[e] = 10

	plot_graph(g, output, fit_view, graphsize, scale)
