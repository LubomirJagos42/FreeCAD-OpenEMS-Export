# Plot S11
#
# To be run with python.
# FreeCAD to OpenEMS plugin by Lubomir Jagos, 
# see https://github.com/LubomirJagos/FreeCAD-OpenEMS-Export
#
# This file has been automatically generated. Manual changes may be overwritten.
#
### Import Libraries
import math
import numpy as np
import os, tempfile, shutil
import csv
import CSXCAD
from openEMS import openEMS
from openEMS import physical_constants

#
# FUNCTION TO CONVERT CARTESIAN TO CYLINDRICAL COORDINATES
#     returns coordinates in order [theta, r, z]
#
def cart2pol(pointCoords):
	theta = np.arctan2(pointCoords[1], pointCoords[0])
	r = np.sqrt(pointCoords[0] ** 2 + pointCoords[1] ** 2)
	z = pointCoords[2]
	return theta, r, z

#
# FUNCTION TO GIVE RANGE WITH ENDPOINT INCLUDED arangeWithEndpoint(0,10,2.5) = [0, 2.5, 5, 7.5, 10]
#     returns coordinates in order [theta, r, z]
#
def arangeWithEndpoint(start, stop, step=1, endpoint=True):
	if start == stop:
		return [start]

	arr = np.arange(start, stop, step)
	if endpoint and arr[-1] + step == stop:
		arr = np.concatenate([arr, [stop]])
	return arr

# Change current path to script file folder
#
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
## constants
unit    = 0.001 # Model coordinates and lengths will be specified in mm.
fc_unit = 0.001 # STL files are exported in FreeCAD standard units (mm).

currDir = os.getcwd()
Sim_Path = os.path.join(currDir, r'simulation_output')
print(currDir)

## setup FDTD parameter & excitation function
max_timesteps = 1000000
min_decrement = 1e-05 # 10*log10(min_decrement) dB  (i.e. 1E-5 means -50 dB)
simulation_oversampling = 4
CSX = CSXCAD.ContinuousStructure()
FDTD = openEMS(NrTS=max_timesteps, EndCriteria=min_decrement, OverSampling=simulation_oversampling)
FDTD.SetCSX(CSX)

#######################################################################################################################################
# COORDINATE SYSTEM
#######################################################################################################################################
def mesh():
	x,y,z

def smoothMesh():
	x,y,z

mesh.x = np.array([]) # mesh variable initialization (Note: x y z implies type Cartesian).
mesh.y = np.array([])
mesh.z = np.array([])

openEMS_grid = CSX.GetGrid()
openEMS_grid.SetDeltaUnit(unit) # First call with empty mesh to set deltaUnit attribute.

#######################################################################################################################################
# EXCITATION Ex
#######################################################################################################################################
f0 = 1.0*1000000000.0
fc = 0.5*1000000000.0
max_res = physical_constants.C0 / (f0 + fc) / 20

#######################################################################################################################################
# MATERIALS AND GEOMETRY
#######################################################################################################################################
materialList = {}

#######################################################################################################################################
# GRID LINES
#######################################################################################################################################

## GRID - AirGrid - WorldBox (Smooth Mesh)
smoothMesh.x = [-10.000000000000005,10.000000000000005];
smoothMesh.x = CSXCAD.SmoothMeshLines.SmoothMeshLines(smoothMesh.x, 0.5)
mesh.x = np.concatenate((mesh.x, smoothMesh.x))
smoothMesh.y = [-10.000000000000009,10.000000000000009];
smoothMesh.y = CSXCAD.SmoothMeshLines.SmoothMeshLines(smoothMesh.y, 0.5)
mesh.y = np.concatenate((mesh.y, smoothMesh.y))
smoothMesh.z = [-10.000000000000009,10.000000000000009];
smoothMesh.z = CSXCAD.SmoothMeshLines.SmoothMeshLines(smoothMesh.z, 0.5)
mesh.z = np.concatenate((mesh.z, smoothMesh.z))

## GRID - PlateGrid - Plate1 (Smooth Mesh)
## GRID - PlateGrid - Plate2 (Smooth Mesh)
smoothMesh.x = [-5.000000000000002,-5.000000000000001,5.000000000000001,5.000000000000002];
smoothMesh.x = CSXCAD.SmoothMeshLines.SmoothMeshLines(smoothMesh.x, 0.2)
mesh.x = np.concatenate((mesh.x, smoothMesh.x))
smoothMesh.y = [-5.000000000000003,-5.000000000000003,5.000000000000003,5.000000000000003];
smoothMesh.y = CSXCAD.SmoothMeshLines.SmoothMeshLines(smoothMesh.y, 0.2)
mesh.y = np.concatenate((mesh.y, smoothMesh.y))
smoothMesh.z = [-1.500000000000004,-0.499999999999997,0.499999999999997,1.500000000000004];
smoothMesh.z = CSXCAD.SmoothMeshLines.SmoothMeshLines(smoothMesh.z, 0.2)
mesh.z = np.concatenate((mesh.z, smoothMesh.z))

openEMS_grid.AddLine('x', mesh.x)
openEMS_grid.AddLine('y', mesh.y)
openEMS_grid.AddLine('z', mesh.z)


#######################################################################################################################################
# MINIMAL GRIDLINES SPACING, removing gridlines which are closer as defined in GUI
#######################################################################################################################################
def removeMeshLines(meshLines, minDistance):
	resultMesh = [meshLines[0]]

	for val in meshLines[1:]:
		if all(abs(val - f) >= minDistance for f in resultMesh):
			resultMesh.append(val)

	return np.array(resultMesh)

mesh.x = openEMS_grid.GetLines("x", True)
mesh.y = openEMS_grid.GetLines("y", True)
mesh.z = openEMS_grid.GetLines("z", True)

openEMS_grid.ClearLines("x")
openEMS_grid.ClearLines("y")
openEMS_grid.ClearLines("z")

mesh.x = np.sort(mesh.x)
mesh.y = np.sort(mesh.y)
mesh.z = np.sort(mesh.z)

mesh.x = np.unique(mesh.x)
mesh.y = np.unique(mesh.y)
mesh.z = np.unique(mesh.z)

mesh.x = removeMeshLines(mesh.x, 0.001000000000000)
mesh.y = removeMeshLines(mesh.y, 0.001000000000000)
mesh.z = removeMeshLines(mesh.z, 0.001000000000000)

openEMS_grid.AddLine('x', mesh.x)
openEMS_grid.AddLine('y', mesh.y)
openEMS_grid.AddLine('z', mesh.z)
#######################################################################################################################################
# PORTS
#######################################################################################################################################
port = {}
portNamesAndNumbersList = {}
## PORT - port - Port
portStart = [ -0.25, -0.25, -0.5 ]
portStop  = [ 0.25, 0.25, 0.5 ]
portR = 50.0
portUnits = 1
portExcitationAmplitude = 10.0
portDirection = 'z'
port[1] = FDTD.AddLumpedPort(port_nr=1, R=portR*portUnits, start=portStart, stop=portStop, p_dir=portDirection, priority=10000, excite=1.0*portExcitationAmplitude)
portNamesAndNumbersList["Port"] = 1;

## postprocessing & do the plots
freq = np.linspace(max(1e6,f0-fc), f0+fc, 501)
port[1].CalcPort(Sim_Path, freq)

Zin = port[1].uf_tot / port[1].if_tot
s11 = port[1].uf_ref / port[1].uf_inc
s11_dB = 20.0*np.log10(np.abs(s11))

#
#   Write S11, real and imag Z_in into CSV file separated by ';'
#
filename = 'openEMS_simulation_s11_dB.csv'

with open(filename, 'w', newline='') as csvfile:
	writer = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
	writer.writerow(['freq (MHz)', 's11 (dB)', 'real Z_in', 'imag Z_in', 'Z_in total'])
	writer.writerows(np.array([
		(freq/1e6),
		s11_dB,
		np.real(Zin),
		np.imag(Zin),
		np.abs(Zin)
	]).T) #creates array with 1st row frequencies, 2nd row S11, ... and transpose it
