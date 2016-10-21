from graph_tool.all import *
import matplotlib.pyplot as plt

CYAN = (0,0.9,0.9,1)
CYAN_ = (0,0.9,0.9,0.5)
CORAL = (0.9,0.4,0.2,1)
CORAL_ = (0.9,0.4,0.2,0.5)

def dcm_graph():
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

	egradient = g.new_edge_property('vector<double>')
	g.edge_properties['egradient'] = egradient
	ewidth = g.new_edge_property('double')
	g.edge_properties['ewidth'] = ewidth


	v1 = g.add_vertex()
	g.vp.vposition[v1] = (1,1)
	g.vp.vlabel[v1] = "laser"
	g.vp.vcolor[v1] = CYAN
	g.vp.vfillcolor[v1] = CYAN_
	v2 = g.add_vertex()
	g.vp.vposition[v2] = (1,2)
	g.vp.vlabel[v2] = "DR"
	g.vp.vcolor[v2] = CYAN_
	g.vp.vfillcolor[v2] = CORAL
	v3 = g.add_vertex()
	g.vp.vposition[v3] = (2,2)
	g.vp.vlabel[v3] = "Cortex"
	g.vp.vcolor[v3] = CORAL_
	g.vp.vfillcolor[v3] = CORAL

	e = g.add_edge(v1, v2)
	g.ep.egradient[e] = (1,)+CYAN
	g.ep.ewidth[e] = 14
	e = g.add_edge(v2, v2)
	g.ep.egradient[e] = (1,)+CORAL
	g.ep.ewidth[e] = 3
	e = g.add_edge(v2, v3)
	g.ep.egradient[e] = (1,)+CORAL
	g.ep.ewidth[e] = 7
	e = g.add_edge(v3, v2)
	g.ep.egradient[e] = (1,)+CORAL
	g.ep.ewidth[e] = 3

	# pos = sfdp_layout(g)
	pos = fruchterman_reingold_layout(g, n_iter=1000)
	# pos = arf_layout(g, max_iter=0)
	# pos = radial_tree_layout(g, g.vertex(0))
	# pos = planar_layout(g)


	graph_draw(g,
		pos=g.vertex_properties['vposition'],
		vertex_text=g.vertex_properties['vlabel'],
		vertex_color=g.vertex_properties['vcolor'],
		vertex_fill_color=g.vertex_properties['vfillcolor'],
		vertex_font_size=16,
		edge_gradient=g.edge_properties["egradient"],
		edge_pen_width=g.edge_properties["ewidth"],
		output_size=(500, 500),
		output="~/two-nodes.pdf",
		)
	plt.show()

if __name__ == '__main__':
	dcm_graph()
