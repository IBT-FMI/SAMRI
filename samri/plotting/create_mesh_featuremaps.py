import sys
from glob import glob
import skimage
from skimage import measure
import nibabel
import numpy
import os
from math import floor
import argparse

def f(i, j, k, affine):
	"""
	Returns affine transformed coordinates (i,j,k) -> (x,y,z) Use to set correct coordinates and size for the mesh.
	
	Parameters:
	-----------
	i,j,k : int
		Integer coordinates of points in 3D space to be transformed.
	affine : array
		4x4 matrix containing affine transformation information of Nifti-Image.
	
	Returns:
	--------
	x,y,z : int
		Affine transformed coordinates of input points.
	
	"""

	M = affine[:3, :3]
	abc = affine[:3, 3]
	return M.dot([i, j, k]) + abc

#Writes an .obj file for the output of marching cube algorithm. Specify affine if needed in mesh. One = True for faces indexing starting at 1 as opposed to 0. Necessary for Blender/SurfIce
def write_obj(name,verts,faces,normals,values,affine=None,one=False):
	"""
	Write a .obj file for the output of marching cube algorithm.

	Parameters:
	-----------
	name : str
		Ouput file name.
	verts : array
		Spatial coordinates for vertices as returned by skimage.measure.marching_cubes_lewiner().
	faces : array
		List of faces, referencing indices of verts as returned by skimage.measure.marching_cubes_lewiner().
	normals : array
		Normal direction of each vertex as returned by skimage.measure.marching_cubes_lewiner().
	affine : array,optional
		If given, vertices coordinates are affine transformed to create mesh with correct origin and size.
	one : bool
		Specify if faces values should start at 1 or at 0. Different visualization programs use different conventions.
	
	"""
	if (one) : faces=faces+1
	thefile = open(name,'w')
	if affine is not None:
		for item in verts:
			transformed = f(item[0],item[1],item[2],affine)
			thefile.write("v {0} {1} {2}\n".format(transformed[0],transformed[1],transformed[2]))
	else :
		for item in verts:
			thefile.write("v {0} {1} {2}\n".format(item[0],item[1],item[2]))
	print("File written 30%")
	for item in normals:
		thefile.write("vn {0} {1} {2}\n".format(item[0],item[1],item[2]))
	print("File written 60%")
	for item in faces:
		thefile.write("f {0}//{0} {1}//{1} {2}//{2}\n".format(item[0],item[1],item[2]))
	thefile.close()

def create_mesh(stat_map,threshold,one=True,pos_values=False):
	##TODO: stat_map also possibly alread a Nifit1Image, adjust
	img= nibabel.load(stat_map)
	img_data = img.get_fdata()
	neg = False
	print(threshold)
	#all negative values
	if (numpy.max(img_data)<= 0):
		img_data = numpy.absolute(img_data)
		neg = True
	#run marching cube
	verts, faces, normals, values = measure.marching_cubes_lewiner(img_data,threshold)

	#save mesh as .obj
	filename = os.path.basename(stat_map)
	filename_prefix = filename.split(".")[0]
	path = "/var/tmp/"
	output_file = filename_prefix + "_pos_mesh.obj"
	if neg: output_file = filename_prefix + "_neg_mesh.obj"
	output_path = os.path.join(path,output_file)
	write_obj(output_path,verts,faces,normals,values,affine = img.affine,one=one)

	#create mesh for negative clusters if present
	if numpy.min(img_data) < 0 and pos_values == False and neg == False:
		img_data[img_data > 0] = 0
		img_data = numpy.absolute(img_data)
		verts, faces, normals, values = measure.marching_cubes_lewiner(img_data,threshold)
		output_file_neg = filename_prefix + "neg_mesh.obj"
		output_path_neg = os.path.join(path,output_file_neg)
		write_obj(output_path_neg,verts,faces,normals,values,affine = img.affine,one=one)
	else:
		output_path_neg = None

	return output_path,output_path_neg


def main():
	parser = argparse.ArgumentParser(description="Create surface mesh form nifti-volume",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('--threshold','-t',default=1,type=float)
	parser.add_argument('--stat_map','-i',type=str)
	args = parser.parse_args()
	create_mesh(args.stat_map,args.threshold,one = True)
    
if __name__ == '__main__': main()
