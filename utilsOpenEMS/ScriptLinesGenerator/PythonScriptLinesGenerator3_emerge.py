#   author: Lubomir Jagos
#
#
import os
from PySide import QtGui, QtCore, QtWidgets
import numpy as np
import re
import math

from utilsOpenEMS.GlobalFunctions.GlobalFunctions import _bool, _r, _r2
from utilsOpenEMS.ScriptLinesGenerator.OctaveScriptLinesGenerator2 import OctaveScriptLinesGenerator2
from utilsOpenEMS.GuiHelpers.GuiHelpers import GuiHelpers
from utilsOpenEMS.GuiHelpers.FactoryCadInterface import FactoryCadInterface

from utilsOpenEMS.ScriptLinesGenerator.CommonScriptLinesGenerator import CommonScriptLinesGenerator
from utilsOpenEMS.ScriptLinesGenerator.PythonScriptLinesGenerator2_openems import PythonScriptLinesGenerator2_openems


class PythonScriptLinesGenerator3_emerge(PythonScriptLinesGenerator2_openems):

    #
    #   constructor, get access to form GUI
    #
    def __init__(self, form, statusBar = None):
        super(PythonScriptLinesGenerator3_emerge, self).__init__(form, statusBar)
        self.portBoundaryConditionScriptLinesBuffer = []
        self.createdObjectNameList = []
        self.createdObjectBoundaryNameList = []

        self.cadHelpers = FactoryCadInterface.createHelper()

    def getCoordinateSystemScriptLines(self):
        genScript = ""

        genScript += "#######################################################################################################################################\n"
        genScript += "# COORDINATE SYSTEM\n"
        genScript += "#######################################################################################################################################\n"

        """ # Till now not used, just using rectangular coordination type, cylindrical MUST BE IMPLEMENTED!
        gridCoordsType = self.getModelCoordsType()
        if (gridCoordsType == "rectangular"):
            genScript += "CSX = InitCSX('CoordSystem',0); # Cartesian coordinate system.\n"
        elif (gridCoordsType == "cylindrical"):
            genScript += "CSX = InitCSX('CoordSystem',1); # Cylindrical coordinate system.\n"
        else:
            genScript += "%%%%%% ERROR GRID COORDINATION SYSTEM TYPE UNKNOWN"				
        """

        genScript += "def mesh():\n"
        genScript += "\tx,y,z\n"
        genScript += "\n"
        genScript += "mesh.x = np.array([]) # mesh variable initialization (Note: x y z implies type Cartesian).\n"
        genScript += "mesh.y = np.array([])\n"
        genScript += "mesh.z = np.array([])\n"
        genScript += "\n"
        genScript += "openEMS_grid = CSX.GetGrid()\n"
        genScript += "openEMS_grid.SetDeltaUnit(unit) # First call with empty mesh to set deltaUnit attribute.\n"
        genScript += "\n"

        return genScript

    def getMaterialDefinitionsScriptLines(self, items, outputDir=None, generateObjects=True):
        genScript = ""

        genScript += "#######################################################################################################################################\n"
        genScript += "# MATERIALS AND GEOMETRY\n"
        genScript += "#######################################################################################################################################\n"

        # PEC is created by default due it's used when microstrip port is defined, so it's here to have it here.
        # Note that the user will need to create a metal named 'PEC' and populate it to avoid a warning
        # about "no primitives assigned to metal 'PEC'".
        genScript += "materialList = {}\n"                              # !!!THIS IS ON PURPOSE NOT LITERAL {} brackets are generated into code for python
        genScript += "\n"

        if not items:
            return genScript

        materialCounter = -1    #increment of this variable is at beginning f for loop so start at 0
        simObjectCounter = 0

        # now export material children, if it's object export as STL, if it's curve export as curve
        if (generateObjects):
            for [item, currSetting] in items:

                #
                #   Materials are stored in variables in python script, so this is counter to create universal name ie. material_1, material_2, ...
                #
                materialCounter += 1

                print(currSetting)
                if (currSetting.getName() == 'Material Default'):
                    print("#Material Default")
                    print("---")
                    continue

                print("#")
                print("#MATERIAL")
                print("#name: " + currSetting.getName())
                print("#epsilon, mue, tand, sigma")
                print("#" + str(currSetting.constants['epsilon']) + ", " + str(currSetting.constants['mue']) + ", " + str(currSetting.constants['kappa']) + ", " + str(currSetting.constants['sigma']))

                genScript += f"## MATERIAL - {currSetting.getName()}\n"
                materialPythonVariable = f"materialList['{currSetting.getName()}']"

                if (currSetting.type == 'metal'):
                    #this is working, same as in lib
                    # genScript += f"{materialPythonVariable} = em.Material(name='{currSetting.getName()}', _metal=True, cond=1e30)\n"

                    #using predefined library with materials
                    genScript += f"{materialPythonVariable} = em.lib.PEC\n"

                    self.internalMaterialIndexNamesList[currSetting.getName()] = materialPythonVariable
                elif (currSetting.type == 'userdefined'):
                    self.internalMaterialIndexNamesList[currSetting.getName()] = materialPythonVariable

                    smp_args = []
                    if str(currSetting.constants['epsilon']) != "0":
                        smp_args.append(f"er={str(currSetting.constants['epsilon'])}")
                    if str(currSetting.constants['mue']) != "0":
                        smp_args.append(f"ur={str(currSetting.constants['mue'])}")
                    if ("tand" in currSetting.constants) \
                       and type(currSetting.constants['tand']) is float:
                            smp_args.append(f"tand={str(currSetting.constants['tand'])}")
                    if str(currSetting.constants['sigma']) != "0":
                        smp_args.append(f"cond={str(currSetting.constants['sigma'])}")

                    genScript += f"{materialPythonVariable} = em.Material(name='{currSetting.getName()}', " + ", ".join(smp_args) + ")\n"

                # first print all current material children names
                for k in range(item.childCount()):
                    childName = item.child(k).text(0)
                    print("##Children:")
                    print("\t" + childName)

                # now export material children, if it's object export as STL, if it's curve export as curve
                for k in range(item.childCount()):
                    simObjectCounter += 1               #counter for objects
                    childName = item.child(k).text(0)

                    self.createdObjectNameList.append(childName)    #add this object into list of created objects which will be used to create named group in exported mesh

                    #
                    #	getting item priority
                    #
                    objModelPriorityItemName = item.parent().text(0) + ", " + item.text(0) + ", " + childName
                    objModelPriority = self.getItemPriority(objModelPriorityItemName)

                    # getting reference to FreeCAD object
                    freeCadObj = [i for i in self.cadHelpers.getObjects() if (i.Label) == childName][0]

                    #
                    #   Set color of material by object, this can overwite it color multiple time, what to do, good enough for now
                    #
                    colorStr = ""
                    colorTuple = freeCadObj.ViewObject.DiffuseColor[0]
                    colorStr += "#" + format(int(255 * colorTuple[0]), '02x') + format(int(255 * colorTuple[1]), '02x') + format(int(255 * colorTuple[2]), '02x')
                    genScript += f"{materialPythonVariable}.color = '{colorStr}'\n"
                    genScript += f"{materialPythonVariable}.opacity = {1.0 - freeCadObj.ViewObject.Transparency}\n"
                    genScript += f"\n"

                    #
                    #   HERE IS OBJECT GENERATOR THERE ARE FEW SPECIAL CASES WHICH ARE HANDLED FIRST AND IF OBJECT IS NORMAL STRUCTURE AT THE END IS GENERATED AS .stl FILR:
                    #       - conducting sheet = just plane is generated, in case of 3D object shell of object bounding box is generated
                    #       - discretized edge = curve from line is generated
                    #       - sketch           = curve is generated from its vertices
                    #
                    if (currSetting.type == 'conducting sheet'):
                        #
                        #   Here comes object generator for conducting sheet. It's possible to define it as plane in XY, XZ, YZ plane in cartesian coords and XY plane in cylindrical coords.
                        #   So in case of conducting sheet no .stl is generated, it will be generated rectangle based on bounding box.
                        #
                        genScript += "##conducting sheet object\n"
                        genScript += f"#object Label: {freeCadObj.Label}\n"
                        bbCoords = freeCadObj.Shape.BoundBox

                        if (freeCadObj.Name.find("Sketch") > -1):
                            #
                            # If object is sketch then it's added as it outline
                            #

                            normDir, elevation, points = self.getSketchPointsForConductingSheet(freeCadObj)
                            if not normDir.startswith("ERROR"):
                                genScript += "points = [[],[]]\n"
                                if len(points[0])  == 0:
                                    genScript += "## ERROR, no points for polygon for conducting sheet nothing generated"
                                else:
                                    for k in range(len(points[0])):
                                        genScript += f"points[0].append({points[0][k]})\n"
                                        genScript += f"points[1].append({points[1][k]})\n"
                                genScript += "\n"

                                genScript += f"{materialPythonVariable}.AddPolygon(points, '{normDir}', {elevation}, priority={objModelPriority})\n"
                                genScript += "\n"
                                print("material conducting sheet: polygon into conducting sheet added.")
                            else:
                                genScript += f"## {normDir}\n"
                                genScript += "\n"
                                print("ERROR: material conducting sheet: " + normDir)

                        elif (_r(bbCoords.XMin) == _r(bbCoords.XMax) or _r(bbCoords.YMin) == _r(bbCoords.YMax) or _r(bbCoords.ZMin) == _r(bbCoords.ZMax)):
                            #
                            # Adding planar object into conducting sheet, if it consists from faces then each face is added as polygon.
                            #

                            normDir, elevation, facesList = self.getFacePointsForConductingSheet(freeCadObj)
                            if normDir != "":
                                for face in facesList:
                                    genScript += f"points = [[],[]]\n"
                                    for pointIndex in range(len(face[0])):
                                        genScript += f"points[0].append({face[0][pointIndex]})\n"
                                        genScript += f"points[1].append({face[1][pointIndex]})\n"
                                        genScript += "\n"
                                    genScript += f"{materialPythonVariable}.AddPolygon(points, '{normDir}', {elevation}, priority={objModelPriority})\n"
                                    genScript += "\n"
                            else:
                                genScript += f"#\tObject has no faces, conducting sheet is generated based on object bounding box since it's planar.\n"
                                genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMin)},{_r(bbCoords.YMin)},{_r(bbCoords.ZMin)}], [{_r(bbCoords.XMax)},{_r(bbCoords.YMax)},{_r(bbCoords.ZMax)}], priority={objModelPriority})\n"
                                genScript += "\n"

                        else:
                            #
                            # If object is 3D object then it's boundaries are added as conducting sheets.
                            #

                            genScript += f"#\tObject is 3D so there are sheets on its boundary box generated.\n"
                            genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMin)}, {_r(bbCoords.YMin)}, {_r(bbCoords.ZMin)}], [{_r(bbCoords.XMax)}, {_r(bbCoords.YMax)}, {_r(bbCoords.ZMin)}], priority={objModelPriority})\n"
                            genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMin)}, {_r(bbCoords.YMin)}, {_r(bbCoords.ZMin)}], [{_r(bbCoords.XMax)}, {_r(bbCoords.YMin)}, {_r(bbCoords.ZMax)}], priority={objModelPriority})\n"
                            genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMin)}, {_r(bbCoords.YMin)}, {_r(bbCoords.ZMin)}], [{_r(bbCoords.XMin)}, {_r(bbCoords.YMax)}, {_r(bbCoords.ZMax)}], priority={objModelPriority})\n"
                            genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMin)}, {_r(bbCoords.YMin)}, {_r(bbCoords.ZMax)}], [{_r(bbCoords.XMax)}, {_r(bbCoords.YMax)}, {_r(bbCoords.ZMax)}], priority={objModelPriority})\n"
                            genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMin)}, {_r(bbCoords.YMax)}, {_r(bbCoords.ZMin)}], [{_r(bbCoords.XMax)}, {_r(bbCoords.YMax)}, {_r(bbCoords.ZMax)}], priority={objModelPriority})\n"
                            genScript += f"{materialPythonVariable}.AddBox([{_r(bbCoords.XMax)}, {_r(bbCoords.YMin)}, {_r(bbCoords.ZMin)}], [{_r(bbCoords.XMax)}, {_r(bbCoords.YMax)}, {_r(bbCoords.ZMax)}], priority={objModelPriority})\n"
                            genScript += "\n"

                    elif (freeCadObj.Name.find("Discretized_Edge") > -1):
                        #
                        #	Adding discretized curve
                        #

                        curvePoints = freeCadObj.Points
                        genScript += "points = [[],[],[]]\n"
                        for k in range(0, len(curvePoints)):
                            genScript += f"points[0].append({_r(curvePoints[k].x)})\n"
                            genScript += f"points[1].append({_r(curvePoints[k].y)})\n"
                            genScript += f"points[2].append({_r(curvePoints[k].z)})\n"
                            genScript += "\n"

                        genScript += f"{materialPythonVariable}.AddCurve(points, priority={objModelPriority})\n"
                        genScript += "\n"
                        print("Curve added to generated script using its points.")

                    elif (freeCadObj.Name.find("Sketch") > -1):
                        #
                        #	Adding JUST LINE SEGMENTS FROM SKETCH, THIS NEED TO BE IMPROVED TO PROPERLY GENERATE CURVE FROM SKETCH,
                        #	there can be circle, circle arc and maybe something else in sketch geometry
                        #

                        genScript += "points = [[],[],[]]\n"

                        """
                        # WRONG SINCE StartPoint, EndPoint are defined in XY and not in absolute coordinates
                        for geometryObj in freeCadObj.Geometry:
                            if (str(type(geometryObj)).find("LineSegment") > -1):
                                genScript += f"points[0].append({geometryObj.StartPoint.x})\n"
                                genScript += f"points[1].append({geometryObj.StartPoint.y})\n"
                                genScript += f"points[2].append({geometryObj.StartPoint.z})\n"

                                genScript += f"points[0].append({geometryObj.EndPoint.x})\n"
                                genScript += f"points[1].append({geometryObj.EndPoint.y})\n"
                                genScript += f"points[2].append({geometryObj.EndPoint.z})\n"

                                genScript += "\n"
                        """

                        for v in freeCadObj.Shape.OrderedVertexes:
                            genScript += f"points[0].append({_r(v.X)})\n"
                            genScript += f"points[1].append({_r(v.Y)})\n"
                            genScript += f"points[2].append({_r(v.Z)})\n"
                            genScript += "\n"

                        #   HERE IS MADE ASSUMPTION THAT:
                        #       We suppose in sketch there are no mulitple closed sketches
                        #
                        #   Add first vertex into list
                        #
                        v = freeCadObj.Shape.OrderedVertexes[0]
                        if len(freeCadObj.OpenVertices) == 0:
                            genScript += f"points[0].append({_r(v.X)})\n"
                            genScript += f"points[1].append({_r(v.Y)})\n"
                            genScript += f"points[2].append({_r(v.Z)})\n"
                            genScript += "\n"

                        genScript += f"{materialPythonVariable}.AddCurve(points, priority={objModelPriority})\n"
                        genScript += "\n"
                        print("Line segments from sketch added.")

                    elif freeCadObj.Name.startswith('Sphere'):
                        bbox = freeCadObj.Shape.BoundBox

                        radius = max(
                            bbox.XMax - bbox.XMin,
                            bbox.YMax - bbox.YMin,
                            bbox.ZMax - bbox.ZMin
                        ) / 2.0

                        # Get center
                        position = (
                            (bbox.XMin + bbox.XMax) / 2,
                            (bbox.YMin + bbox.YMax) / 2,
                            (bbox.ZMin + bbox.ZMax) / 2
                        )

                        cadLengthUnit = self.getFreeCADInternalUnitLengthStr()
                        genScript += f"position = {str(position)}\n"
                        genScript += f"position = tuple([x*{cadLengthUnit} for x in position])\n"
                        genScript += f"newSphereObj = em.geo.Sphere(radius={str(radius)}*{cadLengthUnit}, position=position)\n"
                        genScript += f"newSphereObj.give_name('{freeCadObj.Label}')\n"
                        genScript += f"newSphereObj.name = '{freeCadObj.Label}'\n"
                        genScript += f"newSphereObj.prio_set({objModelPriority})\n"

                    else:
                        #
                        #   Going through each concrete material items and generate their .step files
                        #
                        currDir, baseName = self.getCurrDir()
                        stepModelFileName = childName + "_gen_model.step"
                        genScript += f"stepObjectGroup = em.geo.step.STEPItems(name='{childName}', filename=os.path.join(currDir,'{stepModelFileName}'), unit=mm)\n"
                        genScript += f"for geoObj in stepObjectGroup.objects:\n"
                        genScript += f"\tgeoObj.prio_set({objModelPriority})\n"
                        genScript += f"\tgeoObj.set_material({materialPythonVariable})\n"

                        #output directory path construction, if there is no parameter for output dir then output is in current freecad file dir
                        if (not outputDir is None):
                            exportFileName = os.path.join(outputDir, stepModelFileName)
                        else:
                            exportFileName = os.path.join(currDir, stepModelFileName)

                        self.cadHelpers.exportSTEP([freeCadObj], exportFileName)
                        print("Material object exported as STEP into: " + stepModelFileName)

                genScript += "\n"   #newline after each COMPLETE material category code generated

            genScript += "\n"

        return genScript

    def getBoundaryConditionObjectImportScriptLines(self, items, outputDir=None, generateObjects=True):
        genScript = ""

        genScript += "# Imported objects used as boundary conditions\n"
        genScript += "#\n"
        genScript += "\n"

        # now export material children, if it's object export as STL, if it's curve export as curve
        for [item, currSetting] in items:

            # first print all current material children names
            for k in range(item.childCount()):
                childName = item.child(k).text(0)
                print("##Children:")
                print("\t" + childName)

            # now export material children, if it's object export as STL, if it's curve export as curve
            for k in range(item.childCount()):
                childName = item.child(k).text(0)

                self.createdObjectBoundaryNameList.append(childName)  # add this object into list of created objects which will be used to create named group in exported mesh

                #
                #	getting item priority
                #
                objModelPriorityItemName = item.parent().text(0) + ", " + item.text(0) + ", " + childName
                objModelPriority = self.getItemPriority(objModelPriorityItemName)

                # getting reference to FreeCAD object
                freeCadObj = [i for i in self.cadHelpers.getObjects() if (i.Label) == childName][0]

                if freeCadObj.Name.startswith('Sphere'):
                    bbox = freeCadObj.Shape.BoundBox

                    radius = max(
                        bbox.XMax - bbox.XMin,
                        bbox.YMax - bbox.YMin,
                        bbox.ZMax - bbox.ZMin
                    ) / 2.0

                    # Get center
                    position = (
                        (bbox.XMin + bbox.XMax) / 2,
                        (bbox.YMin + bbox.YMax) / 2,
                        (bbox.ZMin + bbox.ZMax) / 2
                    )

                    cadLengthUnit = self.getFreeCADInternalUnitLengthStr()
                    genScript += f"position = {str(position)}\n"
                    genScript += f"position = tuple([x*{cadLengthUnit} for x in position])\n"
                    genScript += f"newSphereObj = em.geo.Sphere(radius={str(radius)}*{cadLengthUnit}, position=position)\n"
                    genScript += f"newSphereObj.give_name('{freeCadObj.Label}')\n"
                    genScript += f"newSphereObj.name = '{freeCadObj.Label}'\n"
                    genScript += f"newSphereObj.prio_set({objModelPriority})\n"

                else:
                    #
                    #   Going through each concrete material items and generate their .step files
                    #
                    currDir, baseName = self.getCurrDir()
                    stepModelFileName = childName + "_gen_model.step"
                    genScript += f"stepObjectGroup = em.geo.step.STEPItems(name='{childName}', filename=os.path.join(currDir,'{stepModelFileName}'), unit=mm)\n"
                    genScript += f"for geoObj in stepObjectGroup.objects:\n"
                    genScript += f"\tgeoObj.prio_set({objModelPriority})\n"

                    #output directory path construction, if there is no parameter for output dir then output is in current freecad file dir
                    if (not outputDir is None):
                        exportFileName = os.path.join(outputDir, stepModelFileName)
                    else:
                        exportFileName = os.path.join(currDir, stepModelFileName)

                    self.cadHelpers.exportSTEP([freeCadObj], exportFileName)
                    print("Boundary condition object exported as STEP into: " + stepModelFileName)

            genScript += "\n"   #newline after each COMPLETE material category code generated

        return genScript

    def getCartesianOrCylindricalScriptLinesFromStartStop(self, bbCoords, startPointName=None, stopPointName=None):
        genScript = "";
        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        strPortCoordsCartesianToCylindrical = ""
        strPortCoordsCartesianToCylindrical += "[generatedAuxTheta, generatedAuxR, generatedAuxZ] = cart2pol(portStart);\n"
        strPortCoordsCartesianToCylindrical += "portStart = [generatedAuxR, generatedAuxTheta, generatedAuxZ];\n"
        strPortCoordsCartesianToCylindrical += "[generatedAuxTheta, generatedAuxR, generatedAuxZ] = cart2pol(portStop);\n"
        strPortCoordsCartesianToCylindrical += "portStop = [generatedAuxR, generatedAuxTheta, generatedAuxZ];\n"

        if (self.getModelCoordsType() == "cylindrical"):
            # CYLINDRICAL COORDINATE TYPE USED
            if ((bbCoords.XMin <= 0 and bbCoords.YMin <= 0 and bbCoords.XMax >= 0 and bbCoords.YMax >= 0) or
                (bbCoords.XMin >= 0 and bbCoords.YMin >= 0 and bbCoords.XMax <= 0 and bbCoords.YMax <= 0)
            ):
                if (_r2(bbCoords.XMin) == _r2(bbCoords.XMax) or _r2(bbCoords.YMin) == _r2(bbCoords.YMax)):
                    #
                    #   Object is thin it's plane or line crossing origin
                    #
                    radius1 = -math.sqrt((sf * bbCoords.XMin) ** 2 + (sf * bbCoords.YMin) ** 2)
                    theta1 = math.atan2(bbCoords.YMin, bbCoords.XMin)
                    radius2 = math.sqrt((sf * bbCoords.XMax) ** 2 + (sf * bbCoords.YMax) ** 2)

                    genScript += 'portStart = [{0:g}, {1:g}, {2:g}]\n'.format(_r(radius1), _r(theta1), _r(sf * bbCoords.ZMin))
                    genScript += 'portStop = [{0:g}, {1:g}, {2:g}]\n'.format(_r(radius2), _r(theta1), _r(sf * bbCoords.ZMax))
                    genScript += '\n'
                else:
                    #
                    # origin [0,0,0] is contained inside boundary box, so now must used theta 0-360deg
                    #
                    radius1 = math.sqrt((sf * bbCoords.XMin) ** 2 + (sf * bbCoords.YMin) ** 2)
                    radius2 = math.sqrt((sf * bbCoords.XMax) ** 2 + (sf * bbCoords.YMax) ** 2)

                    genScript += 'portStart = [ 0, -math.pi, {0:g} ]\n'.format(_r(sf * bbCoords.ZMin))
                    genScript += 'portStop  = [ {0:g}, math.pi, {1:g} ]\n'.format(_r(max(radius1, radius2)), _r(sf * bbCoords.ZMax))
                    genScript += '\n'
            else:
                #
                # port is lying outside origin
                #
                genScript += 'portStart = [ {0:g}, {1:g}, {2:g} ]\n'.format(_r(sf * bbCoords.XMin),
                                                                             _r(sf * bbCoords.YMin),
                                                                             _r(sf * bbCoords.ZMin))
                genScript += 'portStop  = [ {0:g}, {1:g}, {2:g} ]\n'.format(_r(sf * bbCoords.XMax),
                                                                             _r(sf * bbCoords.YMax),
                                                                             _r(sf * bbCoords.ZMax))
                genScript += strPortCoordsCartesianToCylindrical

                if (bbCoords.YMin <= 0 and bbCoords.YMax >= 0):
                    #
                    #   special case when planar object lays on X axis like in Y+ and Y- in this case theta is generated:
                    #       -pi for start point
                    #       +pi for stop point
                    #   therefore to correct this since theta is in range -pi..+pi I have to add 360deg so +2*pi for start point will get it right as it should be
                    #

                    #18th June - LuboJ - commented this hack, it's causing problems, theta mas be <-2*pi. 2*pi> if it's more there is some positioning problem, for now disabled, need to be RETHINK AGAIN!
                    #   - issue observed using octave script, disabled for python also
                    #genScript += f"portStart[1] += 2*math.pi\n"
                    pass

        else:
            # CARTESIAN GRID USED
            genScript += 'portStart = [ {0:g}, {1:g}, {2:g} ]\n'.format(_r(sf * bbCoords.XMin),
                                                                         _r(sf * bbCoords.YMin),
                                                                         _r(sf * bbCoords.ZMin))
            genScript += 'portStop  = [ {0:g}, {1:g}, {2:g} ]\n'.format(_r(sf * bbCoords.XMax),
                                                                         _r(sf * bbCoords.YMax),
                                                                         _r(sf * bbCoords.ZMax))

        if (not startPointName is None):
            genScript = genScript.replace("portStart", startPointName)
        if (not stopPointName is None):
            genScript = genScript.replace("portStop", stopPointName)

        return genScript

    def getPortDefinitionsScriptLines(self, items):
        genScript = ""
        if not items:
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        # port index counter, they are generated into port{} cell variable for octave, cells index starts at 1
        genScriptPortCount = 1

        # nf2ff box counter, they are stored inside octave cell variable {} so this is to index them properly, in octave cells index starts at 1
        genNF2FFBoxCounter = 1

        #
        #   This here generates string for port excitation field, ie. for z+ generates [0 0 1], for y- generates [0 -1 0]
        #       Options for select field x,y,z were removed from GUI, but left here due there could be saved files from previous versions
        #       with these options so to keep backward compatibility they are treated as positive direction in that directions.
        #

        #baseVectorStr = {'x': '[1 0 0]', 'y': '[0 1 0]', 'z': '[0 0 1]', 'x+': '[1 0 0]', 'y+': '[0 1 0]', 'z+': '[0 0 1]', 'x-': '[-1 0 0]', 'y-': '[0 -1 0]', 'z-': '[0 0 -1]', 'XY plane, top layer': '[0 0 -1]', 'XY plane, bottom layer': '[0 0 1]', 'XZ plane, front layer': '[0 -1 0]', 'XZ plane, back layer': '[0 1 0]', 'YZ plane, right layer': '[-1 0 0]', 'YZ plane, left layer': '[1 0 0]',}
        #ERROR: followed baseVectorStr is just to generate something but need to take into consideration also sign of propagation direction
        baseVectorStr = {'x': "'x'", 'y': "'y'", 'z': "'z'", 'x+': "'x'", 'y+': "'y'", 'z+': "'z'", 'x-': "'x'", 'y-': "'y'", 'z-': "'z'", 'XY plane, top layer': "'z'", 'XY plane, bottom layer': "'z'", 'XZ plane, front layer': "'y'", 'XZ plane, back layer': "'y'", 'YZ plane, right layer': "'z'", 'YZ plane, left layer': "'x'",}

        mslDirStr = {'x': "'x'", 'y': "'y'", 'z': "'z'", 'x+': "'x'", 'y+': "'y'", 'z+': "'z'", 'x-': "'x'", 'y-': "'y'", 'z-': "'z'",}
        coaxialDirStr = {'x': '0', 'y': '1', 'z': '2', 'x+': '0', 'y+': '1', 'z+': '2', 'x-': '0', 'y-': '1', 'z-': '2',}
        coplanarDirStr = {'x': '0', 'y': '1', 'z': '2', 'x+': '0', 'y+': '1', 'z+': '2', 'x-': '0', 'y-': '1', 'z-': '2',}
        striplineDirStr = {'x': '0', 'y': '1', 'z': '2', 'x+': '0', 'y+': '1', 'z+': '2', 'x-': '0', 'y-': '1', 'z-': '2',}
        probeDirStr = {'x': '0', 'y': '1', 'z': '2', 'x+': '0', 'y+': '1', 'z+': '2', 'x-': '0', 'y-': '1', 'z-': '2',}

        genScript += "#######################################################################################################################################\n"
        genScript += "# PORTS\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "port = {}\n"
        genScript += "portNamesAndNumbersList = {}\n"
        genScript += "\n"
        genScript += "\n"

        for [item, currSetting] in items:

            print(f"#PORT - {currSetting.getName()} - {currSetting.getType()}")

            objs = self.cadHelpers.getObjects()
            for k in range(item.childCount()):
                childName = item.child(k).text(0)

                self.createdObjectNameList.append(childName)  # add this object into list of created objects which will be used to create named group in exported mesh

                genScript += "## PORT - " + currSetting.getName() + " - " + childName + "\n"

                freecadObjects = [i for i in objs if (i.Label) == childName]

                # print(freecadObjects)
                for obj in freecadObjects:
                    # BOUNDING BOX
                    bbCoords = obj.Shape.BoundBox
                    print('\tFreeCAD lumped port BoundBox: ' + str(bbCoords))

                    #
                    #	getting item priority
                    #
                    priorityItemName = item.parent().text(0) + ", " + item.text(0) + ", " + childName
                    priorityIndex = self.getItemPriority(priorityItemName)

                    #
                    # PORT openEMS GENERATION INTO VARIABLE
                    #
                    if (currSetting.getType() == 'lumped'):
                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords)

                        genScript += "portStart = [k*0.001 for k in portStart]\n"
                        genScript += "portStop = [k*0.001 for k in portStop]\n"
                        genScript += "\n"

                        genScript += f"\n"
                        genScript += f"port[{str(genScriptPortCount)}] = {{}}\n"

                        portVariableName = f"port[{str(genScriptPortCount)}]"

                        genScript += f"port[{str(genScriptPortCount)}]['portStart'] = portStart\n"
                        genScript += f"port[{str(genScriptPortCount)}]['portStop'] = portStop\n"
                        genScript += f"w = abs(portStart[0] - portStop[0])\n"
                        genScript += f"h = abs(portStart[1] - portStop[1])\n"
                        genScript += f"th = abs(portStart[2] - portStop[2])\n"
                        genScript += f"port[{str(genScriptPortCount)}]['w'] = w\n"
                        genScript += f"port[{str(genScriptPortCount)}]['h'] = h\n"
                        genScript += f"port[{str(genScriptPortCount)}]['th'] = th\n"

                        if currSetting.infiniteResistance:
                            genScript += 'portR = inf\n'
                            genScript += f"port[{str(genScriptPortCount)}]['portR'] = float('inf')\n"
                        else:
                            genScript += f"port[{str(genScriptPortCount)}]['portR'] = {str(currSetting.R)}*{str(currSetting.getRUnits())}\n"

                        if (currSetting.direction.lower() == "x"):
                            genScript += f"port[{str(genScriptPortCount)}]['portDirection'] = em.XAX\n"
                        elif (currSetting.direction.lower() == "y"):
                            genScript += f"port[{str(genScriptPortCount)}]['portDirection'] = em.YAX\n"
                        elif (currSetting.direction.lower() == "z"):
                            genScript += f"port[{str(genScriptPortCount)}]['portDirection'] = em.ZAX\n"
                        elif (currSetting.direction.lower() == "custom"):
                            genScript += f"port[{str(genScriptPortCount)}]['portDirection'] = tuple({str(currSetting.directionCustomVector)})\n"
                        else:
                            genScript += 'portDirection = None\n'

                        genScript += f"port[{str(genScriptPortCount)}]['portExcitationAmplitude'] = {str(currSetting.excitationAmplitude)}\n"

                        PORT_NAME = childName
                        if bbCoords.XLength == 0 or bbCoords.YLength == 0 or bbCoords.ZLength == 0:

                            #
                            #   If port is active create on the fly param with power which is passed to function to create lumped port
                            #
                            excitationPowerParamStr = f", power={portVariableName}['portExcitationAmplitude']" if currSetting.isActive else ""

                            #
                            #   Create lumped port script line based on its orientation for now supports X,Y,Z axis
                            #
                            if bbCoords.XLength == 0:
                                genScript += f"port[{str(genScriptPortCount)}]['object'] = em.geo.Plate(name='{PORT_NAME}', origin=portStart, u=[0,h,0], v=[0,0,th])\n"
                                self.portBoundaryConditionScriptLinesBuffer.append(f"simulationObj.mw.bc.LumpedPort({portVariableName}['object'], {str(genScriptPortCount)}, width={portVariableName}['h'], height={portVariableName}['th'], direction={portVariableName}['portDirection'], Z0={portVariableName}['portR']{excitationPowerParamStr})\n")
                            elif bbCoords.YLength == 0:
                                genScript += f"port[{str(genScriptPortCount)}]['object'] = em.geo.Plate(name='{PORT_NAME}', origin=portStart, u=[w,0,0], v=[0,0,th])\n"
                                self.portBoundaryConditionScriptLinesBuffer.append(f"simulationObj.mw.bc.LumpedPort({portVariableName}['object'], {str(genScriptPortCount)}, width={portVariableName}['w'], height={portVariableName}['th'], direction={portVariableName}['portDirection'], Z0={portVariableName}['portR']{excitationPowerParamStr})\n")
                            elif bbCoords.ZLength == 0:
                                genScript += f"port[{str(genScriptPortCount)}]['object'] = em.geo.Plate(name='{PORT_NAME}', origin=portStart, u=[w,0,0], v=[0,h,0])\n"
                                self.portBoundaryConditionScriptLinesBuffer.append(f"simulationObj.mw.bc.LumpedPort({portVariableName}['object'], {str(genScriptPortCount)}, width={portVariableName}['w'], height={portVariableName}['h'], direction={portVariableName}['portDirection'], Z0={portVariableName}['portR']{excitationPowerParamStr})\n")
                        else:
                            genScript += f"port[{str(genScriptPortCount)}]['object'] = em.geo.Box(name='{PORT_NAME}', width=w, height=h, depth=th, position=tuple(portStart))\n"

                        internalPortName = currSetting.name + " - " + obj.Label
                        self.internalPortIndexNamesList[internalPortName] = genScriptPortCount
                        genScript += f'portNamesAndNumbersList["{obj.Label}"] = {genScriptPortCount}\n'
                        genScriptPortCount += 1

                    #
                    #   ERROR - BELOW STILL NOT REWRITTEN INTO PYTHON!!!
                    #

                    elif (currSetting.getType() == 'microstrip'):
                        portStartX, portStartY, portStartZ, portStopX, portStopY, portStopZ = currSetting.getMicrostripStartStopCoords(bbCoords, sf)
                        bbCoords.Xmin = portStartX
                        bbCoords.Ymin = portStartY
                        bbCoords.Zmin = portStartZ
                        bbCoords.Xmax = portStopX
                        bbCoords.Ymax = portStopY
                        bbCoords.Zmax = portStopZ
                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords)

                        if currSetting.infiniteResistance:
                            genScript += 'portR = inf\n'
                        else:
                            genScript += 'portR = ' + str(currSetting.R) + '\n'

                        genScript += 'portUnits = ' + str(currSetting.getRUnits()) + '\n'

                        #
                        #   if currSetting.isActive == False then excitation is 0
                        #
                        genScript += f"portExcitationAmplitude = {str(currSetting.excitationAmplitude)} * {'1' if currSetting.isActive else '0'}\n"

                        genScript += 'mslDir = {}\n'.format(mslDirStr.get(currSetting.mslPropagation[0], '?')) #use just first letter of propagation direction
                        genScript += 'mslEVec = {}\n'.format(baseVectorStr.get(currSetting.direction, '?'))

                        feedShiftStr = {False: "", True: ", FeedShift=" + str(_r(currSetting.mslFeedShiftValue / self.getUnitLengthFromUI_m() * currSetting.getUnitsAsNumber(currSetting.mslFeedShiftUnits)))}
                        measPlaneStr = {False: "", True: ", MeasPlaneShift=" + str(_r(currSetting.mslMeasPlaneShiftValue / self.getUnitLengthFromUI_m() * currSetting.getUnitsAsNumber(currSetting.mslMeasPlaneShiftUnits)))}

                        isActiveMSLStr = {False: "", True: ", 'ExcitePort', true"}

                        genScript_R = ", 'Feed_R', portR*portUnits"

                        genScript += f'port[{str(genScriptPortCount)}] = FDTD.AddMSLPort(' + \
                                         f'{str(genScriptPortCount)}, ' + \
                                         f"{self.internalMaterialIndexNamesList[currSetting.mslMaterial]}, " + \
                                         f'portStart, ' + \
                                         f'portStop, ' + \
                                         f'mslDir, ' + \
                                         f'mslEVec, ' + \
                                         f"excite=portExcitationAmplitude, " + \
                                         f'priority={str(priorityIndex)}, ' + \
                                         f'Feed_R=portR*portUnits' + \
                                         feedShiftStr.get(True) + \
                                         measPlaneStr.get(True) + \
                                   f")\n"

                        internalPortName = currSetting.name + " - " + obj.Label
                        self.internalPortIndexNamesList[internalPortName] = genScriptPortCount
                        genScript += f'portNamesAndNumbersList["{obj.Label}"] = {genScriptPortCount};\n'
                        genScriptPortCount += 1

                    elif (currSetting.getType() == 'circular waveguide'):
                        #
                        #   NOV 2023 - PYTHON API NOT IMPLEMENTED
                        #
                        genScript += "%% circular port openEMS code should be here, NOT IMPLEMENTED python API for it\n"

                    elif (currSetting.getType() == 'rectangular waveguide'):
                        portStartX, portStartY, portStartZ, portStopX, portStopY, portStopZ, waveguideWidth, waveguideHeight = currSetting.getRectangularWaveguideStartStopWidthHeight(bbCoords, sf)
                        bbCoords.Xmin = portStartX
                        bbCoords.Ymin = portStartY
                        bbCoords.Zmin = portStartZ
                        bbCoords.Xmax = portStopX
                        bbCoords.Ymax = portStopY
                        bbCoords.Zmax = portStopZ
                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords)

                        genScript += f"portExcitationAmplitude = {str(currSetting.excitationAmplitude)} * {'1' if currSetting.isActive else '0'}\n"

                        genScript += f'port[{str(genScriptPortCount)}] = FDTD.AddRectWaveGuidePort(' + \
                                     f'{str(genScriptPortCount)}, ' + \
                                     f'portStart, ' + \
                                     f'portStop, ' + \
                                     f'"{currSetting.waveguideRectDir[0]}", ' + \
                                     f'{waveguideWidth}, ' + \
                                     f'{waveguideHeight}, ' + \
                                     f'"{currSetting.modeName}", ' + \
                                     f"excite=portExcitationAmplitude, " + \
                                     f'priority={str(priorityIndex)}, ' + \
                                     f")\n"

                        internalPortName = currSetting.name + " - " + obj.Label
                        self.internalPortIndexNamesList[internalPortName] = genScriptPortCount
                        genScript += f'portNamesAndNumbersList["{obj.Label}"] = {genScriptPortCount};\n'
                        genScriptPortCount += 1
                    elif (currSetting.getType() == 'coaxial'):
                        #
                        #   NOV 2023 - PYTHON API NOT IMPLEMENTED
                        #
                        genScript += '# ERROR: caoxial port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE\n'
                        genScript += '# raise BaseException("caoxial port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE coaxial port")\n'

                    elif (currSetting.getType() == 'coplanar'):
                        #
                        #   NOV 2023 - PYTHON API NOT IMPLEMENTED
                        #
                        genScript += '# ERROR: coplanar port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE\n'
                        genScript += 'raise BaseException("coplanar port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE")\n'

                    elif (currSetting.getType() == 'stripline'):
                        #
                        #   NOV 2023 - PYTHON API NOT IMPLEMENTED
                        #
                        genScript += '# ERROR: stripline port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE\n'
                        genScript += 'raise BaseException("stripline port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE")\n'

                    elif (currSetting.getType() == 'curve'):
                        genScript += '# ERROR: curve port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE\n'
                        genScript += 'raise BaseException("curve port function NOT IMPLEMENTED IN openEMS PYTHON INTERFACE")\n'

                    else:
                        genScript += '# Unknown port type. Nothing was generated.\n'
                        genScript += 'raise BaseException("Unknown port type. Nothing was generated.")\n'

            genScript += "\n"

        return genScript

    def getProbeDefinitionsScriptLines(self, items):
        genScript = ""
        if not items:
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        # counters for indexing generated python code variables containing list of generated object by their type
        genProbeCounter = 1
        genDumpBoxCounter = 1

        # nf2ff box counter, they are stored inside octave cell variable nf2ff{} so this is to index them properly, in octave cells index starts at 1
        genNF2FFBoxCounter = 1

        #
        #   This here generates string for port excitation field, ie. for z+ generates [0 0 1], for y- generates [0 -1 0]
        #       Options for select field x,y,z were removed from GUI, but left here due there could be saved files from previous versions
        #       with these options so to keep backward compatibility they are treated as positive direction in that directions.
        #
        baseVectorStr = {'x': '0', 'y': '1', 'z': '2', 'x+': '0', 'y+': '1', 'z+': '2', 'x-': '0', 'y-': '1', 'z-': '2', 'XY plane, top layer': '2', 'XY plane, bottom layer': '2', 'XZ plane, front layer': '1', 'XZ plane, back layer': '1', 'YZ plane, right layer': '0', 'YZ plane, left layer': '0',}
        probeDirStr = {'x': '0', 'y': '1', 'z': '2', 'x+': '0', 'y+': '1', 'z+': '2', 'x-': '0', 'y-': '1', 'z-': '2',}

        genScript += "#######################################################################################################################################\n"
        genScript += "# PROBES\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "nf2ffBoxList = {}\n"
        genScript += "dumpBoxList = {}\n"
        genScript += "probeList = {}\n"
        genScript += "\n"

        for [item, currSetting] in items:

            print(f"#PROBE - {currSetting.getName()} - {currSetting.getType()}")

            objs = self.cadHelpers.getObjects()
            for k in range(item.childCount()):
                childName = item.child(k).text(0)

                genScript += "# PROBE - " + currSetting.getName() + " - " + childName + "\n"

                freecadObjects = [i for i in objs if (i.Label) == childName]

                # print(freecadObjects)
                for obj in freecadObjects:
                    print(f"\t{obj.Label}")
                    # BOUNDING BOX
                    bbCoords = obj.Shape.BoundBox
                    print(f"\t\t{bbCoords}")

                    #
                    # PROBE openEMS GENERATION INTO VARIABLE
                    #
                    if (currSetting.getType() == "probe"):
                        probeName = f"{currSetting.name}_{childName}"
                        genScript += f'probeName = "{probeName}"\n'

                        genScript += 'probeDirection = {}\n'.format(baseVectorStr.get(currSetting.direction, '?'))

                        if currSetting.probeType == "voltage":
                            genScript += 'probeType = 0\n'
                        elif currSetting.probeType == "current":
                            genScript += 'probeType = 1\n'
                        elif currSetting.probeType == "E field":
                            genScript += 'probeType = 2\n'
                        elif currSetting.probeType == "H field":
                            genScript += 'probeType = 3\n'
                        else:
                            genScript += 'probeType = ?    #ERROR probe code generate don\'t know type\n'

                        argStr = ""
                        if not (bbCoords.XMin == bbCoords.XMax or bbCoords.YMin == bbCoords.YMax or bbCoords.ZMin == bbCoords.ZMax):
                            argStr += f", norm_dir=probeDirection"

                        if (currSetting.probeDomain == "frequency"):
                            argStr += f", frequency=["

                            if (len(currSetting.probeFrequencyList) > 0):
                                for freqStr in currSetting.probeFrequencyList:
                                    freqStr = freqStr.strip()
                                    result = re.search(r"([+,\,\-,.,0-9]+)([A-Za-z]+)$", freqStr)
                                    if result:
                                        freqValue = float(result.group(1))
                                        freqUnits = result.group(2)
                                        freqValue = freqValue * currSetting.getUnitsAsNumber(freqUnits)
                                        argStr += str(freqValue) + ","
                                argStr += "]"
                            else:
                                argStr += "f0]#{ERROR NO FREQUENCIES FOR PROBE FOUND, SO INSTEAD USED f0#}"
                                self.cadHelpers.printWarning(f"probe octave code generator error, no frequencies defined for '{probeName}', using f0 instead\n")

                        genScript += f"probeList[probeName] = CSX.AddProbe(probeName, probeType" + argStr + ")\n"
                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords, "probeStart", "probeStop")
                        genScript += f"probeList[probeName].AddBox(probeStart, probeStop )\n"
                        genScript += "\n"
                        genProbeCounter += 1

                    elif (currSetting.getType() == "dumpbox"):
                        dumpboxName = f"{currSetting.name}_{childName}"
                        genScript += f'dumpboxName = "{dumpboxName}"\n'

                        dumpType = currSetting.getDumpType()
                        genScript += f'dumpboxType = {dumpType}\n'

                        argStr = ""
                        #
                        #   dump file type:
                        #       0 = vtk (default)
                        #       1 = hdf5
                        #
                        if (currSetting.dumpboxFileType == "hdf5"):
                            argStr += f", file_type=1"

                        emptyFrequencyListError = False
                        if (currSetting.dumpboxDomain == "frequency"):
                            argStr += ", frequency=["

                            if (len(currSetting.dumpboxFrequencyList) > 0):
                                for freqStr in currSetting.dumpboxFrequencyList:
                                    freqStr = freqStr.strip()
                                    result = re.search(r"([+,\,\-,.,0-9]+)([A-Za-z]+)$", freqStr)
                                    if result:
                                        freqValue = float(result.group(1))
                                        freqUnits = result.group(2)
                                        freqValue = freqValue * currSetting.getUnitsAsNumber(freqUnits)
                                        argStr += str(freqValue) + ","
                                argStr += "]"
                            else:
                                emptyFrequencyListError = True
                                argStr += "f0]"
                                self.cadHelpers.printWarning(f"dumpbox octave code generator error, no frequencies defined for '{dumpboxName}', using f0 instead\n")

                        #if error put note about it into script
                        if emptyFrequencyListError:
                            genScript += f"dumpBoxList[dumpboxName] = CSX.AddDump(dumpboxName, dump_type=dumpboxType" + argStr + ") # ERROR script generation no frequencies for dumpbox, therefore using f0\n"
                        else:
                            genScript += f"dumpBoxList[dumpboxName] = CSX.AddDump(dumpboxName, dump_type=dumpboxType" + argStr + ")\n"

                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords, "dumpboxStart", "dumpboxStop")
                        genScript += f"dumpBoxList[dumpboxName].AddBox(dumpboxStart, dumpboxStop )\n"
                        genScript += "\n"
                        genDumpBoxCounter += 1

                    elif (currSetting.getType() == 'et dump'):
                        dumpboxName = f"{currSetting.name}_{childName}"
                        genScript += f'dumpboxName = "{dumpboxName}"\n'

                        genScript += f"dumpBoxList[dumpboxName] = CSX.AddDump(dumpboxName, dump_type=0, dump_mode=2)\n"
                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords, "dumpboxStart", "dumpboxStop")
                        genScript += f"dumpBoxList[dumpboxName].AddBox(dumpboxStart, dumpboxStop)\n"
                        genDumpBoxCounter += 1

                    elif (currSetting.getType() == 'ht dump'):
                        dumpboxName = f"{currSetting.name}_{childName}"
                        genScript += f'dumpboxName = "{dumpboxName}"\n'

                        genScript += f"dumpBoxList[dumpboxName] = CSX.AddDump(dumpboxName, dumnp_type=1, dump_mode=2)\n"
                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords, "dumpboxStart", "dumpboxStop")
                        genScript += f"dumpBoxList[dumpboxName].AddBox(dumpboxStart, dumpboxStop );\n"
                        genDumpBoxCounter += 1

                    elif (currSetting.getType() == 'nf2ff box'):
                        dumpboxName = f"{currSetting.name} - {childName}"
                        dumpboxName = dumpboxName.replace(" ", "_")
                        genScript += f'dumpboxName = "{dumpboxName}"\n'

                        genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords, "nf2ffStart", "nf2ffStop")

                        # genScript += 'nf2ffUnit = ' + currSetting.getUnitAsScriptLine() + ';\n'
                        genScript += f"nf2ffBoxList[dumpboxName] = FDTD.CreateNF2FFBox(dumpboxName, nf2ffStart, nf2ffStop)\n"
                        # NF2FF grid lines are generated below via getNF2FFDefinitionsScriptLines()

                        #
                        #   ATTENTION this is NF2FF box counter
                        #
                        self.internalNF2FFIndexNamesList[dumpboxName] = genNF2FFBoxCounter
                        genNF2FFBoxCounter += 1

                    else:
                        genScript += '# Unknown port type. Nothing was generated. \n'

            genScript += "\n"

        return genScript

    def getLumpedPartDefinitionsScriptLines(self, items):
        genScript = ""
        if not items:
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        genScript += "#######################################################################################################################################\n"
        genScript += "# LUMPED PART\n"
        genScript += "#######################################################################################################################################\n"

        for [item, currentSetting] in items:
            genScript += "# LUMPED PARTS " + currentSetting.getName() + "\n"

            # traverse through all children item for this particular lumped part settings
            objs = self.cadHelpers.getObjects()
            objsExport = []
            for k in range(item.childCount()):
                childName = item.child(k).text(0)
                print("#LUMPED PART " + currentSetting.getType())

                freecadObjects = [i for i in objs if (i.Label) == childName]
                for obj in freecadObjects:
                    # obj = FreeCAD Object class

                    # BOUNDING BOX
                    bbCoords = obj.Shape.BoundBox

                    genScript += self.getCartesianOrCylindricalScriptLinesFromStartStop(bbCoords, "lumpedPartStart", "lumpedPartStop")

                    lumpedPartParams = f"'{currentSetting.name}'"
                    lumpedPartParams += f", ny='{currentSetting.getDirection()}'"

                    if ('r' in currentSetting.getType().lower()):
                        lumpedPartParams += f", R={currentSetting.getR()}"
                    if ('l' in currentSetting.getType().lower()):
                        lumpedPartParams += f", L={currentSetting.getL()}"
                    if ('c' in currentSetting.getType().lower()):
                        lumpedPartParams += f", C={currentSetting.getC()}"

                    lumpedPartParams += f", caps={'True' if currentSetting.getCapsEnabled() else 'False'}"

                    #
                    #   WARNING: This was added just recently needs to be validated.
                    #
                    if (currentSetting.getCombinationType() == 'parallel'):
                        #lumpedPartParams += f", LEtype=0"
                        pass
                    elif (currentSetting.getCombinationType() == 'series'):
                        lumpedPartParams += f", LEtype=1"
                    else:
                        pass

                    #
                    #	getting item priority
                    #
                    priorityItemName = item.parent().text(0) + ", " + item.text(0) + ", " + childName
                    priorityIndex = self.getItemPriority(priorityItemName)

                    # WARNING: Caps param has hardwired value 1, will be generated small metal caps to connect part with circuit !!!
                    genScript += f"lumpedPart = CSX.AddLumpedElement({lumpedPartParams});\n"
                    genScript += f"lumpedPart.AddBox(lumpedPartStart, lumpedPartStop, priority={priorityIndex});\n"

            genScript += "\n"

        return genScript

    def getBoundaryConditionScriptLines(self, items):
        genScript = ""
        if not items:
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        genScript += "#######################################################################################################################################\n"
        genScript += "# BOUNDARY CONDITIONS PART\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "\n"

        for [item, currentSetting] in items:
            genScript += "# BOUNDARY CONDITION NAME: " + currentSetting.getName() + "\n"
            genScript += "# TYPE: " + currentSetting.getType() + "\n"

            # traverse through all children item for this particular lumped part settings
            objs = self.cadHelpers.getObjects()
            objsExport = []
            for k in range(item.childCount()):
                childName = item.child(k).text(0)
                print("#BOUNDARY CONDITION TYPE: " + currentSetting.getType())

                freecadObjectList = [i for i in objs if (i.Label) == childName]
                for freecadObj in freecadObjectList:
                    # freecadObj = FreeCAD Object class

                    genScript += f"boundary_selection = None\n"
                    genScript += f"for geometryObj in simulationObj.state.manager.geometry_list[simulationObj.modelname].values():\n"
                    genScript += f"\tif geometryObj.name == '{childName}' or geometryObj.name.startswith('{childName}'):\n"
                    genScript += f"\t\tboundary_selection = geometryObj.boundary()\n"

                    #
                    #	getting item priority
                    #       for now this is not used as I am not sure how to use it in EMerge
                    #
                    priorityItemName = item.parent().text(0) + ", " + item.text(0) + ", " + childName
                    priorityIndex = self.getItemPriority(priorityItemName)

                    bcType = currentSetting.getType().lower()
                    if  bcType == "absorbing":
                        genScript += f"simulationObj.mw.bc.AbsorbingBoundary(boundary_selection)"
                    elif bcType == "pec":
                        # genScript += f"simulationObj.mw.bc.PECBoundary(boundary_selection)"   #old method for <= 2.3.x
                        genScript += f"simulationObj.mw.bc.PEC(boundary_selection)"             #new method for 2.4.0 and above
                    else:
                        genScript += f"# ERROR: Unknown boundary condition type \"{currentSetting.getType()}\""

                    genScript += f"\n\n"


            genScript += "\n"

        return genScript

    def getNF2FFDefinitionsScriptLines(self, items):
        genScript = ""
        if not items:
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units
        nf2ff_gridlines = {'x': [], 'y': [], 'z': []}

        for [item, currSetting] in items:

            objs = self.cadHelpers.getObjects()
            for k in range(item.childCount()):
                childName = item.child(k).text(0)

                freecadObjects = [i for i in objs if (i.Label) == childName]

                # print(freecadObjects)
                for obj in freecadObjects:
                    # BOUNDING BOX
                    bbCoords = obj.Shape.BoundBox

                    if (currSetting.getType() == 'nf2ff box'):
                        nf2ff_gridlines['x'].append("{0:g}".format(_r(sf * bbCoords.XMin)))
                        nf2ff_gridlines['x'].append("{0:g}".format(_r(sf * bbCoords.XMax)))
                        nf2ff_gridlines['y'].append("{0:g}".format(_r(sf * bbCoords.YMin)))
                        nf2ff_gridlines['y'].append("{0:g}".format(_r(sf * bbCoords.YMax)))
                        nf2ff_gridlines['z'].append("{0:g}".format(_r(sf * bbCoords.ZMin)))
                        nf2ff_gridlines['z'].append("{0:g}".format(_r(sf * bbCoords.ZMax)))

        writeNF2FFlines = (len(nf2ff_gridlines['x']) > 0) or (len(nf2ff_gridlines['y']) > 0) or (
                    len(nf2ff_gridlines['z']) > 0)

        if writeNF2FFlines:
            genScript += "#######################################################################################################################################\n"
            genScript += "# NF2FF PROBES GRIDLINES\n"
            genScript += "#######################################################################################################################################\n"

            genScript += "mesh.x = np.array([])\n"
            genScript += "mesh.y = np.array([])\n"
            genScript += "mesh.z = np.array([])\n"

            if (len(nf2ff_gridlines['x']) > 0):
                genScript += "mesh.x = np.append(mesh.x, [" + ", ".join(str(i) for i in nf2ff_gridlines['x']) + "])\n"
            if (len(nf2ff_gridlines['y']) > 0):
                genScript += "mesh.y = np.append(mesh.y, [" + ", ".join(str(i) for i in nf2ff_gridlines['y']) + "])\n"
            if (len(nf2ff_gridlines['z']) > 0):
                genScript += "mesh.z = np.append(mesh.z, [" + ", ".join(str(i) for i in nf2ff_gridlines['z']) + "])\n"

            genScript += "openEMS_grid.AddLine('x', mesh.x)\n"
            genScript += "openEMS_grid.AddLine('y', mesh.y)\n"
            genScript += "openEMS_grid.AddLine('z', mesh.z)\n"
            genScript += "\n"

        return genScript

    def getOrderedGridDefinitionsScriptLines(self, items):
        genScript = ""
        meshPrioritiesCount = self.form.meshPriorityTreeView.topLevelItemCount()

        if (not items) or (meshPrioritiesCount == 0):
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        refUnitStr = self.form.simParamsDeltaUnitList.currentText()
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        genScript += "#######################################################################################################################################\n"
        genScript += "# GRID LINES\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "\n"

        # Create lists and dict to be able to resolve ordered list of (grid settings instance <-> FreeCAD object) associations.
        # In its current form, this implies user-defined grid lines have to be associated with the simulation volume.
        _assoc = lambda idx: list(map(str.strip, self.form.meshPriorityTreeView.topLevelItem(idx).text(0).split(',')))
        orderedAssociations = [_assoc(k) for k in reversed(range(meshPrioritiesCount))]
        gridSettingsNodeNames = [gridSettingsNode.text(0) for [gridSettingsNode, gridSettingsInst] in items]
        fcObjects = {obj.Label: obj for obj in self.cadHelpers.getObjects()}

        for gridSettingsNodeName in gridSettingsNodeNames:
            print("Grid type : " + gridSettingsNodeName)

        for k, [categoryName, gridName, FreeCADObjectName] in enumerate(orderedAssociations):

            print("Grid priority level {} : {} :: {}".format(k, FreeCADObjectName, gridName))

            if not (gridName in gridSettingsNodeNames):
                print("Failed to resolve '{}'.".format(gridName))
                continue
            itemListIdx = gridSettingsNodeNames.index(gridName)

            #GridSettingsItem object from GUI
            gridSettingsInst = items[itemListIdx][1]

            #Grid category object from GUI
            gridCategoryObj = items[itemListIdx][0]

            #
            #   Fixed Distance, Fixed Count mesh boundaries coords obtain
            #
            if (gridSettingsInst.getType() in ['FEM Max Size']):
                fcObject = fcObjects.get(FreeCADObjectName, None)
                if (not fcObject):
                    print("Failed to resolve '{}'.".format(FreeCADObjectName))
                    continue

                ### Produce script output.

                if (not "Shape" in dir(fcObject)):
                    continue

                genScript += f"#\tmax element size for '{FreeCADObjectName}'\n"
                genScript += f"#\n"
                genScript += f"for geometryObj in simulationObj.state.manager.geometry_list[simulationObj.modelname].values():\n"
                genScript += f"\t\tif geometryObj.name == '{FreeCADObjectName}' or geometryObj.name.startswith('{FreeCADObjectName}_'):\n"

                if gridSettingsInst.femMesh['femUseMaxElementSize'] == True:
                    genScript += f"\t\t\tsimulationObj.mesher.set_size(geometryObj, {gridSettingsInst.femMesh['femMaxElementSize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                if gridSettingsInst.femMesh['femUseMaxBoundarySize'] == True:
                    genScript += f"\t\t\tsimulationObj.mesher.set_boundary_size(geometryObj, {gridSettingsInst.femMesh['femMaxBoundarySize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                if gridSettingsInst.femMesh['femUseMaxFaceSize'] == True:
                    genScript += f"\t\t\tsimulationObj.mesher.set_face_size(geometryObj, {gridSettingsInst.femMesh['femMaxFaceSize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                if gridSettingsInst.femMesh['femUseMaxDomainSize'] == True:
                    genScript += f"\t\t\tsimulationObj.mesher.set_domain_size(geometryObj, {gridSettingsInst.femMesh['femMaxDomainSize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"

                #
                #   TODO: Add user defined mesh, code block will be placed into code
                #

                genScript += f"\n"

            genScript += "\n"

        genScript += "\n"

        return genScript

    def getOrderedGridDefinitionsScriptLines_old_01(self, items):
        genScript = ""
        meshPrioritiesCount = self.form.meshPriorityTreeView.topLevelItemCount()

        if (not items) or (meshPrioritiesCount == 0):
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        refUnitStr = self.form.simParamsDeltaUnitList.currentText()
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        genScript += "#######################################################################################################################################\n"
        genScript += "# GRID LINES\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "\n"

        # Create lists and dict to be able to resolve ordered list of (grid settings instance <-> FreeCAD object) associations.
        # In its current form, this implies user-defined grid lines have to be associated with the simulation volume.
        _assoc = lambda idx: list(map(str.strip, self.form.meshPriorityTreeView.topLevelItem(idx).text(0).split(',')))
        orderedAssociations = [_assoc(k) for k in reversed(range(meshPrioritiesCount))]
        gridSettingsNodeNames = [gridSettingsNode.text(0) for [gridSettingsNode, gridSettingsInst] in items]
        fcObjects = {obj.Label: obj for obj in self.cadHelpers.getObjects()}

        for gridSettingsNodeName in gridSettingsNodeNames:
            print("Grid type : " + gridSettingsNodeName)

        for k, [categoryName, gridName, FreeCADObjectName] in enumerate(orderedAssociations):

            print("Grid priority level {} : {} :: {}".format(k, FreeCADObjectName, gridName))

            if not (gridName in gridSettingsNodeNames):
                print("Failed to resolve '{}'.".format(gridName))
                continue
            itemListIdx = gridSettingsNodeNames.index(gridName)
            gridSettingsInst = items[itemListIdx][1]

            fcObject = fcObjects.get(FreeCADObjectName, None)
            if (not fcObject):
                print("Failed to resolve '{}'.".format(FreeCADObjectName))
                continue

            ### Produce script output.

            if (not "Shape" in dir(fcObject)):
                continue

            bbCoords = fcObject.Shape.BoundBox

            # If generateLinesInside is selected, grid line region is shifted inward by lambda/20.
            if gridSettingsInst.generateLinesInside:
                delta = self.maxGridResolution_m / refUnit
                print("GRID generateLinesInside object detected, setting correction constant to " + str(
                    delta) + " " + refUnitStr)
            else:
                delta = 0

            #
            #	THIS IS HARD WIRED HERE, NEED TO BE CHANGED, LuboJ, September 2022
            #
            # DEBUG - DISABLED - generate grid inside using 1/20 of maximum lambda, it's not that equation,
            #	ie. for 3.4GHz simulation 1/20th is 4mm what is wrong for delta to generate
            #	gridlines inside object, must be much much lower like 10times
            delta = 0
            debugHardLimit = 0.1e-3  # debug hard limit to get gridlines inside STL objects

            xmax = sf * bbCoords.XMax - np.sign(bbCoords.XMax - bbCoords.XMin) * delta - debugHardLimit
            ymax = sf * bbCoords.YMax - np.sign(bbCoords.YMax - bbCoords.YMin) * delta - debugHardLimit
            zmax = sf * bbCoords.ZMax - np.sign(bbCoords.ZMax - bbCoords.ZMin) * delta - debugHardLimit
            xmin = sf * bbCoords.XMin + np.sign(bbCoords.XMax - bbCoords.XMin) * delta + debugHardLimit
            ymin = sf * bbCoords.YMin + np.sign(bbCoords.YMax - bbCoords.YMin) * delta + debugHardLimit
            zmin = sf * bbCoords.ZMin + np.sign(bbCoords.ZMax - bbCoords.ZMin) * delta + debugHardLimit

            # Write grid definition.

            genScript += "## GRID - " + gridSettingsInst.getName() + " - " + FreeCADObjectName + ' (' + gridSettingsInst.getType() + ")\n"

            if (gridSettingsInst.getType() == 'Fixed Distance'):
                if gridSettingsInst.xenabled:
                    if gridSettingsInst.topPriorityLines:
                        genScript += "mesh.x = np.delete(mesh.x, np.argwhere((mesh.x >= {0:g}) & (mesh.x <= {1:g})))\n".format(_r(xmin), _r(xmax))
                    genScript += "mesh.x = np.concatenate((mesh.x, np.arange({0:g},{1:g},{2:g})))\n".format(_r(xmin), _r(xmax), _r(gridSettingsInst.getXYZ(refUnit)['x']))
                if gridSettingsInst.yenabled:
                    if gridSettingsInst.topPriorityLines:
                        genScript += "mesh.y = np.delete(mesh.y, np.argwhere((mesh.y >= {0:g}) & (mesh.y <= {1:g})))\n".format(_r(ymin), _r(ymax))
                    genScript += "mesh.y = np.concatenate((mesh.y, np.arange({0:g},{1:g},{2:g})))\n".format(_r(ymin),_r(ymax),_r(gridSettingsInst.getXYZ(refUnit)['y']))
                if gridSettingsInst.zenabled:
                    if gridSettingsInst.topPriorityLines:
                        genScript += "mesh.z = np.delete(mesh.z, np.argwhere((mesh.z >= {0:g}) & (mesh.z <= {1:g})))\n".format(_r(zmin), _r(zmax))
                    genScript += "mesh.z = np.concatenate((mesh.z, np.arange({0:g},{1:g},{2:g})))\n".format(_r(zmin),_r(zmax),_r(gridSettingsInst.getXYZ(refUnit)['z']))

            elif (gridSettingsInst.getType() == 'Fixed Count'):
                if gridSettingsInst.xenabled:
                    if gridSettingsInst.topPriorityLines:
                        genScript += "mesh.x = np.delete(mesh.x, np.argwhere((mesh.x >= {0:g}) & (mesh.x <= {1:g})))\n".format(_r(xmin), _r(xmax))
                    if (not gridSettingsInst.getXYZ()['x'] == 1):
                        genScript += "mesh.x = np.concatenate((mesh.x, linspace({0:g},{1:g},{2:g})))\n".format(_r(xmin), _r(xmax), _r(gridSettingsInst.getXYZ(refUnit)['x']))
                    else:
                        genScript += "mesh.x = np.append(mesh.x, {0:g})\n".format(_r((xmin + xmax) / 2))

                if gridSettingsInst.yenabled:
                    if gridSettingsInst.topPriorityLines:
                        genScript += "mesh.y = np.delete(mesh.y, np.argwhere((mesh.y >= {0:g}) & (mesh.y <= {1:g})))\n".format(_r(ymin), _r(ymax))
                    if (not gridSettingsInst.getXYZ()['y'] == 1):
                        genScript += "mesh.y = np.concatenate((mesh.y, linspace({0:g},{1:g},{2:g})))\n".format(_r(ymin), _r(ymax), _r(
                            gridSettingsInst.getXYZ(refUnit)['y']))
                    else:
                        genScript += "mesh.y = np.append(mesh.y, {0:g})\n".format(_r((ymin + ymax) / 2))

                if gridSettingsInst.zenabled:
                    if gridSettingsInst.topPriorityLines:
                        genScript += "mesh.z = np.delete(mesh.z, np.argwhere((mesh.z >= {0:g}) & (mesh.z <= {1:g})))\n".format(_r(zmin), _r(zmax))
                    if (not gridSettingsInst.getXYZ()['z'] == 1):
                        genScript += "mesh.z = np.concatenate((mesh.z, linspace({0:g},{1:g},{2:g})))\n".format(_r(zmin), _r(zmax), _r(
                            gridSettingsInst.getXYZ(refUnit)['z']))
                    else:
                        genScript += "mesh.z = np.append(mesh.z, {0:g})\n".format(_r((zmin + zmax) / 2))

            elif (gridSettingsInst.getType() == 'User Defined'):
                genScript += "mesh = " + gridSettingsInst.getXYZ() + ";\n"

            genScript += "\n"

        genScript += "openEMS_grid.AddLine('x', mesh.x)\n"
        genScript += "openEMS_grid.AddLine('y', mesh.y)\n"
        genScript += "openEMS_grid.AddLine('z', mesh.z)\n"
        genScript += "\n"

        return genScript


    def getInitScriptLines(self):
        genScript = ""
        genScript += "# To be run with python.\n"
        genScript += "# FreeCAD to OpenEMS plugin but this time it generates EMerge by Lubomir Jagos, \n"
        genScript += "# see https://github.com/LubomirJagos42/FreeCAD-OpenEMS-Export\n"
        genScript += "#\n"
        genScript += "# This file has been automatically generated. Manual changes may be overwritten.\n"
        genScript += "#\n"
        genScript += "\n"
        genScript += "### Import Libraries\n"
        genScript += "import math\n"
        genScript += "import numpy as np\n"
        genScript += "import emerge as em\n"
        genScript += "import os, tempfile, shutil\n"
        genScript += "\n"

        genScript += "# Change current path to script file folder\n"
        genScript += "#\n"
        genScript += "abspath = os.path.abspath(__file__)\n"
        genScript += "dname = os.path.dirname(abspath)\n"
        genScript += "os.chdir(dname)\n"

        genScript += "## constants\n"
        genScript += "unit    = " + str(self.getUnitLengthFromUI_m()) + " # Model coordinates and lengths will be specified in " + self.form.simParamsDeltaUnitList.currentText() + ".\n"
        genScript += "fc_unit = " + str(self.getFreeCADUnitLength_m()) + " # STL files are exported in FreeCAD standard units (mm).\n"
        genScript += "\n"

        return genScript

    def getExcitationScriptLines(self, definitionsOnly=False):
        genScript = ""

        excitationCategory = self.form.objectAssignmentRightTreeWidget.findItems("Excitation",
                                                                                 QtCore.Qt.MatchFixedString)
        if len(excitationCategory) >= 0:
            print("Excitation Settings detected")
            print("#")
            print("#EXCITATION")

            # FOR WHOLE SIMULATION THERE IS JUST ONE EXCITATION DEFINED, so first is taken!
            if (excitationCategory[0].childCount() > 0):
                item = excitationCategory[0].child(0)
                currSetting = item.data(0, QtCore.Qt.UserRole)  # At index 0 is Default Excitation.
                # Currently only 1 excitation is allowed. Multiple excitations could be managed by setting one of them as "selected" or "active", while all others are deactivated.
                # This would help the user to manage different analysis scenarios / excitation ranges.

                print("#name: " + currSetting.getName())
                print("#type: " + currSetting.getType())

                genScript += "#######################################################################################################################################\n"
                genScript += "# EXCITATION " + currSetting.getName() + "\n"
                genScript += "#######################################################################################################################################\n"

                if (currSetting.getType() == 'sweep'):
                    genScript += f"fmin = {str(currSetting.sweep['fmin'])}*{str(currSetting.getUnitsAsNumber(currSetting.units))}\n"
                    genScript += f"fmax = {str(currSetting.sweep['fmax'])}*{str(currSetting.getUnitsAsNumber(currSetting.units))}\n"
                    genScript += f"resolution = {str(currSetting.sweep['resolution'])}\n"
                    genScript += f"npoints = {str(currSetting.sweep['npoints'])}\n"
                    genScript += f"simulationObj.mw.set_frequency_range(fmin, fmax, npoints)\n"
                    genScript += f"simulationObj.mw.set_resolution(resolution)\n"
                    pass
                else:
                    genScript += f"# ERROR: Excitation type \"{currSetting.getType()}\" not implemented in script generator!\n"

                genScript += "\n"
            else:
                self.guiHelpers.displayMessage("Missing excitation, please define one.")
                pass
            pass
        return genScript

    def getBoundaryConditionsScriptLines(self):
        genScript = ""

        genScript += "#######################################################################################################################################\n"
        genScript += "# BOUNDARY CONDITIONS\n"
        genScript += "#######################################################################################################################################\n"

        _bcStr = lambda pml_val, text: '\"PML_{}\"'.format(str(pml_val)) if text == 'PML' else '\"{}\"'.format(text)
        strBC = ""
        strBC += _bcStr(self.form.PMLxmincells.value(), self.form.BCxmin.currentText()) + ","
        strBC += _bcStr(self.form.PMLxmaxcells.value(), self.form.BCxmax.currentText()) + ","
        strBC += _bcStr(self.form.PMLymincells.value(), self.form.BCymin.currentText()) + ","
        strBC += _bcStr(self.form.PMLymaxcells.value(), self.form.BCymax.currentText()) + ","
        strBC += _bcStr(self.form.PMLzmincells.value(), self.form.BCzmin.currentText()) + ","
        strBC += _bcStr(self.form.PMLzmaxcells.value(), self.form.BCzmax.currentText())

        genScript += "BC = [" + strBC + "]\n"
        genScript += "FDTD.SetBoundaryCond(BC)\n"
        genScript += "\n"

        return genScript

    def getMinimalGridlineSpacingScriptLines(self):
        genScript = ""

        if (self.form.genParamMinGridSpacingEnable.isChecked()):
            minSpacingX = self.form.genParamMinGridSpacingX.value() / 1000 / self.getUnitLengthFromUI_m()
            minSpacingY = self.form.genParamMinGridSpacingY.value() / 1000 / self.getUnitLengthFromUI_m()
            minSpacingZ = self.form.genParamMinGridSpacingZ.value() / 1000 / self.getUnitLengthFromUI_m()

            genScript += "#######################################################################################################################################\n"
            genScript += "# MINIMAL GRIDLINES SPACING, removing gridlines which are closer as defined in GUI\n"
            genScript += "#######################################################################################################################################\n"
            genScript += 'mesh.x = openEMS_grid.GetLines("x", True)\n'
            genScript += 'mesh.y = openEMS_grid.GetLines("y", True)\n'
            genScript += 'mesh.z = openEMS_grid.GetLines("z", True)\n'
            genScript += '\n'
            genScript += 'openEMS_grid.ClearLines("x")\n'
            genScript += 'openEMS_grid.ClearLines("y")\n'
            genScript += 'openEMS_grid.ClearLines("z")\n'
            genScript += '\n'
            genScript += 'for k in range(len(mesh.x)-1):\n'
            genScript += '\tif (not np.isinf(mesh.x[k]) and abs(mesh.x[k+1]-mesh.x[k]) <= ' + str(minSpacingX) + '):\n'
            genScript += '\t\tprint("Removnig line at x: " + str(mesh.x[k+1]))\n'
            genScript += '\t\tmesh.x[k+1] = np.inf\n'
            genScript += '\n'
            genScript += 'for k in range(len(mesh.y)-1):\n'
            genScript += '\tif (not np.isinf(mesh.y[k]) and abs(mesh.y[k+1]-mesh.y[k]) <= ' + str(minSpacingY) + '):\n'
            genScript += '\t\tprint("Removnig line at y: " + str(mesh.y[k+1]))\n'
            genScript += '\t\tmesh.y[k+1] = np.inf\n'
            genScript += '\n'
            genScript += 'for k in range(len(mesh.z)-1):\n'
            genScript += '\tif (not np.isinf(mesh.z[k]) and abs(mesh.z[k+1]-mesh.z[k]) <= ' + str(minSpacingZ) + '):\n'
            genScript += '\t\tprint("Removnig line at z: " + str(mesh.z[k+1]))\n'
            genScript += '\t\tmesh.z[k+1] = np.inf\n'
            genScript += '\n'

            genScript += 'mesh.x = mesh.x[~np.isinf(mesh.x)]\n'
            genScript += 'mesh.y = mesh.y[~np.isinf(mesh.y)]\n'
            genScript += 'mesh.z = mesh.z[~np.isinf(mesh.z)]\n'
            genScript += '\n'

            genScript += "openEMS_grid.AddLine('x', mesh.x)\n"
            genScript += "openEMS_grid.AddLine('y', mesh.y)\n"
            genScript += "openEMS_grid.AddLine('z', mesh.z)\n"
            genScript += '\n'

        return genScript

    def generateSimulationScript(self, outputDir=None):
        """
        General method which should be used as interface in other objects. Generate simulation script.
        :param outputDir:
        :return:
        """
        self.generateEmergeScript(outputDir)

    def generateEmergeScript(self, outputDir=None):
        """
        Generates result simulation script for EMerge

        :param outputDir:
        :return:
        """

        self.portBoundaryConditionScriptLinesBuffer = []
        self.createdObjectNameList = []
        self.createdObjectBoundaryNameList = []

        # Create outputDir relative to local FreeCAD file if output dir does not exists
        #   if outputDir is set to same value
        #   if outputStr is None then folder with name as FreeCAD file with suffix _openEMS_simulation is created
        outputDir = self.createOuputDir(outputDir)

        # Update status bar to inform user that exporting has begun.
        if self.statusBar is not None:
            self.statusBar.showMessage("Generating EMerge script and geometry files ...", 5000)
            QtWidgets.QApplication.processEvents()

        # Constants and variable initialization.

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        refUnitStr = self.form.simParamsDeltaUnitList.currentText()
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        # List categories and items.

        itemsByClassName = self.getItemsByClassName()

        # Write script header.

        genScript = ""

        genScript += "## EMerge simulation\n"
        genScript += "#\n"
        genScript += "#\n"

        genScript += self.getInitScriptLines()

        genScript += "\n"
        genScript += "currDir = os.getcwd()\n"
        genScript += "print(currDir)\n"
        genScript += "\n"

        # Write simulation settings.

        genScript += "## prepare simulation folder, if dir exits remove and create new one to be empty\n"
        genScript += "Sim_Path = os.path.join(currDir, 'simulation_output')\n"

        genScript += "if os.path.exists(Sim_Path):\n"
        genScript += "\tshutil.rmtree(Sim_Path)   # clear previous directory\n"
        genScript += "\tos.mkdir(Sim_Path)    # create empty simulation folder\n"
        genScript += "\n"

        print("======================== REPORT BEGIN ========================\n")

        genScript += "# --- Unit definitions -----------------------------------------------------\n"
        genScript += "m = 1.0\n"
        genScript += "cm = 0.01\n"
        genScript += "mm = 0.001  # meters per millimeter\n"
        genScript += "um = 0.000001\n"
        genScript += "nm = 0.000000001\n"
        genScript += "\n"
        genScript += "pF = 1e-12  # picofarad in farads\n"
        genScript += "fF = 1e-15  # femtofarad in farads\n"
        genScript += "pH = 1e-12  # picohenry in henrys\n"
        genScript += "nH = 1e-9  # nanohenry in henrys\n"
        genScript += "\n"

        simulationName = self.cadHelpers.getCurrentDocumentFileName()

        genScript += f"simulationObj = em.Simulation(\"{simulationName}\", save_file=True)\n"
        solverEngineStr = self.form.simParamsSolverEngine_emerge.currentText()
        if(solverEngineStr.upper() == "CUDA"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.CUDSS)\n"
        elif(solverEngineStr.upper() == "PARDISO"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.PARDISO)\n"
        elif(solverEngineStr.upper() == "SUPERLU"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.SUPERLU)\n"
        elif(solverEngineStr.upper() == "UMFPACK"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.UMFPACK)\n"
        elif(solverEngineStr.upper() == "LAPACK"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.LAPACK)\n"
        elif(solverEngineStr.upper() == "ARPACK"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.ARPACK)\n"
        elif(solverEngineStr.upper() == "SMART_ARPACK"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.SMART_ARPACK)\n"
        elif(solverEngineStr.upper() == "SMART_ARPACK_BMA"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.SMART_ARPACK_BMA)\n"
        elif(solverEngineStr.upper() == "MUMPS"):
            genScript += "simulationObj.mw.solveroutine.set_solver(em.EMSolver.MUMPS)\n"
        genScript += "\n"

        self.reportFreeCADItemSettings(itemsByClassName.get("FreeCADSettingsItem", None))

        # Write excitation definition.
        genScript += self.getExcitationScriptLines()

        # Write material definitions.
        genScript += self.getMaterialDefinitionsScriptLines(itemsByClassName.get("MaterialSettingsItem", None), outputDir)

        # Write import STEP objects which are used as boundary conditions
        genScript += self.getBoundaryConditionObjectImportScriptLines(itemsByClassName.get("BoundaryConditionSettingsItem", None), outputDir)

        # Write port definitions.
        genScript += self.getPortDefinitionsScriptLines(itemsByClassName.get("PortSettingsItem", None))

        #
        #   Commit geometry before mesh definition.
        #       This will reassign dimtags associated inside OpenCASCADe core, so it's done before mesh size definitions.
        #
        genScript += "#######################################################################################################################################\n"
        genScript += "# COMPLETE GEOMETRY\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "\n"
        genScript += "simulationObj.commit_geometry()\n"
        genScript += "\n"

        # Write grid definitions.
        genScript += self.getOrderedGridDefinitionsScriptLines(itemsByClassName.get("GridSettingsItem", None))

        # Write probes definitions
        # genScript += self.getProbeDefinitionsScriptLines(itemsByClassName.get("ProbeSettingsItem", None))

        # Write NF2FF probe grid definitions.
        genScript += self.getNF2FFDefinitionsScriptLines(itemsByClassName.get("ProbeSettingsItem", None))

        genScript += "#\n"
        genScript += "# First mesh must be created on existing geometry\n"
        genScript += "#\n"
        # genScript += "simulationObj.commit_geometry()\n"
        genScript += "simulationObj.generate_mesh()\n"
        genScript += "\n"
        genScript += "\n"

        genScript += "#\n"
        genScript += "# Now follows boundary condition definition\n"
        genScript += "#\n"

        #
        #   Port are added when geometry is created because they must be meshed but then there is also needed to create boundary condition for them
        #
        for portBcScriptLine in self.portBoundaryConditionScriptLinesBuffer:
            genScript += portBcScriptLine
        genScript += "\n"

        #
        #   Genereate code to define boundary conditions
        #       - they must lay on some already existing mesh!
        #
        genScript += self.getBoundaryConditionScriptLines(itemsByClassName.get("BoundaryConditionSettingsItem", None))

        genScript += "#######################################################################################################################################\n"
        genScript += "# EXPERIMENT EXPORT MESH WITH NAMED GROUP OF MESH\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "import gmsh\n"
        genScript += "\n"
        genScript += "def createGmshNamedGroup(geometryObjName: str, groupName: str, groupTag: int = -1, useBoundary: bool = False, useSuffixToRecognizeGeometryName: bool = True):\n"
        genScript += "\tobjectTag1DList = []\n"
        genScript += "\tobjectTag2DList = []\n"
        genScript += "\tobjectTag3DList = []\n"
        genScript += "\n"
        genScript += "\tfor geometryObj in simulationObj.state.manager.geometry_list[simulationObj.modelname].values():\n"
        genScript += "\t\tif geometryObj.name == geometryObjName or geometryObj.name.startswith(geometryObjName + ('_' if useSuffixToRecognizeGeometryName else '')):\n"
        genScript += "\t\t\tfor tagTuple in (geometryObj.boundary().dimtags if useBoundary else geometryObj.dimtags):\n"
        genScript += "\t\t\t\tif tagTuple[0] == 1:\n"
        genScript += "\t\t\t\t\tobjectTag1DList.append(tagTuple[1])\n"
        genScript += "\t\t\t\tif tagTuple[0] == 2:\n"
        genScript += "\t\t\t\t\tobjectTag2DList.append(tagTuple[1])\n"
        genScript += "\t\t\t\tif tagTuple[0] == 3:\n"
        genScript += "\t\t\t\t\tobjectTag3DList.append(tagTuple[1])\n"
        genScript += "\n"
        genScript += "\tif groupTag > -1:\n"
        genScript += "\t\tgmsh.model.addPhysicalGroup(1, objectTag1DList, name=groupName, tag=groupTag)\n"
        genScript += "\t\tgmsh.model.addPhysicalGroup(2, objectTag2DList, name=groupName, tag=groupTag + 1)\n"
        genScript += "\t\tgmsh.model.addPhysicalGroup(3, objectTag3DList, name=groupName, tag=groupTag + 2)\n"
        genScript += "\telse:\n"
        genScript += "\t\tgmsh.model.addPhysicalGroup(1, objectTag1DList, name=groupName)\n"
        genScript += "\t\tgmsh.model.addPhysicalGroup(2, objectTag2DList, name=groupName)\n"
        genScript += "\t\tgmsh.model.addPhysicalGroup(3, objectTag3DList, name=groupName)\n"
        genScript += "\n"
        for objectName in set(self.createdObjectNameList):  #converting list to set make it unique, because some names could be under more categories and we want to use them just once
            genScript += f"createGmshNamedGroup('{objectName}', '{objectName}')\n"
        for objectName in set(self.createdObjectBoundaryNameList):  #converting list to set make it unique, because some names could be under more categories and we want to use them just once
            genScript += f"createGmshNamedGroup('{objectName}', '{objectName}Boundary', useBoundary=True)\n"
        genScript += "\n"
        genScript += f"simulationObj.export('{simulationName}.msh')\n"
        genScript += "\n"

        #
        #   Display model in window first as volumes, then it displays mesh.
        #
        genScript += "#######################################################################################################################################\n"
        genScript += "# DISPLAY MODEL\n"
        genScript += "#######################################################################################################################################\n"
        genScript += "simulationObj.view()\n"
        genScript += "simulationObj.view(plot_mesh=True, volume_mesh=False)\n"
        genScript += "\n"

        print("======================== REPORT END ========================\n")

        # Finalize script.

        genScript += "#######################################################################################################################################\n"
        genScript += "# RUN and save results\n"
        genScript += "#######################################################################################################################################\n"

        if self.form.generateJustPreviewCheckbox.isChecked():
            genScript += "#simulationResult = simulationObj.mw.run_sweep()\n"
            genScript += "#simulationObj.save()\n"
        else:
            genScript += "simulationResult = simulationObj.mw.run_sweep()\n"
            genScript += "simulationObj.save()\n"

        genScript += "\n"

        # Write _OpenEMS.py script file to current directory.
        currDir, nameBase = self.getCurrDir()

        if (not outputDir is None):
            fileName = f"{outputDir}/{nameBase}_emerge.py"
        else:
            fileName = f"{currDir}/{nameBase}_emerge.py"

        f = open(fileName, "w", encoding='utf-8')
        f.write(genScript)
        f.close()

        # Show message or update status bar to inform user that exporting has finished.

        self.guiHelpers.displayMessage('Simulation script written to: ' + fileName, forceModal=True)
        print('Simulation script written to: ' + fileName)

        return

    #
    #	Write NF2FF Button clicked, generate script to display far field pattern
    #
    def writeNf2ffButtonClicked(self, outputDir=None):
        genScript = ""
        genScript += "# Plot far field for structure.\n"
        genScript += "#\n"

        genScript += self.getInitScriptLines()

        genScript += "currDir = os.getcwd()\n"
        genScript += "Sim_Path = os.path.join(currDir, r'simulation_output')\n"
        genScript += "print(currDir)\n"
        genScript += "\n"

        #
        #   ATTENTION THIS IS SPECIFIC FOR FAR FIELD PLOTTING, plotFrequency and frequencies count
        #       port is calculated to get P_in (input power)
        #
        boundaryConditionObjectName = self.form.portNf2ffEmergeObjectList.currentText().split('-')[1].strip()

        cadLengthUnit = self.getFreeCADInternalUnitLengthStr()

        genScript += f"""
#######################################################################################################################################
# Farfield plot and 3D gain generated
#######################################################################################################################################
import emerge as em
import numpy as np
from emerge.plot import smith, plot_sp
import os

simulationObj = em.Simulation("{self.cadHelpers.getCurrentDocumentFileName()}", load_file=True)
simulationResult = simulationObj.data.mw

#######################################################################################################################################
# FAR FIELD PLOT
#######################################################################################################################################
mm = 0.001
currDir = os.getcwd()

#######################################################################################################################################
#   ADD BOUNDARY SELECTION SAME AS SIMULATION FILE
#######################################################################################################################################

boundary_selection = None
for geometryObj in simulationObj.state.manager.geometry_list[simulationObj.modelname].values():
	if geometryObj.name == '{boundaryConditionObjectName}' or geometryObj.name.startswith('{boundaryConditionObjectName}'):
		boundary_selection = geometryObj.boundary()

simulationObj.mw.bc.AbsorbingBoundary(boundary_selection)


# add model files into display
for geoObj in simulationObj.state.manager.geometry_list[simulationObj.modelname].values():
	simulationObj.display.add_object(geoObj)

# display far field
field = simulationResult.field.find(freq={self.form.boundaryNf2ffEmergeFreq.value()}*1e6)
ff3d = field.farfield_3d(boundary_selection, origin=({self.form.diagramPlacementXNF2FFEmerge.value()}*{cadLengthUnit}, {self.form.diagramPlacementYNF2FFEmerge.value()}*{cadLengthUnit}, {self.form.diagramPlacementZNF2FFEmerge.value()}*{cadLengthUnit}))
simulationObj.display.add_field(ff3d.surfplot('{self.form.polarizationNf2ffEmerge.currentText()}','{self.form.quantityNf2ffEmerge.currentText()}',True, dB=True, rmax={self.form.diagramRMaxNF2FFEmerge.value()}*{cadLengthUnit}, offset=({self.form.diagramPlacementXNF2FFEmerge.value()}*mm, {self.form.diagramPlacementYNF2FFEmerge.value()}*mm, {self.form.diagramPlacementZNF2FFEmerge.value()}*mm)))
simulationObj.display.show()

"""

        #
        # WRITE OpenEMS Script file into current dir
        #
        currDir, nameBase = self.getCurrDir()

        self.createOuputDir(outputDir)
        if (not outputDir is None):
            fileName = f"{outputDir}/{nameBase}_draw_NF2FF.py"
        else:
            fileName = f"{currDir}/{nameBase}_draw_NF2FF.py"

        f = open(fileName, "w", encoding='utf-8')
        f.write(genScript)
        f.close()
        print('Script to display far field written into: ' + fileName)
        self.guiHelpers.displayMessage('Script to display far field written into: ' + fileName, forceModal=False)

    #
    #	Write NF2FF Button clicked, generate script to display far field pattern
    #
    def writeFieldButtonClicked(self, outputDir=None):
        cadLengthUnit = self.getFreeCADInternalUnitLengthStr()

        genScript = ""
        genScript += "# Plot far field for structure.\n"
        genScript += "#\n"

        genScript += self.getInitScriptLines()

        genScript += "currDir = os.getcwd()\n"
        genScript += "Sim_Path = os.path.join(currDir, r'simulation_output')\n"
        genScript += "print(currDir)\n"
        genScript += "\n"

        #
        #   ATTENTION THIS IS SPECIFIC FOR FAR FIELD PLOTTING, plotFrequency and frequencies count
        #       port is calculated to get P_in (input power)
        #
        cutplaneScriptLine = ""
        if self.form.cutplaneXFieldProcessingEmerge.value() == 0.0 and self.form.cutplaneYFieldProcessingEmerge.value() == 0.0:
            cutplaneScriptLine = f"result = simulationResult.field.find(freq={self.form.frequencyFieldProcessingEmerge.value()}*1e6).cutplane({self.form.discretizationStepSizeFieldProcessingEmerge.value()}, z={self.form.cutplaneZFieldProcessingEmerge.value()}*{cadLengthUnit})"
        elif self.form.cutplaneXFieldProcessingEmerge.value() == 0.0 and self.form.cutplaneZFieldProcessingEmerge.value() == 0.0:
            cutplaneScriptLine = f"result = simulationResult.field.find(freq={self.form.frequencyFieldProcessingEmerge.value()}*1e6).cutplane({self.form.discretizationStepSizeFieldProcessingEmerge.value()}, y={self.form.cutplaneZFieldProcessingEmerge.value()}*{cadLengthUnit})"
        elif self.form.cutplaneYFieldProcessingEmerge.value() == 0.0 and self.form.cutplaneZFieldProcessingEmerge.value() == 0.0:
            cutplaneScriptLine = f"result = simulationResult.field.find(freq={self.form.frequencyFieldProcessingEmerge.value()}*1e6).cutplane({self.form.discretizationStepSizeFieldProcessingEmerge.value()}, x={self.form.cutplaneZFieldProcessingEmerge.value()}*{cadLengthUnit})"

        genScript += f"""## display field in model
#
#
import emerge as em
import numpy as np
from emerge.plot import smith, plot_sp

from emerge.plot import plot_ff, plot_ff_polar  #added for far field plot
import os

simulationObj = em.Simulation("{self.cadHelpers.getCurrentDocumentFileName()}", load_file=True)
simulationResult = simulationObj.data.mw

#######################################################################################################################################
# E FIELD PLOT
#######################################################################################################################################
mm = 0.001
currDir = os.getcwd()

# add model files into display
for geoObj in simulationObj.state.manager.geometry_list[simulationObj.modelname].values():
	simulationObj.display.add_object(geoObj, opacity=0.1)

{cutplaneScriptLine}
plot_data = result.scalar('{self.form.typeFieldProcessingEmerge.currentText()}','{self.form.metricFieldProcessingEmerge.currentText()}')
X, Y, Z, F = plot_data.xyzf
simulationObj.display.add_surf(X,Y,Z,F)				        #static field display
#simulationObj.display.animate().add_surf(X,Y,Z,F, opacity=0.7)	#animated version of display

simulationObj.display.show()

"""

        #
        # WRITE OpenEMS Script file into current dir
        #
        currDir, nameBase = self.getCurrDir()

        self.createOuputDir(outputDir)
        if (not outputDir is None):
            fileName = f"{outputDir}/{nameBase}_draw_field_{self.form.typeFieldProcessingEmerge.currentText()}.py"
        else:
            fileName = f"{currDir}/{nameBase}_draw_field_{self.form.typeFieldProcessingEmerge.currentText()}.py"

        f = open(fileName, "w", encoding='utf-8')
        f.write(genScript)
        f.close()
        print('Script to display far field written into: ' + fileName)
        self.guiHelpers.displayMessage('Script to display far field written into: ' + fileName, forceModal=False)

    def drawS11ButtonClicked(self, outputDir=None, portName=""):
        genScript = ""

        itemsByClassName = self.getItemsByClassName()
        items = itemsByClassName.get("PortSettingsItem", None)

        genScriptPortCount = 1
        portNamesAndNumbersList = {}
        for [item, currSetting] in items:
            for k in range(item.childCount()):
                childName = item.child(k).text(0)
                portName = f"{currSetting.name} - {childName}"

                # PORT openEMS GENERATION INTO VARIABLE
                if (currSetting.getType() == 'lumped'):
                    portNamesAndNumbersList[portName] = genScriptPortCount
                    genScriptPortCount += 1

        sourcePortName = self.form.drawS11Port.currentText()
        sourcePortNumber = portNamesAndNumbersList[sourcePortName]

        genScript += f"## EMerge simulation - S{sourcePortNumber}{sourcePortNumber}\n"
        genScript += "#\n"
        genScript += "#\n"
        genScript += "import emerge as em\n"
        genScript += "import numpy as np\n"
        genScript += "from emerge.plot import smith, plot_sp\n"
        genScript += "\n"

        simulationName = self.cadHelpers.getCurrentDocumentFileName()
        genScript += f"simulationObj = em.Simulation(\"{simulationName}\", load_file=True)\n"
        genScript += "simulationResult = simulationObj.data.mw\n"
        genScript += "\n"

        #
        #   Get port names and their numbers from GUI
        #
        genScript += "###############################################################################\n"
        genScript += "# PORT NAME AND THEIR NUMBERS LIST\n"
        genScript += "###############################################################################\n"
        genScript += "portNamesAndNumbersList = {}\n"
        for portName, portNumber in portNamesAndNumbersList.items():
            genScript += f'portNamesAndNumbersList["{portName}"] = {portNumber}\n'
        genScript += "\n"

        genScript += "###############################################################################\n"
        genScript += "# PLOT S DATA\n"
        genScript += "###############################################################################\n"
        genScript += f"sourcePortName = '{sourcePortName}'\n"
        genScript += "sourcePortNumber = portNamesAndNumbersList[sourcePortName]\n"
        genScript += "\n"
        genScript += "freqs = simulationResult.scalar.grid.freq\n"
        genScript += "fmin = freqs.min()\n"
        genScript += "fmax = freqs.max()\n"
        genScript += "freq_dense = np.linspace(fmin, fmax, 1001)\n"
        genScript += "S_data = simulationResult.scalar.grid.model_S(sourcePortNumber, sourcePortNumber, freq_dense)  #reflection coefficient\n"
        genScript += "plotLabel = f'S{sourcePortNumber}{sourcePortNumber} ({sourcePortName})'\n"
        genScript += "plot_sp(freq_dense, S_data)  #plot return loss in dB\n"
        genScript += f"smith(S_data, f=freq_dense, labels=plotLabel)  #smith chart\n"
        genScript += "\n"

        #
        # WRITE OpenEMS Script file into current dir
        #
        currDir, nameBase = self.getCurrDir()

        self.createOuputDir(outputDir)
        if (not outputDir is None):
            fileName = f"{outputDir}/{nameBase}_draw_S{sourcePortNumber}{sourcePortNumber}.py"
        else:
            fileName = f"{currDir}/{nameBase}_draw_S{sourcePortNumber}{sourcePortNumber}.py"

        f = open(fileName, "w", encoding='utf-8')
        f.write(genScript)
        f.close()
        print('Draw result from simulation file written into: ' + fileName)
        self.guiHelpers.displayMessage('Draw result from simulation file written into: ' + fileName, forceModal=False)

    def drawS21ButtonClicked(self, outputDir=None, sourcePortName="", targetPortName=""):
        genScript = ""

        itemsByClassName = self.getItemsByClassName()
        items = itemsByClassName.get("PortSettingsItem", None)

        genScriptPortCount = 1
        portNamesAndNumbersList = {}
        for [item, currSetting] in items:
            for k in range(item.childCount()):
                childName = item.child(k).text(0)
                portName = f"{currSetting.name} - {childName}"

                # PORT openEMS GENERATION INTO VARIABLE
                if (currSetting.getType() == 'lumped'):
                    portNamesAndNumbersList[portName] = genScriptPortCount
                    genScriptPortCount += 1

        sourcePortNumber = portNamesAndNumbersList[sourcePortName]
        targetPortNumber = portNamesAndNumbersList[targetPortName]
        sourcePortName = self.form.drawS21Source.currentText()
        targetPortName = self.form.drawS21Target.currentText()

        #
        #   Generate script plotting S21 from source port to output port
        #
        genScript += f"## EMerge simulation - S{targetPortNumber}{sourcePortNumber}\n"
        genScript += f"#\ttransfer from '{sourcePortName}' -> '{targetPortName}'\n"
        genScript += "#\n"
        genScript += "#\n"
        genScript += "import emerge as em\n"
        genScript += "import numpy as np\n"
        genScript += "from emerge.plot import smith, plot_sp\n"
        genScript += "\n"

        simulationName = self.cadHelpers.getCurrentDocumentFileName()
        genScript += f"simulationObj = em.Simulation(\"{simulationName}\", load_file=True)\n"
        genScript += "simulationResult = simulationObj.data.mw\n"
        genScript += "\n"

        #
        #   Get port names and their numbers from GUI
        #
        genScript += "###############################################################################\n"
        genScript += "# PORT NAME AND THEIR NUMBERS LIST\n"
        genScript += "###############################################################################\n"
        genScript += "portNamesAndNumbersList = {}\n"
        for portName, portNumber in portNamesAndNumbersList.items():
            genScript += f'portNamesAndNumbersList["{portName}"] = {portNumber}\n'
        genScript += "\n"

        # --- Post-process S-parameters ------------------------------------------
        genScript += "###############################################################################\n"
        genScript += "# PLOT S DATA\n"
        genScript += "###############################################################################\n"
        genScript += f"sourcePortName = '{sourcePortName}'\n"
        genScript += f"targetPortName = '{targetPortName}'\n"
        genScript += "sourcePortNumber = portNamesAndNumbersList[sourcePortName]\n"
        genScript += "targetPortNumber = portNamesAndNumbersList[targetPortName]\n"
        genScript += "\n"
        genScript += "freqs = simulationResult.scalar.grid.freq\n"
        genScript += "fmin = freqs.min()\n"
        genScript += "fmax = freqs.max()\n"
        genScript += "freq_dense = np.linspace(fmin, fmax, 1001)\n"
        genScript += "S_data = simulationResult.scalar.grid.model_S(sourcePortNumber, targetPortNumber, freq_dense)  # reflection coefficient\n"

        genScript += "plotLabel = f'S{sourcePortNumber}{targetPortNumber} ({sourcePortName} -> {targetPortName})'\n"
        genScript += f"plot_sp(freq_dense, S_data, labels=plotLabel)  # plot return loss in dB\n"
        genScript += f"smith(S_data, f=freq_dense, labels=plotLabel)  # smith chart\n"
        genScript += "\n"

        #
        # WRITE OpenEMS Script file into current dir
        #
        currDir, nameBase = self.getCurrDir()

        self.createOuputDir(outputDir)
        if (not outputDir is None):
            fileName = f"{outputDir}/{nameBase}_draw_S{targetPortNumber}{sourcePortNumber}.py"
        else:
            fileName = f"{currDir}/{nameBase}_draw_S{targetPortNumber}{sourcePortNumber}.py"

        f = open(fileName, "w", encoding='utf-8')
        f.write(genScript)
        f.close()

        print('Draw result from simulation file written to: ' + fileName)
        self.guiHelpers.displayMessage('Draw result from simulation file written to: ' + fileName, forceModal=False)
