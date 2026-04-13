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

        genScript += "# Generate mesh\n"
        genScript += "gmsh.model.mesh.generate(3)\n"
        genScript += "try:\n"
        genScript += "\tos.mkdir('mesh')\n"
        genScript += "except:\n"
        genScript += "\tpass\n"
        genScript += "gmsh.write('mesh/simulation_model.msh')\n"
        genScript += "\n"
        genScript += "print('PASS - Mesh generated and saved as mesh/simulation_model.msh')\n"
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
        genScript += 'simulationConfig["Problem"]["Type"] = "Magnetostatic"\n'
        genScript += 'simulationConfig["Problem"]["Verbose"] = 3\n'
        genScript += 'simulationConfig["Problem"]["Output"] = "sim_results_2"\n'
        genScript += '\n'
        genScript += 'simulationConfig["Model"] = {}\n'
        genScript += 'simulationConfig["Model"]["Mesh"] = "simulation_config/coil_model.msh"\n'
        genScript += 'simulationConfig["Model"]["L0"] = 1.0e-3\n'
        genScript += '\n'
        genScript += 'simulationConfig["Domains"] = {}\n'
        genScript += 'simulationConfig["Domains"]["Materials"] = []\n'
        genScript += 'simulationConfig["Domains"]["Materials"].append({\n'
        genScript += '\t"Attributes": [gmshGroupId["airbox_volume"]],\n'
        genScript += '\t"Permeability": 1.0\n'
        genScript += '})\n'
        genScript += '\n'
        genScript += 'simulationConfig["Domains"]["Postprocessing"] = {}\n'
        genScript += 'simulationConfig["Domains"]["Postprocessing"]["Probe"] = []\n'
        genScript += 'simulationConfig["Domains"]["Postprocessing"]["Probe"].append({\n'
        genScript += '\t"Index": 1,\n'
        genScript += '\t"Center": [0.0, 0.0, 0.004]\n'
        genScript += '})\n'
        genScript += 'simulationConfig["Domains"]["Postprocessing"]["Energy"] = []\n'
        genScript += 'simulationConfig["Domains"]["Postprocessing"]["Energy"].append({\n'
        genScript += '\t"Index": 1,\n'
        genScript += '\t"Attributes": [gmshGroupId["airbox_volume"]]\n'
        genScript += '})\n'
        genScript += '\n'
        genScript += 'simulationConfig["Boundaries"] = {}\n'
        genScript += 'simulationConfig["Boundaries"]["PEC"] = {\n'
        genScript += '\t"Attributes": [gmshGroupId["coil"]]\n'
        genScript += '}\n'
        genScript += 'simulationConfig["Boundaries"]["SurfaceCurrent"] = []\n'
        genScript += 'simulationConfig["Boundaries"]["SurfaceCurrent"].append({\n'
        genScript += '\t"Index": 1,\n'
        genScript += '\t"Attributes": [gmshGroupId["port_in"]],\n'
        genScript += '\t"Direction": [0.0, 0.0, 1.0]\n'
        genScript += '})\n'
        genScript += '\n'
        genScript += 'simulationConfig["Solver"] = {}\n'
        genScript += 'simulationConfig["Solver"]["Linear"] = {}\n'
        genScript += 'simulationConfig["Solver"]["Linear"]["Type"] = "AMS"\n'
        genScript += 'simulationConfig["Solver"]["Linear"]["KSPType"] = "GMRES"\n'
        genScript += 'simulationConfig["Solver"]["Linear"]["Tol"] = 1e-3\n'
        genScript += 'simulationConfig["Solver"]["Linear"]["MaxIts"] = 100\n'
        genScript += 'simulationConfig["Solver"]["Order"] = 2\n'
        genScript += 'simulationConfig["Solver"]["Device"] = "CPU"\n'
        genScript += 'simulationConfig["Solver"]["Magnetostatic"] = {}\n'
        genScript += 'simulationConfig["Solver"]["Magnetostatic"]["Save"] = 2\n'
        genScript += '\n'
        genScript += 'json.dump(simulationConfig, open("magnetostatic_analysis_2.json", "w"), indent=2)\n'
        genScript += '\n'



        ##################################################################################
        # Write _OpenEMS.py script file to current directory.
        ##################################################################################
        currDir, nameBase = self.getCurrDir()

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
