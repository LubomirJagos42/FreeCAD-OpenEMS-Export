# OpenEMS FDTD Analysis Automation Script
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

## switches & options
draw_3d_pattern = 0  # this may take a while...
use_pml = 0          # use pml boundaries instead of mur

currDir = os.getcwd()
print(currDir)

# setup_only : dry run to view geometry, validate settings, no FDTD computations
# num_threads : Number of threads to run or 0 to set openEMS decide
# debug_pec  : generated PEC skeleton (use ParaView to inspect)
debug_pec = False
setup_only = False
num_threads = 0

## prepare simulation folder
Sim_Path = os.path.join(currDir, 'simulation_output')
Sim_CSX = 'PlateCapacitor.xml'
if os.path.exists(Sim_Path):
	shutil.rmtree(Sim_Path)   # clear previous directory
	os.mkdir(Sim_Path)    # create empty simulation folder

## setup FDTD parameter & excitation function
max_timesteps = 1000000
min_decrement = 1e-05 # 10*log10(min_decrement) dB  (i.e. 1E-5 means -50 dB)
simulation_oversampling = 4
CSX = CSXCAD.ContinuousStructure()
FDTD = openEMS(NrTS=max_timesteps, EndCriteria=min_decrement, OverSampling=simulation_oversampling)
FDTD.SetCSX(CSX)

#######################################################################################################################################
# BOUNDARY CONDITIONS
#######################################################################################################################################
BC = ["PEC","PEC","PEC","PEC","PEC","PEC"]
FDTD.SetBoundaryCond(BC)

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
FDTD.SetGaussExcite(f0, fc)
max_res = physical_constants.C0 / (f0 + fc) / 20

#######################################################################################################################################
# MATERIALS AND GEOMETRY
#######################################################################################################################################
materialList = {}

## MATERIAL - Air
materialList['Air'] = CSX.AddMaterial('Air')

materialList['Air'].SetMaterialProperty(epsilon=1, mue=1)
materialList['Air'].AddPolyhedronReader(os.path.join(currDir,'WorldBox_gen_model.stl'), priority=9600).ReadFile()

## MATERIAL - CapacitorDielectric
materialList['CapacitorDielectric'] = CSX.AddMaterial('CapacitorDielectric')

materialList['CapacitorDielectric'].SetMaterialProperty(epsilon=3, mue=1)
materialList['CapacitorDielectric'].AddPolyhedronReader(os.path.join(currDir,'Dielectric_gen_model.stl'), priority=9900).ReadFile()

## MATERIAL - PEC
materialList['PEC'] = CSX.AddMetal('PEC')

materialList['PEC'].AddPolyhedronReader(os.path.join(currDir,'Plate1_gen_model.stl'), priority=9700).ReadFile()
materialList['PEC'].AddPolyhedronReader(os.path.join(currDir,'Plate2_gen_model.stl'), priority=9800).ReadFile()


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
# PORTS
#######################################################################################################################################
port = {}
portNamesAndNumbersList = {}
## PORT - port - Port
portStart = [ -0.25, -0.25, -0.5 ]
portStop  = [ 0.25, 0.25, 0.5 ]
portR = inf
portUnits = 1
portExcitationAmplitude = 1.0
portDirection = 'z'
port[1] = FDTD.AddLumpedPort(port_nr=1, R=portR*portUnits, start=portStart, stop=portStop, p_dir=portDirection, priority=10000, excite=1.0*portExcitationAmplitude)
portNamesAndNumbersList["Port"] = 1;

#######################################################################################################################################
# PROBES
#######################################################################################################################################
nf2ffBoxList = {}
dumpBoxList = {}
probeList = {}

# PROBE - EFieldDump - EFieldDump
dumpboxName = "EFieldDump_EFieldDump"
dumpboxType = 0
dumpBoxList[dumpboxName] = CSX.AddDump(dumpboxName, dump_type=dumpboxType)
dumpboxStart = [ -0, -10, -10 ]
dumpboxStop  = [ 0.01, 10, 10 ]
dumpBoxList[dumpboxName].AddBox(dumpboxStart, dumpboxStop )



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
# RUN
#######################################################################################################################################
### Run the simulation
CSX_file = os.path.join(Sim_Path, Sim_CSX)
if not os.path.exists(Sim_Path):
	os.mkdir(Sim_Path)
CSX.Write2XML(CSX_file)
from CSXCAD import AppCSXCAD_BIN
os.system(AppCSXCAD_BIN + ' "{}"'.format(CSX_file))

if setup_only == False:
	FDTD.Run(Sim_Path, verbose=3, cleanup=True, setup_only=setup_only, debug_pec=debug_pec, numThreads=num_threads)
