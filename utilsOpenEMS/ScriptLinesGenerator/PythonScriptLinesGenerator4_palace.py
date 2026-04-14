#   author: Lubomir Jagos
#
#
import os
from PySide import QtGui, QtCore, QtWidgets
import numpy as np
import re
import math

from utilsOpenEMS.GlobalFunctions.GlobalFunctions import _bool, _r, _r2
from utilsOpenEMS.GuiHelpers.FactoryCadInterface import FactoryCadInterface
from utilsOpenEMS.ScriptLinesGenerator.PythonScriptLinesGenerator3_emerge import PythonScriptLinesGenerator3_emerge

class PythonScriptLinesGenerator4_palace(PythonScriptLinesGenerator3_emerge):

    _gmshGroupId = {}

    #
    #   constructor, get access to form GUI
    #
    def __init__(self, form, statusBar = None):
        super(PythonScriptLinesGenerator4_palace, self).__init__(form, statusBar)

    def generateSimulationScript(self, outputDir=None):
        self.generatePalaceScript(outputDir)

    def generatePalaceScript(self, outputDir=None):
        self.portBoundaryConditionScriptLinesBuffer = []
        self.createdObjectNameList = []
        self.createdObjectBoundaryNameList = []
        self._gmshGroupId = {}

        # Create outputDir relative to local FreeCAD file if output dir does not exists
        #   if outputDir is set to same value
        #   if outputStr is None then folder with name as FreeCAD file with suffix _openEMS_simulation is created
        outputDir = self.createOuputDir(outputDir)

        # Update status bar to inform user that exporting has begun.
        if self.statusBar is not None:
            self.statusBar.showMessage("Generating Palace script and geometry files ...", 5000)
            QtWidgets.QApplication.processEvents()

        # Constants and variable initialization.
        #
        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        refUnitStr = self.form.simParamsDeltaUnitList.currentText()
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        simulationName = self.cadHelpers.getCurrentDocumentFileName()
        simulationOutputMeshFile = self.form.simParamsModelMeshName_palace.text()
        simulationOutputDirectory = self.form.simParamsOutputDirectory_palace.text()
        simParamsVerbose_palace = self.form.simParamsVerbose_palace.value()
        simulationProblemType = self.form.simParamsSimulationTypeList_palace.currentText()
        simParamsModelMeshBaseUnits_palace = self.form.simParamsModelMeshBaseUnits_palace.currentText()

        linearSolverType = self.form.simParamsLinearSolverType_palace.currentText()
        linearSolverTolerance = self.form.simParamsLinearSolverTolerance_palace.value()
        linearSolverMaxIterationCount = self.form.simParamsLinearSolverMaximumIterationCount_palace.value()
        linearSolverKSPType = self.form.simParamsLinearSolverKSPType_palace.currentText()

        solverOrder = self.form.simParamsLinearSolverOrder_palace.value()
        solverDevice = self.form.simParamsSolverDevice_palace.currentText()


        # List categories and items.
        #
        itemsByClassName = self.getItemsByClassName()

        # Write script header.
        #
        genScript = ""

        genScript += "## Palace simulation\n"
        genScript += "#\n"
        genScript += "#\n"

        genScript += "\n"
        genScript += "currDir = os.getcwd()\n"
        genScript += "print(currDir)\n"
        genScript += "\n"
        genScript += "\n"

        genScript += "import gmsh\n"
        genScript += "import os\n"
        genScript += "import json\n"
        genScript += "from basicpalacesolverhelperpackage import BasicMfemMesher\n"
        genScript += "\n"

        genScript += "# --- Unit definitions -----------------------------------------------------\n"
        genScript += "m = 1.0\n"
        genScript += "cm = 0.01\n"
        genScript += "mm = 0.001  # meters per millimeter\n"
        genScript += "um = 0.000001\n"
        genScript += "nm = 0.000000001\n"
        genScript += "\n"

        genScript += "##########################################################################################################\n"
        genScript += "# MAIN PROGRAM\n"
        genScript += "##########################################################################################################\n"
        genScript += "gmsh.initialize()\n"
        genScript += f"gmsh.model.add('{simulationName}')\n"
        genScript += "\n"
        genScript += "mesherObj = BasicMfemMesher()\n"
        genScript += "\n"
        genScript += "##########################################################################################################\n"
        genScript += "# GEOMETRY\n"
        genScript += "##########################################################################################################\n"
        # genScript += "mesherObj.addStepfile('substrate', 'stepfiles/substrate.step', priority=2000)\n"
        genScript += self.getMaterialDefinitionsScriptLines(itemsByClassName.get("MaterialSettingsItem", None), outputDir)
        genScript += self.getBoundaryConditionObjectImportScriptLines(itemsByClassName.get("BoundaryConditionSettingsItem", None), outputDir)
        genScript += "\n"

        genScript += "#\n"
        genScript += "# Create continuous mesh, subtract objects between each other based on their priority and perform fragmentation, reassing internal gmsh tags to objects\n"
        genScript += "#\n"
        genScript += "gmsh.model.occ.synchronize()\n"
        genScript += "#mesherObj.cutVolumesInsideModel()\n"
        genScript += "mesherObj.cutOnlyVolumesInModelBetweenEachOther(allowSurfacesToBeCutted=True)\n"
        genScript += "gmsh.model.occ.removeAllDuplicates()\n"
        genScript += "gmsh.model.occ.synchronize()\n"
        genScript += "mesherObj.performFragmentationAndReassignTags()\n"
        genScript += "gmsh.model.occ.synchronize()\n"
        genScript += "gmsh.fltk.run()\n"
        genScript += "\n"

        genScript += self.getOrderedGridDefinitionsScriptLines(itemsByClassName.get("GridSettingsItem", None))

        genScript += "##########################################################################################################\n"
        genScript += "# Define physical groups for volumes and surfaces\n"
        genScript += "##########################################################################################################\n"
        genScript += "gmshGroupId = {}\n"
        genScript += "#gmshGroupId[\"airbox_volume\"] = 1\n"
        genScript += "#gmshGroupId[\"port_in\"] = 2000\n"
        genScript += "#gmshGroupId[\"coil\"] = 3000\n"
        genScript += "\n"
        genScript += "#mesherObj.createGroup(\"airbox\", \"airbox\", 3)\n"
        genScript += "#mesherObj.createGroup(\"coil\", \"coil\", 2, groupTag=gmshGroupId[\"coil\"])\n"
        genScript += "#mesherObj.createGroup(\"port_in\", \"port_in\", 2, groupTag=gmshGroupId[\"port_in\"])\n"
        genScript += "\n"

        genScript += "##########################################################################################################\n"
        genScript += "# MESH GENERATE\n"
        genScript += "##########################################################################################################\n"
        genScript += "# gmsh directives\n"
        genScript += "gmsh.option.setNumber(\"General.Terminal\", 1)  # print messages\n"
        genScript += "gmsh.option.setNumber(\"Mesh.MshFileVersion\", 2.2)\n"
        genScript += "gmsh.option.setNumber(\"Mesh.Binary\", 0)  # text .msh file\n"
        genScript += "# gmsh.option.setNumber(\"Mesh.Algorithm3D\", 10)\n"
        genScript += "gmsh.option.setNumber(\"Mesh.Algorithm3D\", 1)  # delaunay\n"
        genScript += "\n"
        genScript += "gmsh.model.occ.removeAllDuplicates()\n"
        genScript += "gmsh.model.occ.synchronize()\n"
        genScript += "\n"

        genScript += "# Generate mesh\n"
        genScript += "gmsh.model.mesh.generate(3)\n"
        genScript += "try:\n"
        genScript += "\tos.mkdir('mesh')\n"
        genScript += "except:\n"
        genScript += "\tpass\n"
        genScript += f"gmsh.write('{simulationOutputMeshFile}')\n"
        genScript += "\n"
        genScript += f"print('PASS - Mesh generated and saved as {simulationOutputMeshFile}')\n"
        genScript += "\n"
        genScript += "##########################################################################################################\n"
        genScript += "# Open generated msh file\n"
        genScript += "##########################################################################################################\n"
        genScript += "gmsh.fltk.run()\n"
        genScript += "\n"
        genScript += "gmsh.clear()\n"
        genScript += "gmsh.finalize()\n"
        genScript += "\n"
        genScript += "##########################################################################################################\n"
        genScript += "# Generate Palace solver simulation .json file\n"
        genScript += "##########################################################################################################\n"
        genScript += "simulationConfig = {}\n"
        genScript += "\n"
        genScript += 'simulationConfig["Problem"] = {}\n'
        genScript += f'simulationConfig["Problem"]["Type"] = "{simulationProblemType}"\n'
        genScript += f'simulationConfig["Problem"]["Verbose"] = {simParamsVerbose_palace}\n'
        genScript += f'simulationConfig["Problem"]["Output"] = "{simulationOutputDirectory}"\n'
        genScript += '\n'
        genScript += 'simulationConfig["Model"] = {}\n'
        genScript += f'simulationConfig["Model"]["Mesh"] = "{simulationOutputMeshFile}"\n'
        genScript += f'simulationConfig["Model"]["L0"] = {simParamsModelMeshBaseUnits_palace}\n'
        genScript += '\n'



        genScript += 'simulationConfig["Domains"] = {}\n'
        genScript += 'simulationConfig["Domains"]["Materials"] = []\n'
        genScript += 'for materialName, materialAttributes in materialList:\n'
        genScript += '\tsimulationConfig["Domains"]["Materials"].append({\n'
        genScript += '\t\t"Attributes": [",".join(gmshGroupId[materialName])],\n'
        genScript += '\t\t"Permeability": 1.0\n'
        genScript += '\t})\n'



        # genScript += '\n'
        # genScript += 'simulationConfig["Domains"]["Postprocessing"] = {}\n'
        # genScript += 'simulationConfig["Domains"]["Postprocessing"]["Probe"] = []\n'
        # genScript += 'simulationConfig["Domains"]["Postprocessing"]["Probe"].append({\n'
        # genScript += '\t"Index": 1,\n'
        # genScript += '\t"Center": [0.0, 0.0, 0.004]\n'
        # genScript += '})\n'
        # genScript += 'simulationConfig["Domains"]["Postprocessing"]["Energy"] = []\n'
        # genScript += 'simulationConfig["Domains"]["Postprocessing"]["Energy"].append({\n'
        # genScript += '\t"Index": 1,\n'
        # genScript += '\t"Attributes": [gmshGroupId["airbox_volume"]]\n'
        # genScript += '})\n'
        # genScript += '\n'




        genScript += 'simulationConfig["Boundaries"] = {}\n'
        genScript += 'for boundaryName, boundaryAttributes in boundaryConditionList:\n'
        genScript += f'\tsimulationConfig["Boundaries"][boundaryName] = \n'
        genScript += '\t\t"Attributes": [",".join(gmshGroupId[boundaryName+"_boundary"])]\n'
        genScript += '\t}\n'

        # genScript += 'simulationConfig["Boundaries"]["SurfaceCurrent"] = []\n'
        # genScript += 'simulationConfig["Boundaries"]["SurfaceCurrent"].append({\n'
        # genScript += '\t"Index": 1,\n'
        # genScript += '\t"Attributes": [gmshGroupId["port_in"]],\n'
        # genScript += '\t"Direction": [0.0, 0.0, 1.0]\n'
        # genScript += '})\n'
        # genScript += '\n'





        genScript += 'simulationConfig["Solver"] = {}\n'
        genScript += 'simulationConfig["Solver"]["Linear"] = {}\n'
        genScript += f'simulationConfig["Solver"]["Linear"]["Type"] = "{linearSolverType}"\n'
        genScript += f'simulationConfig["Solver"]["Linear"]["KSPType"] = "{linearSolverKSPType}"\n'
        genScript += f'simulationConfig["Solver"]["Linear"]["Tol"] = {linearSolverTolerance}\n'
        genScript += f'simulationConfig["Solver"]["Linear"]["MaxIts"] = {linearSolverMaxIterationCount}\n'
        genScript += f'simulationConfig["Solver"]["Order"] = {solverOrder}\n'
        genScript += f'simulationConfig["Solver"]["Device"] = "{solverDevice}"\n'

        genScript += 'simulationConfig["Solver"]["Magnetostatic"] = {}\n'
        genScript += 'simulationConfig["Solver"]["Magnetostatic"]["Save"] = 2\n'
        genScript += '\n'

        currDir, nameBase = self.getCurrDir()

        genScript += f'json.dump(simulationConfig, open("{nameBase}.json", "w"), indent=2)\n'
        genScript += '\n'

        ##################################################################################
        # Write _OpenEMS.py script file to current directory.
        ##################################################################################
        if (not outputDir is None):
            fileName = f"{outputDir}/{nameBase}_palace.py"
        else:
            fileName = f"{currDir}/{nameBase}_palace.py"

        f = open(fileName, "w", encoding='utf-8')
        f.write(genScript)
        f.close()

        # Show message or update status bar to inform user that exporting has finished.

        self.guiHelpers.displayMessage('Simulation script written to: ' + fileName, forceModal=True)
        print('Simulation script written to: ' + fileName)

        return

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
                genScript += materialPythonVariable + " = {}\n"

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
                        genScript += f"{materialPythonVariable}['er'] = {str(currSetting.constants['epsilon'])}\n"
                    if str(currSetting.constants['mue']) != "0":
                        genScript += f"{materialPythonVariable}['mue'] = {str(currSetting.constants['mue'])}\n"
                    if ("tand" in currSetting.constants) \
                       and type(currSetting.constants['tand']) is float:
                            genScript += f"{materialPythonVariable}['tand'] = {str(currSetting.constants['tand'])}\n"
                    if str(currSetting.constants['sigma']) != "0":
                        genScript += f"{materialPythonVariable}['cond'] = {str(currSetting.constants['sigma'])}\n"

                # first print all current material children names
                for k in range(item.childCount()):
                    childName = item.child(k).text(0)
                    print("##Children:")
                    print("\t" + childName)

                # now export material children, if it's object export as STL, if it's curve export as curve
                genScript += f"{materialPythonVariable}['objects'] = []\n"
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
                    #   Going through each concrete material items and generate their .step files
                    #
                    currDir, baseName = self.getCurrDir()
                    stepModelFileName = childName + "_gen_model.step"

                    genScript += f"mesherObj.addStepfile('{childName}', os.path.join(currDir, 'stepfiles', '{stepModelFileName}'), priority={objModelPriority})\n"
                    genScript += f"{materialPythonVariable}['objects'].append('{childName}')\n"

                    #output directory path construction, if there is no parameter for output dir then output is in current freecad file dir
                    if (not outputDir is None):
                        stepfileOutputDir = os.path.join(outputDir, 'stepfiles')
                        try:
                            os.makedirs(stepfileOutputDir)
                        except:
                            pass
                        exportFileName = os.path.join(stepfileOutputDir, stepModelFileName)
                    else:
                        stepfileOutputDir = os.path.join(currDir, 'stepfiles')
                        try:
                            os.makedirs(stepfileOutputDir)
                        except:
                            pass
                        exportFileName = os.path.join(stepfileOutputDir, stepModelFileName)

                    self.cadHelpers.exportSTEP([freeCadObj], exportFileName)
                    print("Material object exported as STEP into: " + stepModelFileName)

                genScript += "\n"   #newline after each COMPLETE material category code generated

            genScript += "\n"

        return genScript

    def getBoundaryConditionObjectImportScriptLines(self, items, outputDir=None, generateObjects=True):
        genScript = ""

        genScript += "# Imported objects used as boundary conditions\n"
        genScript += "#\n"
        boundaryPythonVariable = "boundaryConditionList"
        genScript += f"{boundaryPythonVariable} = []\n"
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

                #
                #   Going through each concrete material items and generate their .step files
                #
                currDir, baseName = self.getCurrDir()
                stepModelFileName = childName + "_gen_model.step"

                genScript += f"mesherObj.addStepfile('{childName}', os.path.join(currDir, 'stepfiles', '{stepModelFileName}'), priority={objModelPriority})\n"
                genScript += f"{boundaryPythonVariable}.append({{'name': '{childName}', 'type': ''}})\n"

                #output directory path construction, if there is no parameter for output dir then output is in current freecad file dir
                if (not outputDir is None):
                    stepfileOutputDir = os.path.join(outputDir, 'stepfiles')
                    try:
                        os.makedirs(stepfileOutputDir)
                    except:
                        pass
                    exportFileName = os.path.join(stepfileOutputDir, stepModelFileName)
                else:
                    stepfileOutputDir = os.path.join(currDir, 'stepfiles')
                    try:
                        os.makedirs(stepfileOutputDir)
                    except:
                        pass
                    exportFileName = os.path.join(stepfileOutputDir, stepModelFileName)



                self.cadHelpers.exportSTEP([freeCadObj], exportFileName)
                print("Boundary condition object exported as STEP into: " + stepModelFileName)

            genScript += "\n"   #newline after each COMPLETE material category code generated

        return genScript

    def getOrderedGridDefinitionsScriptLines(self, items):
        genScript = ""
        meshPrioritiesCount = self.form.meshPriorityTreeView.topLevelItemCount()

        if (not items) or (meshPrioritiesCount == 0):
            return genScript

        refUnit = self.getUnitLengthFromUI_m()  # Coordinates need to be given in drawing units
        refUnitStr = self.form.simParamsDeltaUnitList.currentText()
        sf = self.getFreeCADUnitLength_m() / refUnit  # scaling factor for FreeCAD units to drawing units

        genScript += "##########################################################################################################\n"
        genScript += "# MESH SIZE DEFINITION\n"
        genScript += "##########################################################################################################\n"
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
                    # genScript += f"\t\t\tsimulationObj.mesher.set_size(geometryObj, {gridSettingsInst.femMesh['femMaxElementSize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                    genScript += "#TODO: femUseMaxElementSize not implemented yet!\n"
                if gridSettingsInst.femMesh['femUseMaxBoundarySize'] == True:
                    # genScript += f"\t\t\tsimulationObj.mesher.set_boundary_size(geometryObj, {gridSettingsInst.femMesh['femMaxBoundarySize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                genScript += "#TODO: femUseMaxBoundarySize not implemented yet!\n"
                if gridSettingsInst.femMesh['femUseMaxFaceSize'] == True:
                    # genScript += f"\t\t\tsimulationObj.mesher.set_face_size(geometryObj, {gridSettingsInst.femMesh['femMaxFaceSize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                    genScript += f"\t\t\tmesherObj.setSizeOnFace(\"{FreeCADObjectName}\", {gridSettingsInst.femMesh['femMaxFaceSize']})\n"
                if gridSettingsInst.femMesh['femUseMaxDomainSize'] == True:
                    # genScript += f"\t\t\tsimulationObj.mesher.set_domain_size(geometryObj, {gridSettingsInst.femMesh['femMaxDomainSize']} * {gridSettingsInst.femMesh['femMaxSizeUnits']})\n"
                    genScript += "#TODO: femUseMaxDomainSize not implemented yet!\n"

                #
                #   TODO: Add user defined mesh, code block will be placed into code
                #

                genScript += f"\n"

            genScript += "\n"

        genScript += "# Set background field automaticaly using internal field list created during mesh size definition\n"
        genScript += "mesherObj.setBackgroundMinFieldUsingAllDefinedFields()\n"
        genScript += "\n"
        genScript += "# Global limits - use if needed\n"
        genScript += "#gmsh.option.setNumber(\"Mesh.MeshSizeMin\", 0.1)  # Absolute minimum\n"
        genScript += "#gmsh.option.setNumber(\"Mesh.MeshSizeMax\", 10.0)  # Absolute maximum\n"
        genScript += "\n"

        return genScript



