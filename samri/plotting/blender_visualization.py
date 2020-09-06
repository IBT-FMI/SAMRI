import bpy
from bpy import context
import os
import sys
import argparse

## Example call from commandline: blender -b -P decimate_mesh_blender.py -- -f mesh.obj -o mesh_dec.obj -r 0.5 -i 2 -n 4 -l 0.5
## Blender will ignore all options after -- so parameters can be passed to python script.

# get the args passed to blender after "--", all of which are ignored by
# blender so scripts may receive their own arguments
argv = sys.argv
if "--" not in argv:
	argv = []  # as if no args are passed
else:
	argv = argv[argv.index("--") + 1:]  # get all args after "--"

path = os.path.abspath('.')
path = path + '/'

parser = argparse.ArgumentParser(description="Mesh Decimation",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--template_path','-t',type=str,default="")
parser.add_argument('--output_path','-o',type=str,default="")
parser.add_argument('--stat_map_path','-s',action='append',type=str)
parser.add_argument('--stat_map_color','-c',action='append',type=str)#Should be a list
parser.add_argument('--filename','-n',type=str)


args = parser.parse_args(argv)

def hex_to_rgb(value):
	gamma = 2.2
	value = value.lstrip('#')
	lv = len(value)
	fin = list(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
	r = pow(fin[0] / 255, gamma)
	g = pow(fin[1] / 255, gamma)
	b = pow(fin[2] / 255, gamma)
	fin.clear()
	fin.append(r)
	fin.append(g)
	fin.append(b)
	fin.append(1.0)
	return tuple(fin)


color=[]
for c in args.stat_map_color:
	print(c)
	color.append(hex_to_rgb(c))


##Function to deselect all objects
def deselect():
	for obj in bpy.data.objects:
		obj.select_set(False)

##File path
#path = os.path.abspath('.')
#path = os.path.abspath('.')
path = '/tmp/'


## Set Basic Scene: Import reference atlas mesh and desired gene expression/connectivity meshed
##, add a basic lamp and camera set to predefined location and rotation

#Reset factory settings
bpy.ops.wm.read_factory_settings()

#Get rid of blender default objects
for obj in bpy.data.objects:
	obj.select_set(True)
bpy.ops.object.delete()


#Import Reference Atlas
bpy.ops.import_scene.obj(filepath= args.template_path)
Atlas = bpy.context.selected_objects[0]
Atlas.data.use_auto_smooth = False


#Import Gene data
gene_data = []
for stat_map in args.stat_map_path:
	bpy.ops.import_scene.obj(filepath= stat_map)
	importedMesh=bpy.context.selected_objects[0]
	importedMesh.data.use_auto_smooth = False

	gene_data.append(bpy.context.selected_objects[0])

#Increase world brightness0
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)

bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 1


#Add a lamp, set location and rotation

bpy.ops.object.light_add(type='SUN', radius=1, location=(-0.00643184, -10.4931, 10.284))
Sun = bpy.context.selected_objects[0]

deselect()
Sun.select_set(True)
bpy.context.object.rotation_mode = 'AXIS_ANGLE'
bpy.context.object.rotation_axis_angle[0] = 3.02814
bpy.context.object.rotation_axis_angle[1] = 0.0004
bpy.context.object.rotation_axis_angle[2] = 0.387187
bpy.context.object.rotation_axis_angle[3] = -0.916546


#Try with a hemi lamp
#HEMI does not exist in 2.8+
deselect()
bpy.context.object.rotation_axis_angle[2] = 0.387187
bpy.ops.object.light_add(type='SUN', radius=1, location=(-0.00643184, -10.4931, 10.284))
Hemi = bpy.context.selected_objects[0]


#Create an empty to point camera to???
bpy.ops.object.empty_add(type='PLAIN_AXES',align='WORLD', location=(0, 0, 0))
Empty = bpy.context.selected_objects[0]

#Add a camera, set location and rotation
bpy.ops.object.camera_add(enter_editmode=False, location=(0, 0, 0), rotation=(1.10871, 0.0132652, 1.14827))
Camera = bpy.context.selected_objects[0]
Camera.data.lens = 35
Camera.data.sensor_width = 32
Camera.location = (0,-20,20)
Camera.scale[0] = -1

deselect()
Camera.select_set(True)

#bpy.context.object.rotation_mode = 'AXIS_ANGLE'
#bpy.context.object.rotation_axis_angle[0] = 3.12814
#bpy.context.object.rotation_axis_angle[1] = 0.000353694
#bpy.context.object.rotation_axis_angle[2] = 0.487187
#bpy.context.object.rotation_axis_angle[3] = -1.11655
#bpy.ops.transform.rotate(value=-1, constraint_axis=(False, False, True), constraint_orientation='LOCAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)

deselect()
Camera.select_set(True)
Empty.select_set(True)

deselect()
Camera.select_set(True)
#bpy.context.space_data.context = 'CONSTRAINT'
#bpy.ops.object.constraint_add(type='TRACK_TO')
#bpy.context.object.constraints["Track To"].target = Atlas
#bpy.context.object.constraints["Track To"].track_axis = 'TRACK_NEGATIVE_Z'
#bpy.context.object.constraints["Track To"].up_axis = 'UP_Y'

#Camera.constraint_add(type='TRACK_TO')
#Camera.constraints["Track To"].target = bpy.data.objects["ambmc2dsurqec_15micron_cut_mesh_1.023"]
#Camera.constraints["Track To"].target = Empty
#bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)


## Add colour and material to the meshes for visualization
deselect()

##Create Material for template
MatAtlas = bpy.data.materials.new(name="atlas_material")
MatAtlas.use_nodes=True
MatAtlas.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.199638, 0.199638, 0.199638, 1)
MatAtlas.blend_method='BLEND'
MatAtlas.shadow_method='NONE'
MatAtlas.node_tree.nodes["Principled BSDF"].inputs[18].default_value = 0.5
MatAtlas.node_tree.nodes["Principled BSDF"].inputs[5].default_value = 1
MatAtlas.node_tree.nodes["Principled BSDF"].inputs[7].default_value = 0.281818
# matNodes=MatAtlas.node_tree
# mixShader=matNodes.nodes.new('ShaderNodeMixShader')
# GlassNode=matNodes.nodes.new('ShaderNodeBsdfGlass')
# GlassNode.inputs[0].default_value = (0.5, 0.5, 0.5, 0.5)
# outNode=MatAtlas.node_tree.nodes['Material Output']
# matNodes.links.new(outNode.inputs[0],GlassNode.outputs[0])


#Prepare Materials for up to 2 meshes of the statistical maps
MatGenes = []
MatGenes.append(bpy.data.materials.new(name="gene_material_0"))
MatGenes.append(bpy.data.materials.new(name="gene_material_1"))
MatGenes.append(bpy.data.materials.new(name="gene_material_2"))

i = 0
for col in color:
	MatGenes[i].use_nodes=True
	MatGenes[i].node_tree.nodes["Principled BSDF"].inputs[0].default_value  = (col[0],col[1],col[2],1)
	MatGenes[i].node_tree.nodes["Principled BSDF"].inputs[4].default_value = 1

	i = i+1

#Apply colours
if Atlas.data.materials:
	# assign to 1st material slot
	Atlas.data.materials[0] = MatAtlas
else:
	# no slots
	Atlas.data.materials.append(MatAtlas)

i = 0
for stat_map in args.stat_map_path:
	if gene_data[i].data.materials:

		# assign to 1st material slot
		gene_data[i].data.materials[0] = MatGenes[i]

	else:
		# no slots
		gene_data[i].data.materials.append(MatGenes[i])

	i += 1


#Try to rotate camera around the brain and render different angles.

#for step in range(0, step_count):
#	origin.rotation_euler[2] = radians(step * (360.0 / step_count))
#
deselect()

#bpy.data.scenes["Scene"].view_settings.view_transform = 'Raw'
bpy.data.scenes["Scene"].camera = Camera

#bpy.data.scenes["Scene"].render.filepath = path + "/Pic1"
#bpy.ops.render.render( write_still=True )

Atlas.select_set(True)
for Gene in gene_data:
	Gene.select_set(True)
#bpy.ops.transform.rotate(value=1.21921, axis=(-0.00457997, 0.716912, -0.697148), constraint_axis=(False, False, False), constraint_orientation='GLOBAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)


## Set camera to point to Atlas
def look_at(obj_camera, point):
	loc_camera = Camera.location

	direction = point - loc_camera
	# point the cameras '-Z' and use its 'Y' as up
	rot_quat = direction.to_track_quat('-Z', 'Y')

	# assume we're using euler rotation
	obj_camera.rotation_euler = rot_quat.to_euler()


#Set camera to a specific location, render and save image
def take_pic_Loc(file_name,loc):
	Camera.location = loc
	deselect()
	Camera.select= True
	bpy.context.object.rotation_mode = 'XYZ'
	look_at(Camera,Atlas.location)
	#bpy.ops.transform.rotate(value=-3.14, constraint_axis=(True, False, False), constraint_orientation='LOCAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
	#bpy.ops.transform.rotate(value=3.14, axis=(0, 0, -1), constraint_axis=(False, False, False), constraint_orientation='GLOBAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
	bpy.context.scene.render.engine = 'CYCLES'
	bpy.context.scene.cycles.samples = 20
	bpy.context.scene.cycles.device = 'CPU'
	# bpy.context.scene.view_settings.view_transform = 'Standard'
	# bpy.context.scene.view_settings.look = 'Low Contrast'
	bpy.context.scene.world.light_settings.use_ambient_occlusion = True

	bpy.context.scene.view_settings.exposure = 1
	bpy.context.scene.render.film_transparent = True
	bpy.context.scene.render.image_settings.file_format = 'PNG'
	bpy.context.scene.render.image_settings.color_depth = '16'
	bpy.context.scene.render.image_settings.color_mode = 'RGBA'
	bpy.context.scene.render.resolution_x = 3000
	bpy.context.scene.render.resolution_y = 5250
	bpy.data.scenes["Scene"].render.filepath = path + "/" + file_name
	bpy.ops.render.render( write_still=True )

#render and save image
def take_pic(file_name):
	deselect()
	Camera.select_set(True)
	#bpy.ops.transform.rotate(value=-3.14, constraint_axis=(True, False, False), constraint_orientation='LOCAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
	#bpy.ops.transform.rotate(value=3.14, axis=(0, 0, -1), constraint_axis=(False, False, False), constraint_orientation='GLOBAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
	bpy.context.scene.render.engine = 'CYCLES'
	bpy.context.scene.cycles.samples = 20
	bpy.context.scene.cycles.device = 'CPU'
	# bpy.context.scene.view_settings.view_transform = 'Standard'
	# bpy.context.scene.view_settings.look = 'Low Contrast'
	bpy.context.scene.world.light_settings.use_ambient_occlusion = True

	bpy.context.scene.view_settings.exposure = 1
	bpy.context.scene.render.film_transparent = True
	bpy.context.scene.render.image_settings.file_format = 'PNG'
	bpy.context.scene.render.image_settings.color_mode = 'RGBA'
	bpy.context.scene.render.image_settings.color_depth = '16'
	bpy.context.scene.render.resolution_x = 4500
	bpy.context.scene.render.resolution_y = 5250
	bpy.context.scene.render.resolution_percentage = 50

	bpy.data.scenes["Scene"].render.filepath = path + "/" + file_name
	bpy.ops.render.render( write_still=True )


#Rotate mesh to view
deselect()
Atlas.select_set(True)
for Gene in gene_data:
	Gene.select_set(True)

Atlas.rotation_euler[0] = 1.8326
Atlas.rotation_euler[1] = 2.96706
Atlas.rotation_euler[2] = 0.698132

for Gene in gene_data:
	Gene.rotation_euler[0] = 1.8326
	Gene.rotation_euler[1] = 2.96706
	Gene.rotation_euler[2] = 0.698132

Camera.location = (0,-25,0)
Camera.rotation_euler[0] = 1.5708
Camera.rotation_euler[1] = -0
Camera.rotation_euler[2] = 0
Camera.scale[0]= 1
Camera.scale[1]= 1
Camera.scale[2]= 1

take_pic(args.filename)
