from PySide import QtGui, QtCore
import FreeCAD as App
import FreeCADGui, Part, os
import re
import Draft
import random
import numpy as np
import collections
import math

from PySide.QtCore import QSettings
import json	

#import needed local classes
import sys
sys.path.insert(0, os.path.dirname(__file__))

from utilsOpenEMS.OpenEMS import OpenEMS

from utilsOpenEMS.SettingsItem.SettingsItem import SettingsItem
from utilsOpenEMS.SettingsItem.PortSettingsItem import PortSettingsItem
from utilsOpenEMS.SettingsItem.ExcitationSettingsItem import ExcitationSettingsItem
from utilsOpenEMS.SettingsItem.LumpedPartSettingsItem import LumpedPartSettingsItem
from utilsOpenEMS.SettingsItem.MaterialSettingsItem import MaterialSettingsItem
from utilsOpenEMS.SettingsItem.SimulationSettingsItem import SimulationSettingsItem
from utilsOpenEMS.SettingsItem.GridSettingsItem import GridSettingsItem
from utilsOpenEMS.SettingsItem.FreeCADSettingsItem import FreeCADSettingsItem

from utilsOpenEMS.ScriptLinesGenerator.OctaveScriptLinesGenerator import OctaveScriptLinesGenerator

from utilsOpenEMS.FreeCADDocObserver import FreeCADDocObserver

from utilsOpenEMS.GuiHelpers.GuiHelpers import GuiHelpers

# UI file (use Qt Designer to modify)
path_to_ui = "./ui/dialog.ui"
from utilsOpenEMS.GlobalFunctions.GlobalFunctions import _bool, _r

#
# Main GUI panel class
#
class ExportOpenEMSDialog():
	def __del__(self):
		return
		
	def finished(self):
		self.observer.endObservation()
		self.observer = None

	def __init__(self):

		#
		# LOCAL OPENEMS OBJECT
		#
		self.openEMSObj = OpenEMS()

		#
		# Change current path to script file folder
		#
		abspath = os.path.abspath(__file__)
		dname = os.path.dirname(abspath)
		os.chdir(dname)

		# this will create a Qt widget from our ui file
		self.form = FreeCADGui.PySideUic.loadUi(path_to_ui)
		self.form.finished.connect(self.finished)
		
		# add a statusBar widget (comment to revert to QMessageBox if there are any problems)
		self.statusBar = QtGui.QStatusBar()
		self.statusBar.setStyleSheet("QStatusBar{border-top: 1px outset grey;}")
		self.form.dialogVertLayout.addWidget(self.statusBar)

		#
		# instantiate OCTAVE script generator using this dialog form
		#
		self.octaveScriptGenerator = OctaveScriptLinesGenerator(self.form, statusBar = self.statusBar)

		#
		# GUI helpers function like display message box and so
		#
		self.guiHelpers = GuiHelpers(self.form, statusBar = self.statusBar)

		#
		# TOP LEVEL ITEMS / Category Items (excitation, grid, materials, ...)
		#
		self.initRightColumnTopLevelItems()

		#select first item
		topItem = self.form.objectAssignmentRightTreeWidget.itemAt(0,0)
		self.form.objectAssignmentRightTreeWidget.setCurrentItem(topItem)

		self.form.moveLeftButton.clicked.connect(self.onMoveLeft)
		self.form.moveRightButton.clicked.connect(self.onMoveRight)
		
		#########################################################################################################
		#	Left Column - FreeCAD objects list
		#########################################################################################################

		self.initLeftColumnTopLevelItems()	
		self.form.objectAssignmentLeftTreeWidget.itemDoubleClicked.connect(self.objectAssignmentLeftTreeWidgetItemDoubleClicked)	
		
		#########################################################################################################
		#	RIGHT COLUMN - Simulation Object Assignment
		#########################################################################################################
		
		self.form.objectAssignmentRightTreeWidget.itemSelectionChanged.connect(self.objectAssignmentRightTreeWidgetItemSelectionChanged)
		
		self.form.objectAssignmentRightTreeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)  
		self.form.objectAssignmentRightTreeWidget.customContextMenuRequested.connect(self.objectAssignmentRightTreeWidgetContextClicked)
		self.form.objectAssignmentRightTreeWidget.itemDoubleClicked.connect(self.objectAssignmentRightTreeWidgetItemDoubleClicked)

		#########################################################################################################
		#########################################################################################################
		#########################################################################################################

		#
		# SETTINGS FOR BUTTONS CLICK, functions assignments
		#
		self.form.gridSettingsAddButton.clicked.connect(self.gridSettingsAddButtonClicked)
		self.form.gridSettingsRemoveButton.clicked.connect(self.gridSettingsRemoveButtonClicked)
		self.form.gridSettingsUpdateButton.clicked.connect(self.gridSettingsUpdateButtonClicked)

		self.form.materialSettingsAddButton.clicked.connect(self.materialSettingsAddButtonClicked)
		self.form.materialSettingsRemoveButton.clicked.connect(self.materialSettingsRemoveButtonClicked)
		self.form.materialSettingsUpdateButton.clicked.connect(self.materialSettingsUpdateButtonClicked)

		self.form.excitationSettingsAddButton.clicked.connect(self.excitationSettingsAddButtonClicked)
		self.form.excitationSettingsRemoveButton.clicked.connect(self.excitationSettingsRemoveButtonClicked)
		self.form.excitationSettingsUpdateButton.clicked.connect(self.excitationSettingsUpdateButtonClicked)

		self.form.portSettingsAddButton.clicked.connect(self.portSettingsAddButtonClicked)
		self.form.portSettingsRemoveButton.clicked.connect(self.portSettingsRemoveButtonClicked)
		self.form.portSettingsUpdateButton.clicked.connect(self.portSettingsUpdateButtonClicked)

		self.form.lumpedPartSettingsAddButton.clicked.connect(self.lumpedPartSettingsAddButtonClicked)
		self.form.lumpedPartSettingsRemoveButton.clicked.connect(self.lumpedPartSettingsRemoveButtonClicked)
		self.form.lumpedPartSettingsUpdateButton.clicked.connect(self.lumpedPartSettingsUpdateButtonClicked)

		#
		# Handle function for grid radio buttons click
		#
		self.form.userDefinedRadioButton.clicked.connect(self.userDefinedRadioButtonClicked)
		self.form.fixedCountRadioButton.clicked.connect(self.fixedCountRadioButtonClicked)
		self.form.fixedDistanceRadioButton.clicked.connect(self.fixedDistanceRadioButtonClicked)

		# Handle function for MATERIAL RADIO BUTTONS
		self.form.materialUserDefinedRadioButton.toggled.connect(self.materialUserDeinedRadioButtonToggled)	

		#
		# Clicked on "Generate OpenEMS Script"
		#		
		self.form.generateOpenEMSScriptButton.clicked.connect(self.octaveScriptGenerator.generateOpenEMSScriptButtonClicked)

		#
		# Clicked on BUTTONS FOR OBJECT PRIORITIES
		#		
		self.form.moveupPriorityButton.clicked.connect(self.moveupPriorityButtonClicked)
		self.form.movedownPriorityButton.clicked.connect(self.movedownPriorityButtonClicked)

		#
		# Clicked on BUTTONS FOR MESH PRIORITIES
		#		
		self.form.moveupMeshPriorityButton.clicked.connect(self.moveupPriorityMeshButtonClicked)
		self.form.movedownMeshPriorityButton.clicked.connect(self.movedownPriorityMeshButtonClicked)

		#
		#	Octave/Matlab script generating buttons handlers
		#
		self.form.eraseAuxGridButton.clicked.connect(self.eraseAuxGridButtonClicked)											# Clicked on "Erase aux Grid"
		self.form.abortSimulationButton.clicked.connect(self.abortSimulationButtonClicked)										# Clicked on "Write ABORT Simulation File"
		self.form.drawS11Button.clicked.connect(self.octaveScriptGenerator.drawS11ButtonClicked)								# Clicked on "Write Draw S11 Script"
		self.form.drawS21Button.clicked.connect(self.octaveScriptGenerator.drawS21ButtonClicked)								# Clicked on "Write Draw S21 Script"
		self.form.displaySimulationModelButton.clicked.connect(self.octaveScriptGenerator.displaySimulationModelButtonClicked)	# Clicked on "Display Simulation Model"
		self.form.runSimulationButton.clicked.connect(self.octaveScriptGenerator.runSimulationButtonClicked)					# Clicked on "Run Simulation"
		self.form.writeNf2ffButton.clicked.connect(self.octaveScriptGenerator.writeNf2ffButtonClicked)							# Clicked on "Write NF2FF"

		#
		# GRID
		#	- button "Display gridlines...."
		#	- button "Create userdef..."
		#	- select rectangular or cylindrical grid
		#		
		self.form.createUserdefGridLinesFromCurrentButton.clicked.connect(self.createUserdefGridLinesFromCurrentButtonClicked)
		self.form.displayXYGridLinesInModelButton.clicked.connect(self.displayXYGridLinesInModelButtonClicked)
		self.form.gridRectangularRadio.toggled.connect(self.gridCoordsTypeChoosed)
		self.form.gridCylindricalRadio.toggled.connect(self.gridCoordsTypeChoosed)

		#
		# Material, Grid, Excitation, ... item changed handler functions.
		#		
		self.form.materialSettingsTreeView.currentItemChanged.connect(self.materialTreeWidgetItemChanged)	
		self.form.excitationSettingsTreeView.currentItemChanged.connect(self.excitationTreeWidgetItemChanged)	
		self.form.gridSettingsTreeView.currentItemChanged.connect(self.gridTreeWidgetItemChanged)	
		self.form.portSettingsTreeView.currentItemChanged.connect(self.portTreeWidgetItemChanged)	
		self.form.lumpedPartTreeView.currentItemChanged.connect(self.lumpedPartTreeWidgetItemChanged)	

		#PORT tab settings events handlers
		self.form.lumpedPortRadioButton.toggled.connect(self.portSettingsTypeChoosed)
		self.form.microstripPortRadioButton.toggled.connect(self.portSettingsTypeChoosed)
		self.form.circularWaveguidePortRadioButton.toggled.connect(self.portSettingsTypeChoosed)
		self.form.rectangularWaveguidePortRadioButton.toggled.connect(self.portSettingsTypeChoosed)
		self.form.etDumpPortRadioButton.toggled.connect(self.portSettingsTypeChoosed)
		self.form.htDumpPortRadioButton.toggled.connect(self.portSettingsTypeChoosed)
		self.form.nf2ffBoxPortRadioButton.toggled.connect(self.portSettingsTypeChoosed)

		#SIMULATION Boundary Conditions change event mapping
		self.form.BCxmin.currentIndexChanged.connect(self.BCxminCurrentIndexChanged)
		self.form.BCxmax.currentIndexChanged.connect(self.BCxmaxCurrentIndexChanged)
		self.form.BCymin.currentIndexChanged.connect(self.BCyminCurrentIndexChanged)
		self.form.BCymax.currentIndexChanged.connect(self.BCymaxCurrentIndexChanged)
		self.form.BCzmin.currentIndexChanged.connect(self.BCzminCurrentIndexChanged)
		self.form.BCzmax.currentIndexChanged.connect(self.BCzmaxCurrentIndexChanged)

		####################################################################################################
		# GUI SAVE/LOAD from file
		####################################################################################################
		self.form.saveCurrentSettingsButton.clicked.connect(self.saveCurrentSettingsButtonClicked)
		self.form.loadCurrentSettingsButton.clicked.connect(self.loadCurrentSettingsButtonClicked)

		#
		# FILTER LEFT COLUMN ITEMS
		#
		self.form.objectAssignmentFilterLeftButton.clicked.connect(self.objectAssignmentFilterLeftButtonClicked)
		
		# MinDecrement changed 
		self.form.simParamsMinDecrement.valueChanged.connect(self.simParamsMinDecrementValueChanged)
		
		### Other Initialization
		
		# initialize dB preview label with converted value
		self.simParamsMinDecrementValueChanged(self.form.simParamsMinDecrement.value()) 
	
		# create observer instance
		self.observer = FreeCADDocObserver()
		self.observer.objectCreated += self.freecadObjectCreated
		self.observer.objectChanged += self.freecadObjectChanged
		self.observer.objectDeleted += self.freecadBeforeObjectDeleted
		self.observer.startObservation()	
		
	
	def freecadObjectCreated(self, obj):
		print("freecadObjectCreated :{} ('{}')".format(obj.FullName, obj.Label))
		# A new object has been created. Only the list of available objects needs to be updated.
		filterStr = self.form.objectAssignmentFilterLeft.text()
		self.initLeftColumnTopLevelItems(filterStr)
		
	
	def freecadObjectChanged(self, obj, prop):
		print("freecadObjectChanged :{} ('{}') property changed: {}".format(obj.FullName, obj.Label, prop))
		if prop == 'Label':
			# The label (displayed name) of an object has changed.
			# (TODO) Update all mentions in the ObjectAssigments panel.
			filterStr = self.form.objectAssignmentFilterLeft.text()
			self.initLeftColumnTopLevelItems(filterStr)
		
		
	def freecadBeforeObjectDeleted(self,obj):
		# event is generated before object is being removed, so observing instances have to 
		# (TODO) un-list the object without drawing upon the FreeCAD objects list, and
		# (TODO) propagate changes to prevent corruption. 
		#    Simple approach: delete dependent entries.
		#    Advanced: remember and gray out deleted objects to allow settings to be restored when
		#    the user brings the object back with Redo.
		print("freecadObjectDeleted :{} ('{}')".format(obj.FullName, obj.Label))
		
		
	def simParamsMinDecrementValueChanged(self, newValue):
		if newValue == 0:
			s = '( -inf dB )'
		else:
			s = '( ' + str(np.round(10 * np.log10(newValue), decimals=2)) + ' dB )' 
		self.form.simParamsMinDecrementdBLabel.setText(s)

	def BCxminCurrentIndexChanged(self, index):
		self.form.PMLxmincells.setEnabled(self.form.BCxmin.currentText() == "PML")

	def BCxmaxCurrentIndexChanged(self, index):
		self.form.PMLxmaxcells.setEnabled(self.form.BCxmax.currentText() == "PML")

	def BCyminCurrentIndexChanged(self, index):
		self.form.PMLymincells.setEnabled(self.form.BCymin.currentText() == "PML")

	def BCymaxCurrentIndexChanged(self, index):
		self.form.PMLymaxcells.setEnabled(self.form.BCymax.currentText() == "PML")

	def BCzminCurrentIndexChanged(self, index):
		self.form.PMLzmincells.setEnabled(self.form.BCzmin.currentText() == "PML")

	def BCzmaxCurrentIndexChanged(self, index):
		self.form.PMLzmaxcells.setEnabled(self.form.BCzmax.currentText() == "PML")

	def eraseAuxGridButtonClicked(self):
		print("--> Start removing auxiliary gridlines from 3D view.")
		auxGridLines = App.ActiveDocument.Objects
		for gridLine in auxGridLines:
			print("--> Removing " + gridLine.Label + " from 3D view.")
			if "auxGridLine" in gridLine.Label:
				App.ActiveDocument.removeObject(gridLine.Name)
		print("--> End removing auxiliary gridlines from 3D view.")

	def createUserdefGridLinesFromCurrentButtonClicked(self):
		"""
		print("--> Start creating user defined grid from 3D model.")
		allObjects = App.ActiveDocument.Objects
		gridLineListX = []
		gridLineListY = []
		gridLineListZ = []
		for gridLine in allObjects:
			if "auxGridLine" in gridLine.Label:
				gridLineDirection = abs(gridLine.End - gridLine.Start)
				if (gridLineDirection[0] > 0):
					gridLineListX.append(gridLine)
		

		print("Discovered " + str(len(gridLineList)) + " gridlines in model.")
		print("--> End creating user defined grid from 3D model.")
		"""
		self.guiHelpers.displayMessage("createUserdefGridLinesFromCurrentButtonClicked")

	def displayXYGridLinesInModelButtonClicked(self):        
		print('displayXYGridLinesInModelButtonClicked: start draw whole XY grid for each object')

		gridCategory = self.form.objectAssignmentRightTreeWidget.findItems("Grid", QtCore.Qt.MatchFixedString)[0]
		for gridItemIndex in range(gridCategory.childCount()):
			for objIndex in range(gridCategory.child(gridItemIndex).childCount()):
				currItem = gridCategory.child(gridItemIndex).child(objIndex)
				print(currItem.text(0))
				self.objectDrawGrid(currItem)

	#
	#	Update NF2FF list at POSTPROCESSING TAB
	#
	def updateNF2FFList(self):
		#
		#	If Postprocessing tab is actived then fill combobox with nf2ff possible objects
		#
		self.form.portNf2ffObjectList.clear()
		for k in range(0, self.form.objectAssignmentRightTreeWidget.topLevelItemCount()):
			if (self.form.objectAssignmentRightTreeWidget.topLevelItem(k).text(0) == "Port"):
				for l in range(0, self.form.objectAssignmentRightTreeWidget.topLevelItem(k).childCount()):
					if (self.form.objectAssignmentRightTreeWidget.topLevelItem(k).child(l).data(0, QtCore.Qt.UserRole).type == "nf2ff box"):
						self.form.portNf2ffObjectList.addItem(self.form.objectAssignmentRightTreeWidget.topLevelItem(k).child(l).text(0))

	def updateObjectAssignmentRightTreeWidgetItemData(self, groupName, itemName, data):
		gridGroupWidgetItems = self.form.objectAssignmentRightTreeWidget.findItems(
			itemName, 
			QtCore.Qt.MatchExactly | QtCore.Qt.MatchFlag.MatchRecursive
			)
		for item in gridGroupWidgetItems:
			if (groupName == "Grid"):
				item.setData(0, QtCore.Qt.UserRole, data)


	def objectAssignmentRightTreeWidgetItemSelectionChanged(self):
		currItemLabel = self.form.objectAssignmentRightTreeWidget.currentItem().text(0)
		print(currItemLabel)
		if (currItemLabel):
			FreeCADGui.Selection.clearSelection()
			self.openEMSObj.selectObjectByLabel(currItemLabel)

			
	def objectAssignmentRightTreeWidgetContextClicked(self, event):
		self.objAssignCtxMenu = QtGui.QMenu(self.form.objectAssignmentRightTreeWidget)
		action_expand   = self.objAssignCtxMenu.addAction("Expand all")
		actioN_collapse = self.objAssignCtxMenu.addAction("Collapse all")
		menu_action = self.objAssignCtxMenu.exec_(self.form.objectAssignmentRightTreeWidget.mapToGlobal(event))
		if menu_action is not None:
			if menu_action == action_expand:
				self.form.objectAssignmentRightTreeWidget.expandAll()
			if menu_action == actioN_collapse:
				self.form.objectAssignmentRightTreeWidget.collapseAll()
				
	#
	#	Handler for DOUBLE CLICK on grid item in FreeCAD objects list
	#
	def objectAssignmentLeftTreeWidgetItemDoubleClicked(self):
		self.onMoveRight()

	#
	#	Handler for DOUBLE CLICK on grid item in object assignment list
	#
	def objectAssignmentRightTreeWidgetItemDoubleClicked(self):
		currItem = self.form.objectAssignmentRightTreeWidget.currentItem()
		self.objectDrawGrid(currItem)

	#
	#	Draw auxiliary grid in FreeCAD 3D view
	#
	def objectDrawGrid(self, currItem):
		#
		#	Drawing auxiliary object grid for meshing.
		#
		#		example how to draw line for grid: self.openEMSObj.drawDraftLine("gridXY", [-78.0, -138.0, 0.0], [5.0, -101.0, 0.0])

		currSetting = currItem.data(0, QtCore.Qt.UserRole)
		genScript = ""

		#	must be selected FreeCAD object which is child of grid item which gridlines will be draw
		gridObj =  App.ActiveDocument.getObjectsByLabel(currItem.text(0))
		if ("FreeCADSettingItem" in currSetting.type):
			if ("GridSettingsItem" in currItem.parent().data(0, QtCore.Qt.UserRole).__class__.__name__):
				currSetting = currItem.parent().data(0, QtCore.Qt.UserRole)
			else:
				self.guiHelpers.displayMessage('Cannot draw grid for non-grid item object.')
				return
		else:
			self.guiHelpers.displayMessage('Cannot draw grid for object group.')
			return

		bbCoords = gridObj[0].Shape.BoundBox
	
		print("Start drawing aux grid for: " + currSetting.name)
		print("Enabled coords: " + str(currSetting.xenabled) + " " + str(currSetting.yenabled) + " " + str(currSetting.zenabled))

		#getting model boundaries to draw gridlines properly
		modelMinX, modelMinY, modelMinZ, modelMaxX, modelMaxY, modelMaxZ = self.openEMSObj.getModelBoundaryBox(self.form.objectAssignmentRightTreeWidget)

		#don't know why I put here this axis list code snippet probably to include case if there are some auxiliary axis but now seems useless
		#THERE IS QUESTION IN WHICH PLANE GRID SHOULD BE DRAWN IF in XY, XZ or YZ
		currGridAxis = self.form.auxGridAxis.currentText().lower()
		print("Aux grid axis: " + currGridAxis)

		refUnit = currSetting.getSettingsUnitAsNumber()
		#refUnit = 1
		print("Current object grid units set as number to: refUnit: " + str(refUnit))

		"""
		axisList = collections.deque(['x', 'y', 'z'])
		while axisList[0] != currGridAxis:
			axisList.rotate()
		"""

		if (currSetting.coordsType == 'cylindrical' and currGridAxis == "z"):

			if (currSetting.getType() == 'Fixed Distance'):
				#need to be done for this case
				pass

			elif (currSetting.getType() == 'Fixed Count'):

	            #collecting Z coordinates where grid will be drawn, gird will be drawn in XY plane
				zAuxGridCoordList = []
				if (currSetting.zenabled):
					if int(currSetting.getXYZ(refUnit)['z']) != 0:

						if int(currSetting.getXYZ(refUnit)['z']) == 1:
							zlines = np.array([(bbCoords.ZMin + bbCoords.ZMax)/2])
						else:
							zlines = np.linspace(bbCoords.ZMin, bbCoords.ZMax, int(currSetting.getXYZ(refUnit)['z']))
							
						#collecting Z coordinates where grid layers will be drawn
						for zGridLine in zlines:
							zAuxGridCoordList.append(zGridLine)

				print("zlines")
				print(zAuxGridCoordList)
				if len(zAuxGridCoordList) == 0:
					zAuxGridCoordList.append(bbCoords.ZMax)
	
				for zAuxGridCoord in zAuxGridCoordList:
					
					bbPointsVectors = [App.Vector(bbCoords.YMin, bbCoords.XMin, 0), App.Vector(bbCoords.YMin, bbCoords.XMax, 0), App.Vector(bbCoords.YMax, bbCoords.XMin, 0), App.Vector(bbCoords.YMax, bbCoords.XMax, 0)]
					angle1 = math.atan2(bbCoords.YMin, bbCoords.XMin) + 2*math.pi % (2*math.pi)
					angle2 = math.atan2(bbCoords.YMin, bbCoords.XMax) + 2*math.pi % (2*math.pi)
					angle3 = math.atan2(bbCoords.YMax, bbCoords.XMin) + 2*math.pi % (2*math.pi)
					angle4 = math.atan2(bbCoords.YMax, bbCoords.XMax) + 2*math.pi % (2*math.pi)
					
					minAngle = min([angle1, angle2, angle3, angle4])
					maxAngle = max([angle1, angle2, angle3, angle4])						
					radius = max([math.sqrt(modelMinX**2 + modelMinY**2), math.sqrt(modelMaxX**2 + modelMaxY**2)])

					print("Calculate ylines for cylindrical coords.")
					print("minAngle: " + str(minAngle))
					print("maxAngle: " + str(maxAngle))
					print("radius: " + str(radius))						

					#DRAW X LINES auxiliary grid in 3D view
					if (currSetting.xenabled):						
						a = np.array([angle1, angle2, angle3, angle4])
						indicesMin = a.argmin()
						indicesMax = a.argmax()
						closestLineToCenter = bbPointsVectors[indicesMin] - bbPointsVectors[indicesMax]

						#minRadius = closestLineToCenter.distanceToPoint(App.Vector(0,0,0))
						minRadius = abs((bbPointsVectors[indicesMax].x - bbPointsVectors[indicesMin].x)*bbPointsVectors[indicesMin].y - (bbPointsVectors[indicesMax].y - bbPointsVectors[indicesMin].y)*bbPointsVectors[indicesMin].x)/closestLineToCenter.Length
						maxRadius = max([math.sqrt(bbCoords.XMin**2 + bbCoords.YMin**2), math.sqrt(bbCoords.XMax**2 + bbCoords.YMax**2)])

						if float(currSetting.getXYZ(refUnit)['x']) == 1:
							xlines = np.array([(minRadius + maxRadius)/2])
						else:
							xlines = np.linspace(minRadius, maxRadius, int(currSetting.getXYZ(refUnit)['x']))
							
						for xGridLine in xlines:
							self.openEMSObj.drawDraftCircle("auxGridLine", App.Vector(0,0,zAuxGridCoord), xGridLine)
		
					#DRAW Y LINES auxiliary grid in 3D view
					if (currSetting.yenabled):												
						if float(currSetting.getXYZ(refUnit)['y']) == 1:
							ylines = np.array([(minAngle, maxAngle)/2])
						else:
							ylines = np.linspace(minAngle, maxAngle, int(currSetting.getXYZ(refUnit)['y']))
							
						print(ylines)

						for yGridLine in ylines:
							self.openEMSObj.drawDraftLine("auxGridLine", [0, 0, zAuxGridCoord], [math.cos(yGridLine)*radius, math.sin(yGridLine)*radius, zAuxGridCoord])

		elif (currSetting.coordsType == 'rectangular' and currGridAxis == "z"):

			#######################################################################################################################################################################
		  	# Z grid axis
			#######################################################################################################################################################################

			print("Drawing GRID in Z axis.")

			if (currSetting.getType() == 'Fixed Distance'):
	
				#here adding Z coordinates for which grid will be drawn so grid will be drawn in XY plane, so here are collected just Z coords for which it will be drawn
				zAuxGridCoordList = []
				if (currSetting.zenabled):
					if float(currSetting.getXYZ(refUnit)['z']) != 0:
						zlines = np.arange(bbCoords.ZMin, bbCoords.ZMax, currSetting.getXYZ(refUnit)['z'])    #split Z interval and generate Z layers
						for zGridLine in zlines:
							zAuxGridCoordList.append(zGridLine)
				if len(zAuxGridCoordList) == 0:
					zAuxGridCoordList.append(bbCoords.ZMax)
	
				for zAuxGridCoord in zAuxGridCoordList:
					#DRAW X LINES auxiliary grid in 3D view
					if (currSetting.xenabled):
						if float(currSetting.getXYZ(refUnit)['x']) !=  0:
							xlines = np.arange(bbCoords.XMin, bbCoords.XMax, currSetting.getXYZ(refUnit)['x'])
							for xGridLine in xlines:
								#self.openEMSObj.drawDraftLine("auxGridLine", [xGridLine, bbCoords.YMin, zAuxGridCoord], [xGridLine, bbCoords.YMax, zAuxGridCoord])
								self.openEMSObj.drawDraftLine("auxGridLine", [xGridLine, modelMinY, zAuxGridCoord], [xGridLine, modelMaxY, zAuxGridCoord])
		
					#DRAW Y LINES auxiliary grid in 3D view
					if (currSetting.yenabled):
						if float(currSetting.getXYZ(refUnit)['y']) != 0:
							ylines = np.arange(bbCoords.YMin, bbCoords.YMax, currSetting.getXYZ(refUnit)['y'])
							for yGridLine in ylines:
								#self.openEMSObj.drawDraftLine("auxGridLine", [bbCoords.XMin, yGridLine, zAuxGridCoord], [bbCoords.XMax, yGridLine, zAuxGridCoord])
								self.openEMSObj.drawDraftLine("auxGridLine", [modelMinX, yGridLine, zAuxGridCoord], [modelMaxX, yGridLine, zAuxGridCoord])
	
			elif (currSetting.getType() == 'Fixed Count'):
	
	            #collecting Z coordinates where grid will be drawn, grid will be drawn in XY plane
				zAuxGridCoordList = []
				if (currSetting.zenabled):
					if float(currSetting.getXYZ(refUnit)['z']) != 0:
						if float(currSetting.getXYZ(refUnit)['z']) == 1:
							zlines = np.arange(bbCoords.ZMin, bbCoords.ZMax, int(currSetting.getXYZ(refUnit)['z']))
						else:
							zlines = np.array([(bbCoords.ZMin + bbCoords.ZMax)/2])
							
						#collecting Z coordinates where grid layers will be drawn
						for zGridLine in zlines:
							zAuxGridCoordList.append(zGridLine)
				if len(zAuxGridCoordList) == 0:
					zAuxGridCoordList.append(bbCoords.ZMax)
	
				for zAuxGridCoord in zAuxGridCoordList:
					#DRAW X LINES auxiliary grid in 3D view
					if (currSetting.xenabled):
						if float(currSetting.getXYZ(refUnit)['x']) == 1:
							xlines = np.array([(bbCoords.XMin + bbCoords.XMax)/2])
						else:
							xlines = np.linspace(bbCoords.XMin, bbCoords.XMax, int(currSetting.getXYZ(refUnit)['x']))
							
						for xGridLine in xlines:
							#self.openEMSObj.drawDraftLine("auxGridLine", [xGridLine, bbCoords.YMin, zAuxGridCoord], [xGridLine, bbCoords.YMax, zAuxGridCoord])
							self.openEMSObj.drawDraftLine("auxGridLine", [xGridLine, modelMinY, zAuxGridCoord], [xGridLine, modelMaxY, zAuxGridCoord])
		
					#DRAW Y LINES auxiliary grid in 3D view
					if (currSetting.yenabled):
						if float(currSetting.getXYZ(refUnit)['y']) == 1:
							ylines = np.array([(bbCoords.YMin + bbCoords.YMax)/2])
						else:
							ylines = np.linspace(bbCoords.YMin, bbCoords.YMax, int(currSetting.getXYZ(refUnit)['y']))

						for yGridLine in ylines:
							#self.openEMSObj.drawDraftLine("auxGridLine", [bbCoords.XMin, yGridLine, zAuxGridCoord], [bbCoords.XMax, yGridLine, zAuxGridCoord])
							self.openEMSObj.drawDraftLine("auxGridLine", [modelMinX, yGridLine, zAuxGridCoord], [modelMaxX, yGridLine, zAuxGridCoord])
	
			elif (currSetting.getType() == 'User Defined'):
				#UNIT FOR MESH										
				genScript += "meshUnit = " + currSetting.getUnitAsScriptLine() + "; % all length in mm\n"
				genScript += "mesh = " + currSetting.getXYZ(refUnit) + ";\n"

		elif (currSetting.coordsType == 'rectangular' and currGridAxis == "x"):

			#######################################################################################################################################################################
		  	# X grid axis - STILL EXPERIMENTAL require REPAIR
			#######################################################################################################################################################################

			print("Drawing GRID in X axis.")
			
			if (currSetting.getType() == 'Fixed Distance'):
	
				#here adding Z coordinates for which grid will be drawn so grid will be drawn in XY plane, so here are collected just Z coords for which it will be drawn
				xAuxGridCoordList = []
				if (currSetting.xenabled):
					if float(currSetting.getXYZ(refUnit)['x']) != 0:
						xlines = np.arange(bbCoords.XMin, bbCoords.XMax, currSetting.getXYZ(refUnit)['x'])    #split Z interval and generate Z layers
						for xGridLine in xlines:
							xAuxGridCoordList.append(xGridLine)
				if len(xAuxGridCoordList) == 0:
					xAuxGridCoordList.append(bbCoords.XMax)
	
				for xAuxGridCoord in xAuxGridCoordList:
					#DRAW Z LINES auxiliary grid in 3D view
					if (currSetting.zenabled):
						if float(currSetting.getXYZ(refUnit)['z']) !=  0:
							zlines = np.arange(bbCoords.ZMin, bbCoords.ZMax, currSetting.getXYZ(refUnit)['z'])
							for zGridLine in zlines:
								self.openEMSObj.drawDraftLine("auxGridLine", [xAuxGridCoord, modelMinY, zGridLine], [xAuxGridCoord, modelMaxY, zGridLine])
		
					#DRAW Y LINES auxiliary grid in 3D view
					if (currSetting.yenabled):
						if float(currSetting.getXYZ(refUnit)['y']) != 0:
							ylines = np.arange(bbCoords.YMin, bbCoords.YMax, currSetting.getXYZ(refUnit)['y'])
							for yGridLine in ylines:
								self.openEMSObj.drawDraftLine("auxGridLine", [xAuxGridCoord, yGridLine, modelMinZ], [xAuxGridCoord, yGridLine, modelMaxZ])
	
			elif (currSetting.getType() == 'Fixed Count'):
	
	            #collecting Z coordinates where grid will be drawn, grid will be drawn in XY plane
				xAuxGridCoordList = []
				if (currSetting.xenabled):
					if float(currSetting.getXYZ(refUnit)['x']) != 0:
						if float(currSetting.getXYZ(refUnit)['x']) == 1:
							xlines = np.array([(bbCoords.XMin + bbCoords.XMax)/2])
						else:
							xlines = np.arange(bbCoords.XMin, bbCoords.XMax, int(currSetting.getXYZ(refUnit)['x']))   #collecting Z coordinates where grid layers will be drawn
							
						for xGridLine in xlines:
							xAuxGridCoordList.append(xGridLine)

				if len(xAuxGridCoordList) == 0:
					xAuxGridCoordList.append(bbCoords.XMax)
	
				for xAuxGridCoord in xAuxGridCoordList:
					#DRAW X LINES auxiliary grid in 3D view
					if (currSetting.zenabled):
						if float(currSetting.getXYZ(refUnit)['z']) == 1:
							zlines = np.array([(bbCoords.ZMin + bbCoords.ZMax)/2])
						else:
							zlines = np.linspace(bbCoords.ZMin, bbCoords.ZMax, int(currSetting.getXYZ(refUnit)['z']))
						
						for zGridLine in zlines:
							self.openEMSObj.drawDraftLine("auxGridLine", [xAuxGridCoord, modelMinY, zGridLine], [xAuxGridCoord, modelMaxY, zGridLine])
		
					#DRAW Y LINES auxiliary grid in 3D view
					if (currSetting.yenabled):
						if float(currSetting.getXYZ(refUnit)['y']) == 1:
							ylines = np.array([(bbCoords.YMin + bbCoords.YMax)/2])
						else:
							ylines = np.linspace(bbCoords.YMin, bbCoords.YMax, int(currSetting.getXYZ(refUnit)['y']))
						
						for yGridLine in ylines:
								self.openEMSObj.drawDraftLine("auxGridLine", [xAuxGridCoord, yGridLine, modelMinZ], [xAuxGridCoord, yGridLine, modelMaxZ])
	
			elif (currSetting.getType() == 'User Defined'):
				#UNIT FOR MESH										
				genScript += "meshUnit = " + currSetting.getUnitAsScriptLine() + "; % all length in mm\n"
				genScript += "mesh = " + currSetting.getXYZ(refUnit) + ";\n"
				
		elif (currSetting.coordsType == 'rectangular' and currGridAxis == "y"):

			#######################################################################################################################################################################
		  	# Y grid axis - NOT IMPLEMENTED
			#######################################################################################################################################################################

			print("Drawing GRID in Y axis.")

			if (currSetting.getType() == 'Fixed Distance'):
	
				#here adding Z coordinates for which grid will be drawn so grid will be drawn in XY plane, so here are collected just Z coords for which it will be drawn
				yAuxGridCoordList = []
				if (currSetting.yenabled):
					if float(currSetting.getXYZ(refUnit)['y']) != 0:
						ylines = np.arange(bbCoords.YMin, bbCoords.YMax, currSetting.getXYZ(refUnit)['y'])    #split Y interval and generate Z layers
						for yGridLine in ylines:
							yAuxGridCoordList.append(yGridLine)
				if len(yAuxGridCoordList) == 0:
					yAuxGridCoordList.append(bbCoords.YMax)
	
				for yAuxGridCoord in yAuxGridCoordList:
					#DRAW Z LINES auxiliary grid in 3D view
					if (currSetting.zenabled):
						if float(currSetting.getXYZ(refUnit)['z']) !=  0:
							zlines = np.arange(bbCoords.ZMin, bbCoords.ZMax, currSetting.getXYZ(refUnit)['z'])
							for zGridLine in zlines:
								self.openEMSObj.drawDraftLine("auxGridLine", [modelMinX, yAuxGridCoord, zGridLine], [modelMaxX, yAuxGridCoord, zGridLine])
		
					#DRAW X LINES auxiliary grid in 3D view
					if (currSetting.xenabled):
						if float(currSetting.getXYZ(refUnit)['x']) != 0:
							xlines = np.arange(bbCoords.XMin, bbCoords.XMax, currSetting.getXYZ(refUnit)['x'])
							for xGridLine in xlines:
								self.openEMSObj.drawDraftLine("auxGridLine", [xGridLine, yAuxGridCoord, modelMinZ], [xGridLine, yAuxGridCoord, modelMaxZ])
	
			elif (currSetting.getType() == 'Fixed Count'):
	
	            #collecting Z coordinates where grid will be drawn, grid will be drawn in XY plane
				yAuxGridCoordList = []
				if (currSetting.yenabled):
					if float(currSetting.getXYZ(refUnit)['y']) != 0:
						if float(currSetting.getXYZ(refUnit)['y']) == 1:
							ylines = np.array([(bbCoords.YMin + bbCoords.YMax)/2])
						else:
							ylines = np.arange(bbCoords.YMin, bbCoords.YMax, int(currSetting.getXYZ(refUnit)['y']))   #collecting Y coordinates where grid layers will be drawn

						for yGridLine in ylines:
							yAuxGridCoordList.append(yGridLine)

				if len(yAuxGridCoordList) == 0:
					yAuxGridCoordList.append(bbCoords.YMax)
	
				for yAuxGridCoord in yAuxGridCoordList:
					#DRAW Z LINES auxiliary grid in 3D view
					if (currSetting.zenabled):
						if float(currSetting.getXYZ(refUnit)['z']) == 1:
							zlines = np.array([(bbCoords.ZMin + bbCoords.ZMax)/2])
						else:
							zlines = np.linspace(bbCoords.ZMin, bbCoords.ZMax, int(currSetting.getXYZ(refUnit)['z']))

						for zGridLine in zlines:
							self.openEMSObj.drawDraftLine("auxGridLine", [modelMinX, yAuxGridCoord, zGridLine], [modelMaxX, yAuxGridCoord, zGridLine])
		
					#DRAW X LINES auxiliary grid in 3D view
					if (currSetting.xenabled):
						if float(currSetting.getXYZ(refUnit)['x']) == 1:
							xlines = np.array([(bbCoords.XMin + bbCoords.XMax)/2])
						else:
							xlines = np.linspace(bbCoords.XMin, bbCoords.XMax, int(currSetting.getXYZ(refUnit)['x']))

						for xGridLine in xlines:
							self.openEMSObj.drawDraftLine("auxGridLine", [xGridLine, yAuxGridCoord, modelMinZ], [xGridLine, yAuxGridCoord, modelMaxZ])
	
			elif (currSetting.getType() == 'User Defined'):
				#UNIT FOR MESH										
				genScript += "meshUnit = " + currSetting.getUnitAsScriptLine() + "; % all length in mm\n"
				genScript += "mesh = " + currSetting.getXYZ(refUnit) + ";\n"

		#update whole document
		App.ActiveDocument.recompute()
		print("---> Aux grid drawing finished. \n" + genScript)

	#######################################################################################################################################################################
  	# END GRID DRAWING
	#######################################################################################################################################################################
	
	def initLeftColumnTopLevelItems(self, filterStr = ""):
		self.form.objectAssignmentLeftTreeWidget.clear()

		items = self.openEMSObj.getOpenEMSObjects(filterStr)
		treeItems = []
		for i in items:
			print("openEMS object to export:" + i.Label)

			# ADDING ITEMS with UserData object which storethem in intelligent way
			#
			topItem = QtGui.QTreeWidgetItem([i.Label])
			itemData = FreeCADSettingsItem(name = i.Label, freeCadId = i.Name)
			topItem.setData(0, QtCore.Qt.UserRole, itemData)
			if (i.Name.find("Sketch") > -1):
				topItem.setIcon(0, QtGui.QIcon("./img/wire.svg")) 
			elif (i.Name.find("Discretized_Edge") > -1): 
				topItem.setIcon(0, QtGui.QIcon("./img/curve.svg"))
			else:
				topItem.setIcon(0, QtGui.QIcon("./img/object.svg")) 
			treeItems.append(topItem)

		
		self.form.objectAssignmentLeftTreeWidget.insertTopLevelItems(0, treeItems)

	#
	#	ABORT simulation button handler
	#		write empty file ABORT into tmp/ folder what should abort simulation in next iteration
	#
	def abortSimulationButtonClicked(self):
		programdir = os.path.dirname(App.ActiveDocument.FileName)
		outFile = programdir + '/tmp/ABORT'
		print("------------->" + outFile)

		f = open(outFile, "w+", encoding='utf-8')
		f.write("THIS CAN BE JUST EMPTY FILE. ABORT simulation.")
		f.close()

	def materialUserDeinedRadioButtonToggled(self):
		if (self.form.materialUserDefinedRadioButton.isChecked()):
			self.form.materialEpsilonNumberInput.setEnabled(True)
			self.form.materialMueNumberInput.setEnabled(True)
			self.form.materialKappaNumberInput.setEnabled(True)
			self.form.materialSigmaNumberInput.setEnabled(True)
		else:
			self.form.materialEpsilonNumberInput.setEnabled(False)
			self.form.materialMueNumberInput.setEnabled(False)
			self.form.materialKappaNumberInput.setEnabled(False)
			self.form.materialSigmaNumberInput.setEnabled(False)

	def objectAssignmentFilterLeftButtonClicked(self):
		print("Filter left column")
		filterStr = self.form.objectAssignmentFilterLeft.text()
		self.initLeftColumnTopLevelItems(filterStr)

	def initRightColumnTopLevelItems(self):
		#
		# Default items for each section
		#
		""" NO DEFAULT ITEMS!
		topItem = self.form.objectAssignmentRightTreeWidget.itemAt(0,0)
		defaultMaterialItem = QtGui.QTreeWidgetItem(["Material Default"])
		defaultExcitationItem = QtGui.QTreeWidgetItem(["Excitation Default"])
		defaultGridItem = QtGui.QTreeWidgetItem(["Grid Default"])
		defaultPortItem = QtGui.QTreeWidgetItem(["Port Default"])
		defaultLumpedPartItem = QtGui.QTreeWidgetItem(["LumpedPart Default"])
		"""

		#
		# Default items in each subsection have user data FreeCADSttingsItem classes to have just basic information like genereal freecad object
		#
		""" NO DEFAULT ITEMS!
		defaultMaterialItem.setData(0, QtCore.Qt.UserRole, FreeCADSettingsItem("Material Default"))
		defaultExcitationItem.setData(0, QtCore.Qt.UserRole, FreeCADSettingsItem("Excitation Default"))
		defaultGridItem.setData(0, QtCore.Qt.UserRole, FreeCADSettingsItem("Grid Default"))
		defaultPortItem.setData(0, QtCore.Qt.UserRole, FreeCADSettingsItem("Port Default"))
		defaultLumpedPartItem.setData(0, QtCore.Qt.UserRole, FreeCADSettingsItem("LumpedPart Default"))
		"""

		# MATERIALS
		topItem = QtGui.QTreeWidgetItem(["Material"])
		topItem.setIcon(0, QtGui.QIcon("./img/material.svg"))
		#topItem.addChildren([defaultMaterialItem])	#NO DEFAULT ITEM
		self.form.objectAssignmentRightTreeWidget.insertTopLevelItem(0, topItem)

		#LuboJ
		self.MaterialsItem = topItem	#aux item materials item to have some reference here to be sure for future access it

		# EXCITATION
		topItem = QtGui.QTreeWidgetItem(["Excitation"])
		topItem.setIcon(0, QtGui.QIcon("./img/excitation.svg"))
		#topItem.addChildren([defaultExcitationItem])	#NO DEFAULT ITEM
		self.form.objectAssignmentRightTreeWidget.insertTopLevelItem(0, topItem)

		# GRID
		topItem = QtGui.QTreeWidgetItem(["Grid"])
		topItem.setIcon(0, QtGui.QIcon("./img/grid.svg"))
		#topItem.addChildren([defaultGridItem])	#NO DEFAULT ITEM
		self.form.objectAssignmentRightTreeWidget.insertTopLevelItem(0, topItem)

		# PORTS
		topItem = QtGui.QTreeWidgetItem(["Port"])
		topItem.setIcon(0, QtGui.QIcon("./img/port.svg"))
		#topItem.addChildren([defaultPortItem])	#NO DEFAULT ITEM
		self.form.objectAssignmentRightTreeWidget.insertTopLevelItem(0, topItem)

		# LUMPED PART
		topItem = QtGui.QTreeWidgetItem(["LumpedPart"])
		topItem.setIcon(0, QtGui.QIcon("./img/lumpedpart.svg"))
		#topItem.addChildren([defaultLumpedPartItem])	#NO DEFAULT ITEM
		self.form.objectAssignmentRightTreeWidget.insertTopLevelItem(0, topItem)

		return

	""" DUPLICATION
	def saveCurrentSettingsButtonClicked(self):
		print("objectAssignmentShowSettingsButtonClicked entered")

		#get reference to each category item
		allItems = []
		childCount = self.form.objectAssignmentRightTreeWidget.invisibleRootItem().childCount()
		for k in range(childCount):
			allItems.append(self.form.objectAssignmentRightTreeWidget.topLevelItem(k))

		#go through categories children
		#output their data inside
		for m in range(len(allItems)):
			currItem = allItems[m]
			for k in range(currItem.childCount()):
				item = currItem.child(k)
				itemData = item.data(0, QtCore.Qt.UserRole)
				print("User datatype: " + item.text(0) + " - " + str(type(itemData)))
				if (itemData):
					print(itemData.serializeToString())

		return
	"""

	#
	#	Get COORDINATION TYPE
	#		this function traverse priority tree view and return coordination type of the most high item
	#
	#	returns string coords type
	#
	def getModelCoordsType(self):
		for k in range(self.form.objectAssignmentPriorityTreeView.topLevelItemCount()):
			priorityObjNameSplitted = self.form.objectAssignmentPriorityTreeView.topLevelItem(k).text(0).split(',')
			if (priorityObjNameSplitted[0].strip() == "Grid"):
				gridCategoryItem = self.form.objectAssignmentRightTreeWidget.findItems("Grid", QtCore.Qt.MatchFixedString)
				gridObj = [gridCategoryItem[0].child(x) for x in range(gridCategoryItem[0].childCount()) if gridCategoryItem[0].child(x).text(0) == priorityObjNameSplitted[1].strip()]
				return gridObj[0].data(0, QtCore.Qt.UserRole).coordsType
		return ""

	def getSimParamsUnitsStr(self):
		units = self.form.simParamsUnitsNumberInput.currentText()
		if (units == 'Hz'):
			units2 = ''
			pass
		elif(units == "kHz"):
			units2 = 'e3'
			pass
		elif(units == "MHz"):
			units2 = 'e6'
			pass
		elif(units == "GHz"):
			units2 = 'e9'
			pass
		return units2

	def getSimParamsFcStr(self):
		units = self.getSimParamsUnitsStr()
		return str(self.form.simParamFcNumberInput.value()) + units

	def getSimParamsF0Str(self):
		units = self.getSimParamsUnitsStr()
		return str(self.form.simParamF0NumberInput.value()) + units

	#
	# Universal function to add items into categories in GUI.
	#
	def addSettingsItemGui(self, settingsItem):
		treeItemName = settingsItem.name
		treeItem = QtGui.QTreeWidgetItem([treeItemName])

		itemTypeReg = re.search("(.*)SettingsItem", str(settingsItem.__class__.__name__))
		typeStr = itemTypeReg.group(1)

		treeItem.setIcon(0, QtGui.QIcon("./img/" + typeStr.lower() + ".svg"))
		treeItem.setData(0, QtCore.Qt.UserRole, settingsItem)

		#add item into excitation list
		treeWidgetRef = {}
		itemChangedRef = {}
		if (typeStr.lower() == "excitation"):
			treeWidgetRef = self.form.excitationSettingsTreeView
		elif (typeStr.lower() == "port"):
			treeWidgetRef = self.form.portSettingsTreeView
		elif (typeStr.lower() == "grid"):
			treeWidgetRef = self.form.gridSettingsTreeView
		elif (typeStr.lower() == "material"):
			treeWidgetRef = self.form.materialSettingsTreeView
		elif (typeStr.lower() == "lumpedpart"):
			treeWidgetRef = self.form.lumpedPartTreeView
		else:
			print('cannot assign item ' + typeStr)
			return

		treeWidgetRef.insertTopLevelItem(0, treeItem)
		treeWidgetRef.setCurrentItem(treeWidgetRef.topLevelItem(0))

		#adding excitation also into OBJCET ASSIGNMENT WINDOW
		targetGroup = self.form.objectAssignmentRightTreeWidget.findItems(typeStr, QtCore.Qt.MatchExactly)
		targetGroup[0].addChild(treeItem.clone())

	###
	#	Removing from Priority List
	###
	def removePriorityName(self, priorityName):
		print("Removing from oibjects priority list tree view:" + priorityName)
		priorityItemRemoved = True
		while priorityItemRemoved:
			priorityItemRemoved = False

			#search item in priority list for OBJECTS
			priorityItemsCount = self.form.objectAssignmentPriorityTreeView.topLevelItemCount()
			for k in range(priorityItemsCount):
				priorityItem = self.form.objectAssignmentPriorityTreeView.topLevelItem(k)
				if priorityName in priorityItem.text(0):
					self.form.objectAssignmentPriorityTreeView.takeTopLevelItem(k)
					priorityItemRemoved = True
					break

			#search item also in priority list for MESH
			if not priorityItemRemoved:
				priorityItemsCount = self.form.meshPriorityTreeView.topLevelItemCount()
				for k in range(priorityItemsCount):
					priorityItem = self.form.meshPriorityTreeView.topLevelItem(k)
					if priorityName in priorityItem.text(0):
						self.form.meshPriorityTreeView.takeTopLevelItem(k)
						priorityItemRemoved = True
						break

	def show(self):
		self.form.show()

	#
	#	Button << to assign object from FreeCAD to OpenEMS solver structure
	#
	def onMoveLeft(self):
		print("Button << clicked.")
		rightItem = self.form.objectAssignmentRightTreeWidget.selectedItems()[0]

		#
		#	REMOVE FROM PRIORITY OBJECT ASSIGNMENT tree view
		#
		prioritySettingsItemName = rightItem.parent().parent().text(0) + ", " + rightItem.parent().text(0) + ", " + rightItem.text(0)

		#going through items in priority object list and searching for name, when matched it's removed from list
		itemsCount = self.form.objectAssignmentPriorityTreeView.topLevelItemCount()
		for k in range(itemsCount):
			priorityItem = self.form.objectAssignmentPriorityTreeView.topLevelItem(k)
			if prioritySettingsItemName in priorityItem.text(0):
				self.form.objectAssignmentPriorityTreeView.takeTopLevelItem(k)
				print("Removing item " + prioritySettingsItemName + " from priority object list.")
				break	#this will break loop SO JUST ONE ITEM FROM PRIORITY LIST IS DELETED

		#
		#	REMOVE FROM PRIORITY MESH ASSIGNMENT tree view
		#

		#going through items in priority mesh list and searching for name, when matched it's removed from list
		itemsCount = self.form.meshPriorityTreeView.topLevelItemCount()
		for k in range(itemsCount):
			priorityItem = self.form.meshPriorityTreeView.topLevelItem(k)
			if prioritySettingsItemName in priorityItem.text(0):
				self.form.meshPriorityTreeView.takeTopLevelItem(k)
				print("Removing item " + prioritySettingsItemName + " from priority mesh list.")
				break	#this will break loop SO JUST ONE ITEM FROM PRIORITY LIST IS DELETED

		#
		#	REMOVE ITEM FROM OpenEMS Simulation assignments tree view
		#
		rightItem.parent().removeChild(rightItem)

		return

	#
	#	Button >> to remove object assignment
	#
	def onMoveRight(self):
		print("Button >> clicked.")

		# here are created 2 clones of item in left column to be putted into right column into some category
		# as material, port or something and there is also priority list where another clone is inserted
		leftItem = self.form.objectAssignmentLeftTreeWidget.selectedItems()[0].clone()
		leftItem2 = self.form.objectAssignmentLeftTreeWidget.selectedItems()[0].clone()

		rightItem = self.form.objectAssignmentRightTreeWidget.selectedItems()[0]

		#check if item is type of SettingsItem based on its class name and if yes then add subitems into it
		reResult = re.search(__name__+".(.*)SettingsItem", str(type(rightItem.data(0, QtCore.Qt.UserRole))))
		if (reResult):
			if (reResult.group(1).lower() == 'excitation'):
				self.guiHelpers.displayMessage("Excitation doesn't accept any objects.")
				return
			if (reResult.group(1).lower() == 'freecad'):
				self.guiHelpers.displayMessage("FreeCAD object cannot have child item.")
				return
			else:
				print("Item " + leftItem.text(0) + " added into " + rightItem.text(0))
	
			#
			# ADD ITEM INTO RIGHT LIST, first clone is inserted
			#
			rightItem.addChild(leftItem)
			rightItem.setExpanded(True)

			#
			# ADD ITEM INTO PRIORITY LIST, must be 2nd copy that's reason why there is used leftItem2 to have different clone of left item
			#
			addItemToPriorityList = True

			newAddedItemName = rightItem.parent().text(0) + ", " + rightItem.text(0) + ", " + leftItem2.text(0)
			leftItem2.setData(0, QtCore.Qt.UserRole, rightItem.data(0, QtCore.Qt.UserRole))
	
			#
			#	Check if item is already in priority list, must be in same category as material, port or so to be not added due it will be duplicate
			#	There are 2 priority lists:
			#		1. objects priority for 3D objects - materials, ports
			#		2. mesh priority objects
			#
			isGridObjectToBeAdded = reResult.group(1).lower() == 'grid'

			if (isGridObjectToBeAdded):
				priorityListItems = self.form.meshPriorityTreeView.findItems(newAddedItemName, QtCore.Qt.MatchFixedString)
				addItemToPriorityList = len(priorityListItems) == 0	#check for DUPLICATES
			else:
				priorityListItems = self.form.objectAssignmentPriorityTreeView.findItems(newAddedItemName, QtCore.Qt.MatchFixedString)
				addItemToPriorityList = len(priorityListItems) == 0	#check for DUPLICATES
			
			if addItemToPriorityList:
				#	Item is gonna be added into list:
				#		1. copy icon of object category in right list to know what is added (PORT, MATERIAL, Excitation, ...)
				#		2. add item into priority list with according icon and category				
				leftItem2.setText(0, newAddedItemName)

				if (isGridObjectToBeAdded):
					self.form.meshPriorityTreeView.insertTopLevelItem(0, leftItem2)						
				else:
					self.form.objectAssignmentPriorityTreeView.insertTopLevelItem(0, leftItem2)

				#
				# If grid settings is not set to be top priority lines, therefore it's disabled (because then it's not take into account when generate mesh lines and it's overlapping something)
				#
				self.updateMeshPriorityDisableItems()
				
				leftItem2.setIcon(0, rightItem.parent().icon(0)) #set same icon as parent have means same as category
				print("Object " + leftItem2.text(0)+ " added into priority list")
			else:
				#
				#	NO ITEM WOULD BE ADDED BECAUSE ALREADY IS IN LIST
				#
				print("Object " + leftItem2.text(0)+ " in category " + rightItem.parent().text(0) + " already in priority list")


		else:
				self.guiHelpers.displayMessage("Item must be added into some settings inside category.")


	def updateMeshPriorityDisableItems(self):
		itemsCount = self.form.meshPriorityTreeView.topLevelItemCount()
		for k in range(itemsCount):
			priorityItem = self.form.meshPriorityTreeView.topLevelItem(k)
			itemNameFields = priorityItem.text(0).split(',')
			print("Searching......" + itemNameFields[1])
			gridParent = self.form.objectAssignmentRightTreeWidget.findItems(itemNameFields[1].strip(), QtCore.Qt.MatchRecursive)
			if len(gridParent) > 0:
				print("parent grid found")
				print(gridParent[0].data(0, QtCore.Qt.UserRole).topPriorityLines)
				print(type(gridParent[0].data(0, QtCore.Qt.UserRole).topPriorityLines))
			#	if not gridParent[0].data(0, QtCore.Qt.UserRole).topPriorityLines or gridParent[0].data(0, QtCore.Qt.UserRole).topPriorityLines == 'false':
			#		self.form.meshPriorityTreeView.topLevelItem(k).setDisabled(True)
			#	else:
			#		self.form.meshPriorityTreeView.topLevelItem(k).setDisabled(False)

		"""
		# If grid item is set to have priority lines it means it should be highlighted in mesh priority widget
		# to display it is special generated in script for simulation
		if rightItem.data(0, QtCore.Qt.UserRole).topPriorityLines:
			#self.form.meshPriorityTreeView.topLevelItem(0).setFont(0, QtGui.QFont("Courier", weight = QtGui.QFont.Bold))
			self.form.meshPriorityTreeView.topLevelItem(0).setDisabled(True)
		else:
			#self.form.meshPriorityTreeView.topLevelItem(0).setFont(0, QtGui.QFont("Courier", weight = QtGui.QFont.Bold))
			self.form.meshPriorityTreeView.topLevelItem(0).setDisabled(False)
		"""

	def removeAllMeshPriorityItems(self):
		print("START REMOVING MESH PRIORITY WIDGET ITEMS")
		print("ITEM TO REMOVE: " + str(self.form.meshPriorityTreeView.invisibleRootItem().childCount()))

		priorityItemsCount = self.form.meshPriorityTreeView.topLevelItemCount()
		for k in reversed(range(priorityItemsCount)):
			print("REMOVING ITEM " + self.form.meshPriorityTreeView.takeTopLevelItem(k).text(0))
			self.form.meshPriorityTreeView.takeTopLevelItem(k)

	#
	#	PRIORITY OBJECT LIST move item UP
	#
	def moveupPriorityButtonClicked(self):
		currItemIndex = self.form.objectAssignmentPriorityTreeView.indexOfTopLevelItem(self.form.objectAssignmentPriorityTreeView.currentItem())
		if currItemIndex > 0:
			takenItem = self.form.objectAssignmentPriorityTreeView.takeTopLevelItem(currItemIndex)
			self.form.objectAssignmentPriorityTreeView.insertTopLevelItem(currItemIndex-1, takenItem)
			self.form.objectAssignmentPriorityTreeView.setCurrentItem(takenItem)

	#
	#	PRIORITY OBJECT LIST move item DOWN
	#
	def movedownPriorityButtonClicked(self):
		currItemIndex = self.form.objectAssignmentPriorityTreeView.indexOfTopLevelItem(self.form.objectAssignmentPriorityTreeView.currentItem())
		countAllItems = self.form.objectAssignmentPriorityTreeView.topLevelItemCount()
		if currItemIndex < countAllItems-1:
			takenItem = self.form.objectAssignmentPriorityTreeView.takeTopLevelItem(currItemIndex)
			self.form.objectAssignmentPriorityTreeView.insertTopLevelItem(currItemIndex+1, takenItem)
			self.form.objectAssignmentPriorityTreeView.setCurrentItem(takenItem)

	#
	#	PRIORITY MESH LIST move item UP
	#
	def moveupPriorityMeshButtonClicked(self):
		currItemIndex = self.form.meshPriorityTreeView.indexOfTopLevelItem(self.form.meshPriorityTreeView.currentItem())
		if currItemIndex > 0:
			takenItem = self.form.meshPriorityTreeView.takeTopLevelItem(currItemIndex)
			self.form.meshPriorityTreeView.insertTopLevelItem(currItemIndex-1, takenItem)
			self.form.meshPriorityTreeView.setCurrentItem(takenItem)

	#
	#	PRIORITY MESH LIST move item DOWN
	#
	def movedownPriorityMeshButtonClicked(self):
		currItemIndex = self.form.meshPriorityTreeView.indexOfTopLevelItem(self.form.meshPriorityTreeView.currentItem())
		countAllItems = self.form.meshPriorityTreeView.topLevelItemCount()
		if currItemIndex < countAllItems-1:
			takenItem = self.form.meshPriorityTreeView.takeTopLevelItem(currItemIndex)
			self.form.meshPriorityTreeView.insertTopLevelItem(currItemIndex+1, takenItem)
			self.form.meshPriorityTreeView.setCurrentItem(takenItem)

	def checkTreeWidgetForDuplicityName(self,refTreeWidget, itemName):
		isDuplicityName = False
		iterator = QtGui.QTreeWidgetItemIterator(refTreeWidget, QtGui.QTreeWidgetItemIterator.All)
		while iterator.value():
			item = iterator.value()
			if item.text(0) == itemName:
				isDuplicityName = True
				self.guiHelpers.displayMessage("Please change name, item with this name already exists.", True)
			iterator +=1
		return isDuplicityName

	#this should erase all items from tree widgets and everything before loading new configuration to everything pass right
	#	tree widget is just important to erase because all items contains userdata items which contains its configuration and whole
	#	gui is generating code based on these information, so when items are erased and new ones created everything is ok
	def deleteAllSettings(self):
		self.form.objectAssignmentRightTreeWidget.clear()	#init right column as at startup to have default structure cleared
		self.initRightColumnTopLevelItems()			#rerecreate default simulation structure

		self.form.objectAssignmentPriorityTreeView.clear()	#delete OBJECT ASSIGNMENTS entries
		self.form.gridSettingsTreeView.clear()			#delete GRID entries
		self.form.materialSettingsTreeView.clear()		#delete MATERIAL entries
		self.form.excitationSettingsTreeView.clear()		#delete EXCITATION entries
		self.form.portSettingsTreeView.clear()			#delete PORT entries
		self.form.lumpedPartTreeView.clear()			#delete LUMPED PART entries
		
		return

	# GRID SETTINGS
	#   _____ _____  _____ _____     _____ ______ _______ _______ _____ _   _  _____  _____ 
	#  / ____|  __ \|_   _|  __ \   / ____|  ____|__   __|__   __|_   _| \ | |/ ____|/ ____|
	# | |  __| |__) | | | | |  | | | (___ | |__     | |     | |    | | |  \| | |  __| (___  
	# | | |_ |  _  /  | | | |  | |  \___ \|  __|    | |     | |    | | | . ` | | |_ |\___ \ 
	# | |__| | | \ \ _| |_| |__| |  ____) | |____   | |     | |   _| |_| |\  | |__| |____) |
	#  \_____|_|  \_\_____|_____/  |_____/|______|  |_|     |_|  |_____|_| \_|\_____|_____/ 
	#
	def fixedCountRadioButtonClicked(self):
		self.form.userDefinedGridLinesTextInput.setEnabled(False)
		self.form.gridTopPriorityLinesCheckbox.setEnabled(True)

	def fixedDistanceRadioButtonClicked(self):
		self.form.userDefinedGridLinesTextInput.setEnabled(False)
		self.form.gridTopPriorityLinesCheckbox.setEnabled(True)

	def userDefinedRadioButtonClicked(self):
		self.form.userDefinedGridLinesTextInput.setEnabled(True)

		self.form.gridTopPriorityLinesCheckbox.setCheckState(QtCore.Qt.Unchecked)
		self.form.gridTopPriorityLinesCheckbox.setEnabled(False)
		
	def getCurrentSimulationGridType(self):
		isCoordTypeRectangular = True

		#none grid items defined
		if self.form.gridSettingsTreeView.invisibleRootItem().childCount() == 0:
			return None

		#there are grid items defined, so going through them and find their coordination type, they should be all the same coord type
		currentSimulationGridType = 'rectangular'
		topGridItem = self.form.gridSettingsTreeView.invisibleRootItem()
		definedGridItemsCount = topGridItem.childCount()
		for k in range(0, definedGridItemsCount):
			if topGridItem.child(k).data(0, QtCore.Qt.UserRole).coordsType != currentSimulationGridType:
				currentSimulationGridType = 'cylindrical'

		return currentSimulationGridType

	def getGridItemFromGui(self):
		name = self.form.gridSettingsNameInput.text()

		gridX = 0
		gridY = 0
		gridZ = 0

		gridItem = GridSettingsItem()
		gridItem.name = name

		xenabled = self.form.gridXEnable.isChecked()
		yenabled = self.form.gridYEnable.isChecked()
		zenabled = self.form.gridZEnable.isChecked()
		gridItem.xenabled = xenabled
		gridItem.yenabled = yenabled
		gridItem.zenabled = zenabled

		if (self.form.gridRectangularRadio.isChecked()):
			gridItem.coordsType = "rectangular"
		if (self.form.gridCylindricalRadio.isChecked()):
			gridItem.coordsType = "cylindrical"

		if (self.form.fixedCountRadioButton.isChecked()):
			gridItem.type = "Fixed Count"
			gridX = self.form.fixedCountXNumberInput.value()
			gridY = self.form.fixedCountYNumberInput.value()
			gridZ = self.form.fixedCountZNumberInput.value()

			gridItem.fixedCount = {}
			gridItem.fixedCount['x'] = gridX
			gridItem.fixedCount['y'] = gridY
			gridItem.fixedCount['z'] = gridZ

			print("---> Saved GridSetting ")
			print(str(gridX) + " " + str(gridY) + " " + str(gridZ))

		if (self.form.fixedDistanceRadioButton.isChecked()):
			gridItem.type = "Fixed Distance"
			gridX = self.form.fixedDistanceXNumberInput.value()
			gridY = self.form.fixedDistanceYNumberInput.value()
			gridZ = self.form.fixedDistanceZNumberInput.value()

			gridItem.fixedDistance = {}
			gridItem.fixedDistance['x'] = gridX
			gridItem.fixedDistance['y'] = gridY
			gridItem.fixedDistance['z'] = gridZ

		if (self.form.userDefinedRadioButton.isChecked()):
			gridItem.type = "User Defined"
			gridItem.userDefined['data'] = self.form.userDefinedGridLinesTextInput.toPlainText()

		gridItem.units = self.form.gridUnitsInput.currentText()
		gridItem.units2 = self.form.gridUnitsInput_2.currentText()
		gridItem.generateLinesInside = self.form.gridGenerateLinesInsideCheckbox.isChecked()
		gridItem.topPriorityLines = self.form.gridTopPriorityLinesCheckbox.isChecked()

		return gridItem
		

	def gridSettingsAddButtonClicked(self):		
		settingsInst = self.getGridItemFromGui()

		#check if all items have same type of coordinate system
		currentSimulationGridType = self.getCurrentSimulationGridType()
		if currentSimulationGridType != None and settingsInst.coordsType != currentSimulationGridType:
			self.guiHelpers.displayMessage("All current defined grids are " + currentSimulationGridType + " you have to remove them or change type of current grid item.")
			return

		#check for duplicity in names if there is some warning message displayed
		#if everything is OK, item is added into tree
		isDuplicityName = self.checkTreeWidgetForDuplicityName(self.form.gridSettingsTreeView, settingsInst.name)
		if (not isDuplicityName):

			#disable/enable grid plane drawing if rectangular, for cylindrical just axis z
			if settingsInst.coordsType == "rectangular":
				self.form.auxGridAxis.setEnabled(True)				
			else:
				#set grid drawing plane to 'z' and disable chosing plane to draw grid
				index = self.form.auxGridAxis.findText('z', QtCore.Qt.MatchFixedString)
				if index >= 0:
					 self.form.auxGridAxis.setCurrentIndex(index)
				self.form.auxGridAxis.setEnabled(False)				

			#add item into gui tree views
			self.addSettingsItemGui(settingsInst)
			self.updateMeshPriorityDisableItems()	#update grid priority table at object assignment panel

	def gridSettingsRemoveButtonClicked(self):
		#selectedItem = self.form.gridSettingsTreeView.selectedItems()[0].data(0, QtCore.Qt.UserRole)
		#self.guiHelpers.displayMessage(selectedItem.serializeToString())

		selectedItem = self.form.gridSettingsTreeView.selectedItems()[0]
		print("Selected port name: " + selectedItem.text(0))

		gridGroupWidgetItems = self.form.objectAssignmentRightTreeWidget.findItems(
			selectedItem.text(0),
			QtCore.Qt.MatchExactly | QtCore.Qt.MatchFlag.MatchRecursive
			)
		gridGroupItem = None
		for item in gridGroupWidgetItems:
			if (item.parent().text(0) == "Grid"):
				gridGroupItem = item
		print("Currently removing port item: " + gridGroupItem.text(0))

		#	Remove from Priority List
		priorityName = gridGroupItem.parent().text(0) + ", " + gridGroupItem.text(0);
		self.removePriorityName(priorityName)

		#	Remove from Assigned Object
		self.form.gridSettingsTreeView.invisibleRootItem().removeChild(selectedItem)
		gridGroupItem.parent().removeChild(gridGroupItem)

		self.updateMeshPriorityDisableItems()	#update grid priority table at object assignment panel

	def gridSettingsUpdateButtonClicked(self):
		### capture UI settings	
		settingsInst = self.getGridItemFromGui() 

		### replace old with new settingsInst
		selectedItems = self.form.gridSettingsTreeView.selectedItems()
		if len(selectedItems) != 1:
			return
		selectedItems[0].setData(0, QtCore.Qt.UserRole, settingsInst)

		### update other UI elements to propagate changes
		# replace oudated copy of settingsInst 
		self.updateObjectAssignmentRightTreeWidgetItemData("Grid", selectedItems[0].text(0), settingsInst)		
		# update grid priority table at object assignment panel
		self.updateMeshPriorityDisableItems() 	
		

	def gridCoordsTypeChoosed(self):
		"""	
		if (self.form.gridRectangularRadio.isChecked()):
			self.form.gridUnitsInput.clear()
			self.form.gridUnitsInput.addItem("mm")
			self.form.gridUnitsInput.addItem("m")
			self.form.gridUnitsInput.addItem("cm")
			self.form.gridUnitsInput.addItem("nm")
			self.form.gridUnitsInput.addItem("pm")
			self.form.gridXEnable.setText("X")
			self.form.gridYEnable.setText("Y")
		
		if (self.form.gridCylindricalRadio.isChecked()):
			self.form.gridUnitsInput.clear()
			self.form.gridUnitsInput.addItem("rad")
			self.form.gridUnitsInput.addItem("deg")
			self.form.gridXEnable.setText("r")
			self.form.gridYEnable.setText("phi")
		"""

		if (self.form.gridRectangularRadio.isChecked()):
			self.form.gridXEnable.setText("X")
			self.form.gridYEnable.setText("Y")
			self.form.gridUnitsInput_2.setEnabled(False)
		
		if (self.form.gridCylindricalRadio.isChecked()):
			self.form.gridXEnable.setText("r")
			self.form.gridYEnable.setText("phi")
			self.form.gridUnitsInput_2.setEnabled(True)
		
	#
	# MATERIAL SETTINGS
	#  __  __       _______ ______ _____  _____          _         _____ ______ _______ _______ _____ _   _  _____  _____ 
	# |  \/  |   /\|__   __|  ____|  __ \|_   _|   /\   | |       / ____|  ____|__   __|__   __|_   _| \ | |/ ____|/ ____|
	# | \  / |  /  \  | |  | |__  | |__) | | |    /  \  | |      | (___ | |__     | |     | |    | | |  \| | |  __| (___  
	# | |\/| | / /\ \ | |  |  __| |  _  /  | |   / /\ \ | |       \___ \|  __|    | |     | |    | | | . ` | | |_ |\___ \ 
	# | |  | |/ ____ \| |  | |____| | \ \ _| |_ / ____ \| |____   ____) | |____   | |     | |   _| |_| |\  | |__| |____) |
	# |_|  |_/_/    \_\_|  |______|_|  \_\_____/_/    \_\______| |_____/|______|  |_|     |_|  |_____|_| \_|\_____|_____/ 
	#      

	def getMaterialItemFromGui(self):
		name = self.form.materialSettingsNameInput.text()
		epsilon = self.form.materialEpsilonNumberInput.value()
		mue = self.form.materialMueNumberInput.value()
		kappa = self.form.materialKappaNumberInput.value()
		sigma = self.form.materialSigmaNumberInput.value()
		
		materialItem = MaterialSettingsItem()
		materialItem.name = name
		materialItem.constants = {}	# !!! <--- THIS MUST BE HERE, OTHERWISE ALL CONSTANTS IN ALL MATERIAL ITEMS HAVE SAME VALUE LIKE REFERENCING SAME OBJECT
		materialItem.constants['epsilon'] = epsilon
		materialItem.constants['mue'] = mue
		materialItem.constants['kappa'] = kappa
		materialItem.constants['sigma'] = sigma	

		if (self.form.materialMetalRadioButton.isChecked() == 1):
			materialItem.type = "metal"
		elif (self.form.materialUserDefinedRadioButton.isChecked() == 1):
			materialItem.type = "userdefined"

		return materialItem
		
	
	def materialSettingsAddButtonClicked(self):
		materialItem = self.getMaterialItemFromGui()

		# display message box with current material settings to be added
		#self.guiHelpers.displayMessage(materialItem.serializeToString())

		#check for duplicity in names if there is some warning message displayed
		isDuplicityName = self.checkTreeWidgetForDuplicityName(self.form.materialSettingsTreeView, materialItem.name)

		if (not isDuplicityName):
			self.addSettingsItemGui(materialItem)
			

	def materialSettingsRemoveButtonClicked(self):
		selectedItem = self.form.materialSettingsTreeView.selectedItems()[0]
		print("Selected material name: " + selectedItem.text(0))

		materialGroupWidgetItems = self.form.objectAssignmentRightTreeWidget.findItems(
			selectedItem.text(0), 
			QtCore.Qt.MatchExactly | QtCore.Qt.MatchFlag.MatchRecursive
			)
		materialGroupItem = None
		for item in materialGroupWidgetItems:
			if (item.parent().text(0) == "Material"):
				materialGroupItem = item
		print("Currently removing material item: " + materialGroupItem.text(0))

		# Remove from Priority list
		priorityName = materialGroupItem.parent().text(0) + ", " + materialGroupItem.text(0);
		self.removePriorityName(priorityName)
		
		# Remove from Materials list
		self.form.materialSettingsTreeView.invisibleRootItem().removeChild(selectedItem)
		materialGroupItem.parent().removeChild(materialGroupItem)
		

	def materialSettingsUpdateButtonClicked(self):
		### capture UI settings
		settingsInst = self.getMaterialItemFromGui()
	
		### replace old with new settingsInst
		selectedItems = self.form.materialSettingsTreeView.selectedItems()
		if len(selectedItems) != 1:
			return
		selectedItems[0].setData(0, QtCore.Qt.UserRole, settingsInst)
		
		### update other UI elements to propagate changes
		# replace oudated copy of settingsInst 
		self.updateObjectAssignmentRightTreeWidgetItemData("Material", selectedItems[0].text(0), settingsInst)	


	# EXCITATION SETTINGS
	#  ________   _______ _____ _______    _______ _____ ____  _   _    _____ ______ _______ _______ _____ _   _  _____  _____ 
	# |  ____\ \ / / ____|_   _|__   __|/\|__   __|_   _/ __ \| \ | |  / ____|  ____|__   __|__   __|_   _| \ | |/ ____|/ ____|
	# | |__   \ V / |      | |    | |  /  \  | |    | || |  | |  \| | | (___ | |__     | |     | |    | | |  \| | |  __| (___  
	# |  __|   > <| |      | |    | | / /\ \ | |    | || |  | | . ` |  \___ \|  __|    | |     | |    | | | . ` | | |_ |\___ \ 
	# | |____ / . \ |____ _| |_   | |/ ____ \| |   _| || |__| | |\  |  ____) | |____   | |     | |   _| |_| |\  | |__| |____) |
	# |______/_/ \_\_____|_____|  |_/_/    \_\_|  |_____\____/|_| \_| |_____/|______|  |_|     |_|  |_____|_| \_|\_____|_____/ 
	#                                                                                                                          

	def getExcitationItemFromGui(self):
		name = self.form.excitationSettingsNameInput.text()

		excitationItem = ExcitationSettingsItem()
		excitationItem.name = name
		excitationItem.units = self.form.excitationUnitsNumberInput.currentText()

		if (self.form.sinusodialExcitationRadioButton.isChecked()):
			excitationItem.type = 'sinusodial'
			excitationItem.sinusodial = {}
			excitationItem.sinusodial['f0'] = self.form.sinusodialExcitationF0NumberInput.value()
		if (self.form.gaussianExcitationRadioButton.isChecked()):
			excitationItem.type = 'gaussian'
			excitationItem.gaussian = {}
			excitationItem.gaussian['fc'] = self.form.gaussianExcitationFcNumberInput.value()
			excitationItem.gaussian['f0'] = self.form.gaussianExcitationF0NumberInput.value()
		if (self.form.customExcitationRadioButton.isChecked()):
			excitationItem.type = 'custom'
			excitationItem.custom = {}
			excitationItem.custom['functionStr'] = self.form.customExcitationTextInput.text()
			excitationItem.custom['f0'] = self.form.customExcitationF0NumberInput.value()
		return excitationItem


	def excitationSettingsAddButtonClicked(self):
		settingsInst = self.getExcitationItemFromGui()

		#check for duplicity in names if there is some warning message displayed
		isDuplicityName = self.checkTreeWidgetForDuplicityName(self.form.excitationSettingsTreeView, settingsInst.name)
		isMoreThanOne = self.form.excitationSettingsTreeView.topLevelItemCount() > 0

		if (isDuplicityName):
			return
		if (isMoreThanOne):
			self.guiHelpers.displayMessage("There could be just one excitation!")
			return
		
		self.addSettingsItemGui(settingsInst)
		

	def excitationSettingsRemoveButtonClicked(self):
		selectedItem = self.form.excitationSettingsTreeView.selectedItems()[0]
		print("Selected port name: " + selectedItem.text(0))

		excitationGroupWidgetItems = self.form.objectAssignmentRightTreeWidget.findItems(
			selectedItem.text(0),
			QtCore.Qt.MatchExactly | QtCore.Qt.MatchFlag.MatchRecursive
			)
		excitationGroupItem = None
		for item in excitationGroupWidgetItems:
			if (item.parent().text(0) == "Excitation"):
				excitationGroupItem = item
		print("Currently removing port item: " + excitationGroupItem.text(0))

		self.form.excitationSettingsTreeView.invisibleRootItem().removeChild(selectedItem)
		excitationGroupItem.parent().removeChild(excitationGroupItem)

	def excitationSettingsUpdateButtonClicked(self):
		### capture UI settings
		settingsInst = self.getExcitationItemFromGui()
	
		### replace old with new settingsInst
		selectedItems = self.form.excitationSettingsTreeView.selectedItems()
		if len(selectedItems) != 1:
			return
		selectedItems[0].setData(0, QtCore.Qt.UserRole, settingsInst)
		
		### update other UI elements to propagate changes
		# replace oudated copy of settingsInst 
		self.updateObjectAssignmentRightTreeWidgetItemData("Excitation", selectedItems[0].text(0), settingsInst)	



	# PORT SETTINGS
	#  _____   ____  _____ _______    _____ ______ _______ _______ _____ _   _  _____  _____ 
	# |  __ \ / __ \|  __ \__   __|  / ____|  ____|__   __|__   __|_   _| \ | |/ ____|/ ____|
	# | |__) | |  | | |__) | | |    | (___ | |__     | |     | |    | | |  \| | |  __| (___  
	# |  ___/| |  | |  _  /  | |     \___ \|  __|    | |     | |    | | | . ` | | |_ |\___ \ 
	# | |    | |__| | | \ \  | |     ____) | |____   | |     | |   _| |_| |\  | |__| |____) |
	# |_|     \____/|_|  \_\ |_|    |_____/|______|  |_|     |_|  |_____|_| \_|\_____|_____/ 
	#    

	def getPortItemFromGui(self):
		name = self.form.portSettingsNameInput.text()

		portItem = PortSettingsItem()
		portItem.name = name

		portItem.R = self.form.portResistanceInput.value()
		portItem.RUnits = self.form.portResistanceUnitsInput.currentText()
		portItem.isActive = self.form.portActive.isChecked()
		portItem.direction = self.form.portDirectionInput.currentText()

		if (self.form.lumpedPortRadioButton.isChecked()):
			portItem.type = "lumped"
		if (self.form.microstripPortRadioButton.isChecked()):
			portItem.type = "microstrip"

		if (self.form.circularWaveguidePortRadioButton.isChecked()):
			portItem.type = "circular waveguide"
			portItem.modeName = self.form.portWaveguideModeName.currentText()
			portItem.polarizationAngle = self.form.portWaveguidePolarizationAngle.currentText()
			portItem.excitationAmplitude = self.form.portWaveguideExcitationAmplitude.value()

		if (self.form.rectangularWaveguidePortRadioButton.isChecked()):
			portItem.type = "rectangular waveguide"
		if (self.form.etDumpPortRadioButton.isChecked()):
			portItem.type = "et dump"
		if (self.form.htDumpPortRadioButton.isChecked()):
			portItem.type = "ht dump"
		if (self.form.nf2ffBoxPortRadioButton.isChecked()):
			portItem.type = "nf2ff box"
			
		return portItem
		
	
	def portSettingsAddButtonClicked(self):
		settingsInst = self.getPortItemFromGui()

		#check for duplicity in names if there is some warning message displayed
		isDuplicityName = self.checkTreeWidgetForDuplicityName(self.form.portSettingsTreeView, settingsInst.name)

		if (not isDuplicityName):
			self.addSettingsItemGui(settingsInst)
			if (settingsInst.type == "nf2ff box"):
				self.updateNF2FFList()


	def portSettingsRemoveButtonClicked(self):
		selectedItem = self.form.portSettingsTreeView.selectedItems()[0]
		print("Selected port name: " + selectedItem.text(0))

		portGroupWidgetItems = self.form.objectAssignmentRightTreeWidget.findItems(
			selectedItem.text(0),
			QtCore.Qt.MatchExactly | QtCore.Qt.MatchFlag.MatchRecursive
			)
		portGroupItem = None
		for item in portGroupWidgetItems:
			if (item.parent().text(0) == "Port"):
				portGroupItem = item
		print("Currently removing port item: " + portGroupItem.text(0))

		# Removing from Priority List
		priorityName = portGroupItem.parent().text(0) + ", " + portGroupItem.text(0);
		self.removePriorityName(priorityName)

		# Removing from Object Assugnment Tree
		self.form.portSettingsTreeView.invisibleRootItem().removeChild(selectedItem)
		portGroupItem.parent().removeChild(portGroupItem)

		# If NF2FF box removed then update NF2FF list on POSTPROCESSING TAB
		if (portGroupItem.data(0, QtCore.Qt.UserRole).type == "nf2ff box"):
			self.updateNF2FFList()
			

	def portSettingsUpdateButtonClicked(self):
		### capture UI settings
		settingsInst = self.getPortItemFromGui()
	
		### replace old with new settingsInst
		selectedItems = self.form.portSettingsTreeView.selectedItems()
		if len(selectedItems) != 1:
			return
		selectedItems[0].setData(0, QtCore.Qt.UserRole, settingsInst)
		
		### update other UI elements to propagate changes
		# replace oudated copy of settingsInst 
		self.updateObjectAssignmentRightTreeWidgetItemData("Port", selectedItems[0].text(0), settingsInst)	



	def portSettingsTypeChoosed(self):
		if (self.form.circularWaveguidePortRadioButton.isChecked()):
			self.form.waveguideSettingsGroup.setEnabled(True)
		else:
			self.form.waveguideSettingsGroup.setEnabled(False)


	#  _     _    _ __  __ _____  ______ _____    _____        _____ _______            _   _   _                 
	# | |   | |  | |  \/  |  __ \|  ____|  __ \  |  __ \ /\   |  __ \__   __|          | | | | (_)                
	# | |   | |  | | \  / | |__) | |__  | |  | | | |__) /  \  | |__) | | |     ___  ___| |_| |_ _ _ __   __ _ ___ 
	# | |   | |  | | |\/| |  ___/|  __| | |  | | |  ___/ /\ \ |  _  /  | |    / __|/ _ \ __| __| | '_ \ / _` / __|
	# | |___| |__| | |  | | |    | |____| |__| | | |  / ____ \| | \ \  | |    \__ \  __/ |_| |_| | | | | (_| \__ \
	# |______\____/|_|  |_|_|    |______|_____/  |_| /_/    \_\_|  \_\ |_|    |___/\___|\__|\__|_|_| |_|\__, |___/
	#                                                                                                    __/ |    
	#                                                                                                   |___/    
	#
	
	def getLumpedPartItemFromGui(self):
		name = self.form.lumpedPartSettingsNameInput.text()

		lumpedPartItem = LumpedPartSettingsItem()
		lumpedPartItem.name = name

		if (self.form.lumpedPartLEnable.isChecked()):
			lumpedPartItem.params['L'] = self.form.lumpedPartLInput.value()
			lumpedPartItem.params['LUnits'] = self.form.lumpedPartLUnits.currentText()
			lumpedPartItem.params['LEnabled'] = 1
		if (self.form.lumpedPartREnable.isChecked()):
			lumpedPartItem.params['R'] = self.form.lumpedPartRInput.value()
			lumpedPartItem.params['RUnits'] = self.form.lumpedPartRUnits.currentText()
			lumpedPartItem.params['REnabled'] = 1
		if (self.form.lumpedPartCEnable.isChecked()):
			lumpedPartItem.params['C'] = self.form.lumpedPartCInput.value()
			lumpedPartItem.params['CUnits'] = self.form.lumpedPartCUnits.currentText()
			lumpedPartItem.params['CEnabled'] = 1

		return lumpedPartItem
		
	
	def lumpedPartSettingsAddButtonClicked(self):
		# capture UI settings
		settingsInst = self.getLumpedPartItemFromGui()		

		#check for duplicity in names if there is some warning message displayed
		isDuplicityName = self.checkTreeWidgetForDuplicityName(self.form.lumpedPartTreeView, settingsInst.name)
		if (not isDuplicityName):
			self.addSettingsItemGui(settingsInst)
			

	def lumpedPartSettingsRemoveButtonClicked(self):
		selectedItem = self.form.lumpedPartTreeView.selectedItems()[0]
		print("Selected lumpedpart name: " + selectedItem.text(0))

		lumpedPartGroupWidgetItems = self.form.objectAssignmentRightTreeWidget.findItems(
			selectedItem.text(0),
			QtCore.Qt.MatchExactly|QtCore.Qt.MatchFlag.MatchRecursive
			)
		lumpedPartGroupItem = None
		for item in lumpedPartGroupWidgetItems:
			if (item.parent().text(0) == "LumpedPart"):
				lumpedPartGroupItem = item
		print("Currently removing lumped part item: " + lumpedPartGroupItem.text(0))

		###
		#	Removing from Priority List
		###
		priorityName = lumpedPartGroupItem.parent().text(0) + ", " + lumpedPartGroupItem.text(0);
		self.removePriorityName(priorityName)

		self.form.lumpedPartTreeView.invisibleRootItem().removeChild(selectedItem)
		lumpedPartGroupItem.parent().removeChild(lumpedPartGroupItem)
		

	def lumpedPartSettingsUpdateButtonClicked(self):
		### capture UI settings
		settingsInst = self.getLumpedPartItemFromGui()		
	
		### replace old with new settingsInst
		selectedItems = self.form.portSettingsTreeView.selectedItems()
		if len(selectedItems) != 1:
			return
		selectedItems[0].setData(0, QtCore.Qt.UserRole, settingsInst)
		
		### update other UI elements to propagate changes
		# replace oudated copy of settingsInst 
		self.updateObjectAssignmentRightTreeWidgetItemData("LumpedPart", selectedItems[0].text(0), settingsInst)	



	#   _____________   ____________  ___    __       _____ _______________________   _____________
	#  / ____/ ____/ | / / ____/ __ \/   |  / /      / ___// ____/_  __/_  __/  _/ | / / ____/ ___/
	# / / __/ __/ /  |/ / __/ / /_/ / /| | / /       \__ \/ __/   / /   / /  / //  |/ / / __ \__ \ 
	#/ /_/ / /___/ /|  / /___/ _, _/ ___ |/ /___    ___/ / /___  / /   / / _/ // /|  / /_/ /___/ / 
	#\____/_____/_/ |_/_____/_/ |_/_/  |_/_____/   /____/_____/ /_/   /_/ /___/_/ |_/\____//____/  
	#
	def materialTreeWidgetItemChanged(self, current, previous):
		print("Material item changed.")

		#if last item was erased from port list do nothing
		if not self.form.materialSettingsTreeView.currentItem():
			return

		currSetting = self.form.materialSettingsTreeView.currentItem().data(0, QtCore.Qt.UserRole)
		self.form.materialSettingsNameInput.setText(currSetting.name)

		#ATTENTIONS there is ocnversion to float() used BELOW
		if (currSetting.type == 'metal'):
			self.form.materialMetalRadioButton.click()
		elif (currSetting.type == 'userdefined'):
			self.form.materialUserDefinedRadioButton.click()

		self.form.materialEpsilonNumberInput.setValue(float(currSetting.constants['epsilon']))
		self.form.materialMueNumberInput.setValue(float(currSetting.constants['mue']))
		self.form.materialKappaNumberInput.setValue(float(currSetting.constants['kappa']))
		self.form.materialSigmaNumberInput.setValue(float(currSetting.constants['sigma']))
		return

	def gridTreeWidgetItemChanged(self, current, previous):
		print("Grid item changed.")

		#if last item was erased from port list do nothing
		if not self.form.gridSettingsTreeView.currentItem():
			return

		#set values to zero to not left previous settings to confuse user
		self.form.fixedDistanceXNumberInput.setValue(0)
		self.form.fixedDistanceYNumberInput.setValue(0)
		self.form.fixedDistanceZNumberInput.setValue(0)
		self.form.fixedCountXNumberInput.setValue(0)
		self.form.fixedCountYNumberInput.setValue(0)
		self.form.fixedCountZNumberInput.setValue(0)
		self.form.userDefinedGridLinesTextInput.setPlainText("")
		self.form.gridXEnable.setChecked(False)
		self.form.gridYEnable.setChecked(False)
		self.form.gridZEnable.setChecked(False)
		self.form.gridGenerateLinesInsideCheckbox.setChecked(False)
		self.form.gridTopPriorityLinesCheckbox.setChecked(False)

		#set values in grid settings by actual selected item
		currSetting = self.form.gridSettingsTreeView.currentItem().data(0, QtCore.Qt.UserRole)
		self.form.gridSettingsNameInput.setText(currSetting.name)

		index = self.form.gridUnitsInput.findText(currSetting.units, QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.gridUnitsInput.setCurrentIndex(index)

		if (currSetting.coordsType == "rectangular"):
			self.form.gridRectangularRadio.click()
		if (currSetting.coordsType == "cylindrical"):
			self.form.gridCylindricalRadio.click()

		if (currSetting.type == "Fixed Distance"):
			self.form.fixedDistanceRadioButton.click()
			self.form.fixedDistanceXNumberInput.setValue(currSetting.fixedDistance['x'])
			self.form.fixedDistanceYNumberInput.setValue(currSetting.fixedDistance['y'])
			self.form.fixedDistanceZNumberInput.setValue(currSetting.fixedDistance['z'])
		elif (currSetting.type == "Fixed Count"):
			self.form.fixedCountRadioButton.click()
			self.form.fixedCountXNumberInput.setValue(currSetting.fixedCount['x'])
			self.form.fixedCountYNumberInput.setValue(currSetting.fixedCount['y'])
			self.form.fixedCountZNumberInput.setValue(currSetting.fixedCount['z'])
			pass
		elif (currSetting.type == "User Defined"):
			self.form.userDefinedRadioButton.click()
			self.form.userDefinedGridLinesTextInput.setPlainText(currSetting.userDefined['data'])
			pass
		else:
			pass
			
		self.form.gridXEnable.setChecked(currSetting.xenabled)
		self.form.gridYEnable.setChecked(currSetting.yenabled)
		self.form.gridZEnable.setChecked(currSetting.zenabled)

		self.form.gridGenerateLinesInsideCheckbox.setChecked(currSetting.generateLinesInside)
		self.form.gridTopPriorityLinesCheckbox.setChecked(currSetting.topPriorityLines)

		return

	def excitationTreeWidgetItemChanged(self, current, previous):
		print("Excitation item changed.")

		#if last item was erased from port list do nothing
		if not self.form.excitationSettingsTreeView.currentItem():
			return

		currSetting = self.form.excitationSettingsTreeView.currentItem().data(0, QtCore.Qt.UserRole)
		self.form.excitationSettingsNameInput.setText(currSetting.name)
		if (currSetting.type == "sinusodial"):
			self.form.sinusodialExcitationRadioButton.click()
			self.form.sinusodialExcitationF0NumberInput.setValue(currSetting.sinusodial['f0'])
		elif (currSetting.type == "gaussian"):
			self.form.gaussianExcitationRadioButton.click()
			self.form.gaussianExcitationF0NumberInput.setValue(currSetting.gaussian['f0'])
			self.form.gaussianExcitationFcNumberInput.setValue(currSetting.gaussian['fc'])
			pass
		elif (currSetting.type == "custom"):
			self.form.customExcitationRadioButton.click()
			self.form.customExcitationTextInput.setText(currSetting.custom['functionStr'])
			self.form.customExcitationF0NumberInput.setValue(currSetting.custom['f0'])
			
			index = self.form.excitationUnitsNumberInput.findText(currSetting.units, QtCore.Qt.MatchFixedString)
			if index >= 0:
				self.form.excitationUnitsNumberInput.setCurrentIndex(index)
			pass
		else:
			return #no gui update
			
		index = self.form.excitationUnitsNumberInput.findText(currSetting.units, QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.excitationUnitsNumberInput.setCurrentIndex(index)

		return

	def portTreeWidgetItemChanged(self, current, previous):
		print("Port item changed.")

		#if last item was erased from port list do nothing
		if not self.form.portSettingsTreeView.currentItem():
			return

		currSetting = self.form.portSettingsTreeView.currentItem().data(0, QtCore.Qt.UserRole)
		self.form.portSettingsNameInput.setText(currSetting.name)
		self.form.portResistanceInput.setValue(float(currSetting.R))

		#set active port field direction
		index = self.form.portDirectionInput.findText(currSetting.direction, QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.portDirectionInput.setCurrentIndex(index)		

		index = self.form.portResistanceUnitsInput.findText(currSetting.RUnits, QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.portResistanceUnitsInput.setCurrentIndex(index)

		self.form.portResistanceInput.setEnabled(True)
		self.form.portResistanceUnitsInput.setEnabled(True)

		if (currSetting.type.lower() == "lumped"):
			self.form.lumpedPortRadioButton.click()

		elif (currSetting.type.lower() == "microstrip"):
			self.form.microstripPortRadioButton.click()

		elif (currSetting.type.lower() == "circular waveguide"):
			self.form.circularWaveguidePortRadioButton.click()

			#set mode, e.g. TE11, TM21, ...
			index = self.form.portWaveguideModeName.findText(currSetting.modeName, QtCore.Qt.MatchFixedString)
			if index >= 0:
				self.form.portWaveguideModeName.setCurrentIndex(index)

			#set polarization angle
			index = self.form.portWaveguidePolarizationAngle.findText(currSetting.polarizationAngle, QtCore.Qt.MatchFixedString)
			if index >= 0:
				self.form.portWaveguidePolarizationAngle.setCurrentIndex(index)

			self.form.portWaveguideExcitationAmplitude.setValue(float(currSetting.excitationAmplitude))

		elif (currSetting.type.lower() == "rectangular waveguide"):
			self.form.rectangularWaveguidePortRadioButton.click()
		elif (currSetting.type.lower() == "et dump"):
			self.form.portResistanceInput.setEnabled(False)
			self.form.portResistanceUnitsInput.setEnabled(False)
			self.form.etDumpPortRadioButton.click()
		elif (currSetting.type.lower() == "ht dump"):
			self.form.portResistanceInput.setEnabled(False)
			self.form.portResistanceUnitsInput.setEnabled(False)
			self.form.htDumpPortRadioButton.click()
		elif (currSetting.type.lower() == "nf2ff box"):
			self.form.portResistanceInput.setEnabled(False)
			self.form.portResistanceUnitsInput.setEnabled(False)
			self.form.nf2ffBoxPortRadioButton.click()
		else:
			pass #no gui update

		self.form.portActive.setChecked(currSetting.isActive)	#convert value from INI file to bool

		return

	def simulationTreeWidgetItemChanged(self, current, previous):
		print("Simulation params changed.")
		return

	def lumpedPartTreeWidgetItemChanged(self, current, previous):
		print("Lumped part item changed.")

		#if last item was erased from port list do nothing
		if not self.form.lumpedPartTreeView.currentItem():
			return

		currSetting = self.form.lumpedPartTreeView.currentItem().data(0, QtCore.Qt.UserRole)
		self.form.lumpedPartSettingsNameInput.setText(currSetting.name)

		self.form.lumpedPartLEnable.setChecked(False)
		self.form.lumpedPartREnable.setChecked(False)
		self.form.lumpedPartCEnable.setChecked(False)
		if (currSetting.params['LEnabled']):
			self.form.lumpedPartLEnable.setChecked(True)
		if (currSetting.params['REnabled']):
			self.form.lumpedPartREnable.setChecked(True)
		if (currSetting.params['CEnabled']):
			self.form.lumpedPartCEnable.setChecked(True)

		self.form.lumpedPartLInput.setValue(currSetting.params['L'])
		self.form.lumpedPartRInput.setValue(currSetting.params['R'])
		self.form.lumpedPartCInput.setValue(currSetting.params['C'])

		index = self.form.lumpedPartLUnits.findText(currSetting.params['LUnits'], QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.lumpedPartLUnits.setCurrentIndex(index)
		index = self.form.lumpedPartRUnits.findText(currSetting.params['RUnits'], QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.lumpedPartRUnits.setCurrentIndex(index)
		index = self.form.lumpedPartCUnits.findText(currSetting.params['CUnits'], QtCore.Qt.MatchFixedString)
		if index >= 0:
			self.form.lumpedPartCUnits.setCurrentIndex(index)

		return

	def setSimlationParamBC(self, comboBox, strValue):
		index = comboBox.findText(strValue, QtCore.Qt.MatchFixedString)
		if index >= 0:
			comboBox.setCurrentIndex(index)

	####################################################################################################################################################################
	# GUI SAVE/LOAD buttons
	####################################################################################################################################################################

	#   _____    __      ________    _____ ______ _______ _______ _____ _   _  _____  _____ 
	#  / ____|  /\ \    / /  ____|  / ____|  ____|__   __|__   __|_   _| \ | |/ ____|/ ____|
	# | (___   /  \ \  / /| |__    | (___ | |__     | |     | |    | | |  \| | |  __| (___  
	#  \___ \ / /\ \ \/ / |  __|    \___ \|  __|    | |     | |    | | | . ` | | |_ |\___ \ 
	#  ____) / ____ \  /  | |____   ____) | |____   | |     | |   _| |_| |\  | |__| |____) |
	# |_____/_/    \_\/   |______| |_____/|______|  |_|     |_|  |_____|_| \_|\_____|_____/ 
	#
	def saveCurrentSettingsButtonClicked(self):
		programname = os.path.basename(App.ActiveDocument.FileName)
		programdir = os.path.dirname(App.ActiveDocument.FileName)
		programbase, ext = os.path.splitext(programname)  # extract basename and ext from filename
		outFile = programdir + '/' + programbase + "_settings.ini"
		print("Saving settings to file: " + outFile)
		if self.statusBar is not None:
			self.statusBar.showMessage("Saving settings to file...", 5000)
			QtGui.QApplication.processEvents()

		if (os.path.exists(outFile)):
			os.remove(outFile)	# Remove outFile in case an old version exists.

		settings = QtCore.QSettings(outFile, QtCore.QSettings.IniFormat)    

		# SAVE MATERIAL SETTINGS
		
		materialList = self.openEMSObj.getAllTreeWidgetItems(self.form.materialSettingsTreeView)
		for k in range(len(materialList)):
			print("Save new MATERIAL constants into file: ")
			print(materialList[k].constants)
	
			settings.beginGroup("MATERIAL-" + materialList[k].getName())
			settings.setValue("type", materialList[k].type)
			settings.setValue("material_epsilon", materialList[k].constants['epsilon'])
			settings.setValue("material_mue", materialList[k].constants['mue'])
			settings.setValue("material_kappa", materialList[k].constants['kappa'])
			settings.setValue("material_sigma", materialList[k].constants['sigma'])
			settings.endGroup()

		# SAVE GRID SETTINGS
		
		gridList = self.openEMSObj.getAllTreeWidgetItems(self.form.gridSettingsTreeView)
		for k in range(len(gridList)):
			print("Save new GRID constants into file: " + gridList[k].getName())
	
			settings.beginGroup("GRID-" + gridList[k].getName())
			settings.setValue("coordsType", gridList[k].coordsType)
			settings.setValue("type", gridList[k].type)
			settings.setValue("units", gridList[k].units)
			settings.setValue("xenabled", gridList[k].xenabled)
			settings.setValue("yenabled", gridList[k].yenabled)
			settings.setValue("zenabled", gridList[k].zenabled)
			settings.setValue("fixedCount", json.dumps(gridList[k].fixedCount))
			settings.setValue("fixedDistance", json.dumps(gridList[k].fixedDistance))
			settings.setValue("userDefined", json.dumps(gridList[k].userDefined))
			settings.setValue("generateLinesInside", gridList[k].generateLinesInside)
			settings.setValue("topPriorityLines", gridList[k].topPriorityLines)
			settings.endGroup()

		# SAVE EXCITATION
		
		excitationList = self.openEMSObj.getAllTreeWidgetItems(self.form.excitationSettingsTreeView)
		for k in range(len(excitationList)):
			print("Save new EXCITATION constants into file: " + excitationList[k].getName())
	
			settings.beginGroup("EXCITATION-" + excitationList[k].getName())
			settings.setValue("type", excitationList[k].type)
			settings.setValue("sinusodial", json.dumps(excitationList[k].sinusodial))
			settings.setValue("gaussian", json.dumps(excitationList[k].gaussian))
			settings.setValue("custom", json.dumps(excitationList[k].custom))
			settings.setValue("units", excitationList[k].units)
			settings.endGroup()

		# SAVE PORT SETTINGS
		
		portList = self.openEMSObj.getAllTreeWidgetItems(self.form.portSettingsTreeView)
		for k in range(len(portList)):
			print("Save new PORT constants into file: " + portList[k].getName())
	
			settings.beginGroup("PORT-" + portList[k].getName())
			settings.setValue("type", portList[k].type)
			settings.setValue("R", portList[k].R)
			settings.setValue("RUnits", portList[k].RUnits)
			settings.setValue("isActive", portList[k].isActive)
			settings.setValue("direction", portList[k].direction)

			if (portList[k].type == "circular waveguide"):
				settings.setValue("modeName", portList[k].modeName)
				settings.setValue("polarizationAngle", portList[k].polarizationAngle)
				settings.setValue("excitationAmplitude", portList[k].excitationAmplitude)

			settings.endGroup()

		# SAVE SIMULATION PARAMS
		
		simulationSettings = SimulationSettingsItem("Hardwired Name 1")
		
		simulationSettings.params['max_timestamps'] = self.form.simParamsMaxTimesteps.value()
		simulationSettings.params['min_decrement']  = self.form.simParamsMinDecrement.value()
		
		simulationSettings.params['generateJustPreview'] = self.form.generateJustPreviewCheckbox.isChecked()
		simulationSettings.params['generateDebugPEC']    = self.form.generateDebugPECCheckbox.isChecked()
		simulationSettings.params['mFileExecCommand']    = self.form.octaveExecCommandList.currentText()
		simulationSettings.params['base_length_unit_m']  = self.form.simParamsDeltaUnitList.currentText()
		
		simulationSettings.params['BCxmin'] = self.form.BCxmin.currentText()
		simulationSettings.params['BCxmax'] = self.form.BCxmax.currentText()
		simulationSettings.params['BCymin'] = self.form.BCymin.currentText()
		simulationSettings.params['BCymax'] = self.form.BCymax.currentText()
		simulationSettings.params['BCzmin'] = self.form.BCzmin.currentText()
		simulationSettings.params['BCzmax'] = self.form.BCzmax.currentText()
		simulationSettings.params['PMLxmincells'] = self.form.PMLxmincells.value()
		simulationSettings.params['PMLxmaxcells'] = self.form.PMLxmaxcells.value()
		simulationSettings.params['PMLymincells'] = self.form.PMLymincells.value()
		simulationSettings.params['PMLymaxcells'] = self.form.PMLymaxcells.value()
		simulationSettings.params['PMLzmincells'] = self.form.PMLzmincells.value()
		simulationSettings.params['PMLzmaxcells'] = self.form.PMLzmaxcells.value()
		simulationSettings.params['min_gridspacing_x'] = self.form.genParamMinGridSpacingX.value()
		simulationSettings.params['min_gridspacing_y'] = self.form.genParamMinGridSpacingY.value()
		simulationSettings.params['min_gridspacing_z'] = self.form.genParamMinGridSpacingZ.value()

		settings.beginGroup("SIMULATION-" + simulationSettings.name)
		settings.setValue("name", simulationSettings.name)
		settings.setValue("params", json.dumps(simulationSettings.params))
		settings.endGroup()

		#SAVE OBJECT ASSIGNMENTS	
		
		topItemsCount = self.form.objectAssignmentRightTreeWidget.topLevelItemCount()
		objCounter = 0
		for k in range(topItemsCount):
			topItem = self.form.objectAssignmentRightTreeWidget.topLevelItem(k)
			topItemName = topItem.text(0)
			print("---> topItem: " + topItem.text(0))
			for m in range(topItem.childCount()):
				childItem = topItem.child(m)
				childItemName = childItem.text(0)
				print("Save new OBJECT ASSIGNMENTS for category -> settings profile: ")
				print("\t" + topItemName + " --> " + childItemName)
				for n in range(childItem.childCount()):
					objItem = childItem.child(n)
					objItemName = objItem.text(0)

					#get unique FreeCAD internal item ID saved in FreeCADSettingsItem
					objItemId = objItem.data(0, QtCore.Qt.UserRole).getFreeCadId()
	
					settings.beginGroup("_OBJECT" + str(objCounter) + "-" + objItemName)
					settings.setValue("type", "FreeCadObj")
					settings.setValue("parent", childItemName)
					settings.setValue("category", topItemName)
					settings.setValue("freeCadId", objItemId)
					settings.endGroup()

					objCounter += 1
					
		#SAVE LUMPED PART SETTINGS

		lumpedPartList = self.openEMSObj.getAllTreeWidgetItems(self.form.lumpedPartTreeView)
		print("Lumped part list contains " + str(len(lumpedPartList)) + " items.")
		for k in range(len(lumpedPartList)):
			print("Saving new LUMPED PART " + lumpedPartList[k].getName())
	
			settings.beginGroup("LUMPEDPART-" + lumpedPartList[k].getName())
			settings.setValue("params", json.dumps(lumpedPartList[k].params))
			settings.endGroup()

		#SAVE PRIORITY OBJECT LIST SETTINGS

		settings.beginGroup("PRIORITYLIST-OBJECTS")
		priorityObjList = self.form.objectAssignmentPriorityTreeView

		print("Priority list contains " + str(priorityObjList.topLevelItemCount()) + " items.")
		for k in range(priorityObjList.topLevelItemCount()):
			priorityObjName = priorityObjList.topLevelItem(k).text(0)
			print("Saving new PRIORITY for " + priorityObjName)	
			settings.setValue(priorityObjName, str(k))
		settings.endGroup()

		#SAVE MESH PRIORITY

		settings.beginGroup("PRIORITYLIST-MESH")
		priorityMeshObjList = self.form.meshPriorityTreeView

		print("Priority list contains " + str(priorityMeshObjList.topLevelItemCount()) + " items.")
		for k in range(priorityMeshObjList.topLevelItemCount()):
			priorityMeshObjName = priorityMeshObjList.topLevelItem(k).text(0)
			print("Saving new MESH PRIORITY for " + priorityMeshObjName)	
			settings.setValue(priorityMeshObjName, str(k))
		settings.endGroup()


		#SAVE POSTPROCESSING OPTIONS

		settings.beginGroup("POSTPROCESSING-DefaultName")
		settings.setValue("nf2ffObject", self.form.portNf2ffObjectList.currentText())
		settings.setValue("nf2ffFreq", self.form.portNf2ffFreq.value())
		settings.setValue("nf2ffThetaStart", self.form.portNf2ffThetaStart.value())
		settings.setValue("nf2ffThetaStop", self.form.portNf2ffThetaStop.value())
		settings.setValue("nf2ffThetaStep", self.form.portNf2ffThetaStep.value())
		settings.setValue("nf2ffPhiStart", self.form.portNf2ffPhiStart.value())
		settings.setValue("nf2ffPhiStop", self.form.portNf2ffPhiStop.value())
		settings.setValue("nf2ffPhiStep", self.form.portNf2ffPhiStep.value())
		settings.endGroup()


		#sys.exit()  # prevents second call
		print("Current settings saved to file: " + outFile)
		self.guiHelpers.displayMessage("Settings saved to file: " + outFile, forceModal=False)
		return


	#  _      ____          _____     _____ ______ _______ _______ _____ _   _  _____  _____ 
	# | |    / __ \   /\   |  __ \   / ____|  ____|__   __|__   __|_   _| \ | |/ ____|/ ____|
	# | |   | |  | | /  \  | |  | | | (___ | |__     | |     | |    | | |  \| | |  __| (___  
	# | |   | |  | |/ /\ \ | |  | |  \___ \|  __|    | |     | |    | | | . ` | | |_ |\___ \ 
	# | |___| |__| / ____ \| |__| |  ____) | |____   | |     | |   _| |_| |\  | |__| |____) |
	# |______\____/_/    \_\_____/  |_____/|______|  |_|     |_|  |_____|_| \_|\_____|_____/ 
	#                                                                                       
	def loadCurrentSettingsButtonClicked(self):
		print("Load current values from file.")
		if self.statusBar is not None:
			self.statusBar.showMessage("Loading current values from file...", 5000)
			QtGui.QApplication.processEvents()

		#FIRST DELETE ALL GUI TREE WIDGET ITEMS
		self.deleteAllSettings()

		#
		# DEBUG: now read hardwired file name with __file__ + "_settings.ini"
		#
		programname = os.path.basename(App.ActiveDocument.FileName)
		programdir = os.path.dirname(App.ActiveDocument.FileName)
		programbase, ext = os.path.splitext(programname)  # extract basename and ext from filename
		outFile = programdir + '/' + programbase + "_settings.ini"
		print("Loading data from file: " + outFile)
		settings = QtCore.QSettings(outFile, QtCore.QSettings.IniFormat)    

		#
		# LOADING ITEMS FROM SETTINGS FILE
		#
		print("Settings file groups:", end="")
		print(settings.childGroups())
		for settingsGroup in settings.childGroups():

			#extract category name from ini name
			itemNameReg = re.search("-(.*)", settingsGroup)
			itemName = itemNameReg.group(1)

			if (re.compile("EXCITATION").search(settingsGroup)):
				print("Excitation item settings found.")
				settings.beginGroup(settingsGroup)
				categorySettings = ExcitationSettingsItem()
				categorySettings.name = itemName
				categorySettings.type = settings.value('type')
				categorySettings.sinusodial = json.loads(settings.value('sinusodial'))
				categorySettings.gaussian = json.loads(settings.value('gaussian'))
				categorySettings.custom = json.loads(settings.value('custom'))
				categorySettings.units = settings.value('units')
				settings.endGroup()

			elif (re.compile("GRID").search(settingsGroup)):
				print("GRID item settings found.")
				settings.beginGroup(settingsGroup)
				categorySettings = GridSettingsItem()
				categorySettings.name = itemName
				categorySettings.coordsType = settings.value('coordsType')
				categorySettings.type = settings.value('type')
				categorySettings.xenabled = _bool(settings.value('xenabled'))
				categorySettings.yenabled = _bool(settings.value('yenabled'))
				categorySettings.zenabled = _bool(settings.value('zenabled'))
				categorySettings.units = settings.value('units')
				categorySettings.fixedDistance = json.loads(settings.value('fixedDistance'))
				categorySettings.fixedCount = json.loads(settings.value('fixedCount'))
				categorySettings.userDefined = json.loads(settings.value('userDefined'))
				categorySettings.generateLinesInside = _bool(settings.value('generateLinesInside'))
				categorySettings.topPriorityLines = _bool(settings.value('topPriorityLines'))
				settings.endGroup()

			elif (re.compile("PORT").search(settingsGroup)):
				print("PORT item settings found.")
				settings.beginGroup(settingsGroup)
				categorySettings = PortSettingsItem()
				categorySettings.name = itemName
				categorySettings.type = settings.value('type')
				categorySettings.R = settings.value('R')
				categorySettings.RUnits = settings.value('RUnits')
				categorySettings.isActive = _bool(settings.value('isActive'))
				categorySettings.direction = settings.value('direction')

				if (categorySettings.type == "circular waveguide"):
					categorySettings.modeName = settings.value('modeName')
					categorySettings.polarizationAngle = settings.value('polarizationAngle')
					categorySettings.excitationAmplitude = settings.value('excitationAmplitude')
				elif (categorySettings.type == "nf2ff box"):
					#
					#	Add nf2ff box item into list of possible object in postprocessing tab
					#
					self.form.portNf2ffObjectList.addItem(categorySettings.name)


				settings.endGroup()

			elif (re.compile("MATERIAL").search(settingsGroup)):
				print("Material item settings found.")
				settings.beginGroup(settingsGroup)
				categorySettings = MaterialSettingsItem()
				categorySettings.name = itemName
				categorySettings.type = settings.value('type')
				categorySettings.constants = {}
				categorySettings.constants['epsilon'] = settings.value('material_epsilon')
				categorySettings.constants['mue'] = settings.value('material_mue')
				categorySettings.constants['kappa'] = settings.value('material_kappa')
				categorySettings.constants['sigma'] = settings.value('material_sigma')
				settings.endGroup()

			elif (re.compile("SIMULATION").search(settingsGroup)):
				print("Simulation params item settings found.")
				settings.beginGroup(settingsGroup)
				simulationSettings = SimulationSettingsItem()
				simulationSettings.name = itemName
				simulationSettings.type = settings.value('type')
				simulationSettings.params = json.loads(settings.value('params'))
				print('SIMULATION PARAMS:')
				print(simulationSettings.params)
				settings.endGroup()

				self.form.simParamsMaxTimesteps.setValue(simulationSettings.params['max_timestamps'])
				self.form.simParamsMinDecrement.setValue(simulationSettings.params['min_decrement'])
				self.form.generateJustPreviewCheckbox.setCheckState(
					QtCore.Qt.Checked if simulationSettings.params.get('generateJustPreview', False) else QtCore.Qt.Unchecked)
				self.form.generateDebugPECCheckbox.setCheckState(
					QtCore.Qt.Checked if simulationSettings.params.get('generateDebugPEC'   , False) else QtCore.Qt.Unchecked)
				self.form.octaveExecCommandList.setCurrentText(
					simulationSettings.params.get("mFileExecCommand", self.form.octaveExecCommandList.itemData(0)))
				self.form.simParamsDeltaUnitList.setCurrentText(
					simulationSettings.params.get("base_length_unit_m", self.form.simParamsDeltaUnitList.itemData(0))) 

				self.setSimlationParamBC(self.form.BCxmin, simulationSettings.params['BCxmin'])
				self.setSimlationParamBC(self.form.BCxmax, simulationSettings.params['BCxmax'])
				self.setSimlationParamBC(self.form.BCymin, simulationSettings.params['BCymin'])
				self.setSimlationParamBC(self.form.BCymax, simulationSettings.params['BCymax'])
				self.setSimlationParamBC(self.form.BCzmin, simulationSettings.params['BCzmin'])
				self.setSimlationParamBC(self.form.BCzmax, simulationSettings.params['BCzmax'])

				self.form.PMLxmincells.setValue(simulationSettings.params['PMLxmincells'])
				self.form.PMLxmaxcells.setValue(simulationSettings.params['PMLxmaxcells'])
				self.form.PMLymincells.setValue(simulationSettings.params['PMLymincells'])
				self.form.PMLymaxcells.setValue(simulationSettings.params['PMLymaxcells'])
				self.form.PMLzmincells.setValue(simulationSettings.params['PMLzmincells'])
				self.form.PMLzmaxcells.setValue(simulationSettings.params['PMLzmaxcells'])

				self.form.genParamMinGridSpacingX.setValue(simulationSettings.params['min_gridspacing_x'])
				self.form.genParamMinGridSpacingY.setValue(simulationSettings.params['min_gridspacing_y'])
				self.form.genParamMinGridSpacingZ.setValue(simulationSettings.params['min_gridspacing_z'])

				continue	#there is no tree widget to add item to

			elif (re.compile("_OBJECT").search(settingsGroup)):
				print("FreeCadObject item settings found.")
				settings.beginGroup(settingsGroup)
				objParent = settings.value('parent')
				objCategory = settings.value('category')
				objFreeCadId = settings.value('freeCadId')
				print("\t" + objParent)
				print("\t" + objCategory)
				settings.endGroup()

				#adding excitation also into OBJECT ASSIGNMENT WINDOW
				targetGroup = self.form.objectAssignmentRightTreeWidget.findItems(objCategory, QtCore.Qt.MatchExactly)
				print("\t" + str(targetGroup))
				for k in range(len(targetGroup)):					
					print("\t" + targetGroup[k].text(0))
					for m in range(targetGroup[k].childCount()):
						print("\t" + targetGroup[k].child(m).text(0))
						if (targetGroup[k].child(m).text(0) == objParent):
							settingsItem = FreeCADSettingsItem(itemName)

							#treeItem = QtGui.QTreeWidgetItem([itemName])
							treeItem = QtGui.QTreeWidgetItem()
							treeItem.setText(0, itemName)

							#set icon during load, if object is some solid object it has object icon, if it's sketch it will have wire/antenna or whatever indicates wire icon
							errorLoadByName = False
							try:
								freeCadObj = App.ActiveDocument.getObjectsByLabel(itemName)[0]
							except:
								#
								#	ERROR - need to be check if this is enough to auto-repair load errors
								#
								if len(objFreeCadId) > 0:
									freeCadObj = App.ActiveDocument.getObject(objFreeCadId)
									treeItem.setText(0, freeCadObj.Label)	#auto repair name, replace it with current name
									errorLoadByName = True

							#
							#	ERROR - here needs to be checked if freeCadObj was even found based on its Label if no try looking based on its ID from file,
							#	need to do this this way due backward compatibility
							#		- also FreeCAD should have set uniqe label for objects in Preferences
							#
							#set unique FreeCAD inside name as ID
							settingsItem.setFreeCadId(freeCadObj.Name)

							#SAVE settings object into GUI tree item
							treeItem.setData(0, QtCore.Qt.UserRole, settingsItem)

							if (freeCadObj.Name.find("Sketch") > -1):
								treeItem.setIcon(0, QtGui.QIcon("./img/wire.svg")) 
							elif (freeCadObj.Name.find("Discretized_Edge") > -1):
								treeItem.setIcon(0, QtGui.QIcon("./img/curve.svg")) 
							else:
								treeItem.setIcon(0, QtGui.QIcon("./img/object.svg"))

							#
							#	THERE IS MISMATCH BETWEEN NAME STORED IN IN FILE AND FREECAD NAME
							#
							if errorLoadByName:
								treeItem.setIcon(0, QtGui.QIcon("./img/errorLoadObject.svg"))

							targetGroup[k].child(m).addChild(treeItem)
							print("\tItem added")
							
				continue #items is already added into tree widget nothing more needed

			elif (re.compile("LUMPEDPART").search(settingsGroup)):
				print("LumpedPart item settings found.")
				settings.beginGroup(settingsGroup)
				categorySettings = LumpedPartSettingsItem()
				categorySettings.name = itemName
				categorySettings.params = json.loads(settings.value('params'))
				settings.endGroup()

			elif (re.compile("PRIORITYLIST-OBJECTS").search(settingsGroup)):
				print("PriorityList group settings found.")

				#start reading priority objects configuration in ini file
				settings.beginGroup(settingsGroup)

				#add each priority item from ini file into GUI tree widget
				topItemsList = [0 for i in range(len(settings.childKeys()))]
				print("Priority objects list array initialized with size " +  str(len(topItemsList)))
				for prioritySettingsKey in settings.childKeys():
					prioritySettingsOrder = int(settings.value(prioritySettingsKey))
					prioritySettingsType = prioritySettingsKey.split(", ")
					print("Priority list adding item " + prioritySettingsKey)

					#adding item into priority list
					topItem = QtGui.QTreeWidgetItem([prioritySettingsKey])
					topItem.setData(0, QtCore.Qt.UserRole, prioritySettingsType)
					topItem.setIcon(0, self.openEMSObj.getIconByCategory(prioritySettingsType))
					topItemsList[prioritySettingsOrder] = topItem

				self.form.objectAssignmentPriorityTreeView.insertTopLevelItems(0,topItemsList)

				settings.endGroup()
				continue

			elif (re.compile("PRIORITYLIST-MESH").search(settingsGroup)):
				print("PriorityList mesh group settings found.")

				#clear all items from mesh tree widget
				self.removeAllMeshPriorityItems()

				#start reading priority objects configuration in ini file
				settings.beginGroup(settingsGroup)

				#add each priority item from ini file into GUI tree widget
				topItemsList = [0 for i in range(len(settings.childKeys()))]
				print("Priority list array initialized with size " +  str(len(topItemsList)))
				for prioritySettingsKey in settings.childKeys():
					prioritySettingsOrder = int(settings.value(prioritySettingsKey))
					prioritySettingsType = prioritySettingsKey.split(", ")
					print("Priority list adding item " + prioritySettingsKey)

					#adding item into priority list
					topItem = QtGui.QTreeWidgetItem([prioritySettingsKey])
					topItem.setData(0, QtCore.Qt.UserRole, prioritySettingsType)
					topItem.setIcon(0, self.openEMSObj.getIconByCategory(prioritySettingsType))
					topItemsList[prioritySettingsOrder] = topItem

				self.form.meshPriorityTreeView.insertTopLevelItems(0,topItemsList)

				settings.endGroup()

				#
				# If grid settings is not set to be top priority lines, therefore it's disabled (because then it's not take into account when generate mesh lines and it's overlapping something)
				#
				self.updateMeshPriorityDisableItems()

				continue

			elif (re.compile("POSTPROCESSING").search(settingsGroup)):
				print("POSTPROCESSING item settings found.")
				settings.beginGroup(settingsGroup)
				#
				#	In case of error just continue and do nothing to correct values
				#
				try:
					index = self.form.portNf2ffObjectList.findText(settings.value("nf2ffObject"), QtCore.Qt.MatchFixedString)
					if index >= 0:
						 self.form.portNf2ffObjectList.setCurrentIndex(index)
						 
					self.form.portNf2ffFreq.setValue(settings.value("nf2ffFreq"))
					self.form.portNf2ffThetaStart.setValue(settings.value("nf2ffThetaStart"))
					self.form.portNf2ffThetaStop.setValue(settings.value("nf2ffThetaStop"))
					self.form.portNf2ffThetaStep.setValue(settings.value("nf2ffThetaStep"))
					self.form.portNf2ffPhiStart.setValue(settings.value("nf2ffPhiStart"))
					self.form.portNf2ffPhiStop.setValue(settings.value("nf2ffPhiStop"))
					self.form.portNf2ffPhiStep.setValue(settings.value("nf2ffPhiStep"))
				except:
					pass

				settings.endGroup()
				continue

			else:
				#if no item recognized then conitnue next run, at the end there is adding into object assignment tab
				#and if category is not known it's need to goes for another one
				continue

			# add all items
			self.addSettingsItemGui(categorySettings)
			# start with expanded treeWidget
			self.form.objectAssignmentRightTreeWidget.expandAll()

		self.guiHelpers.displayMessage("Settings loaded from file: " + outFile, forceModal=False)
		
		return

####################################################################################################################################################################
# End of PANEL definition
####################################################################################################################################################################
 
if __name__ == "__main__":
	panel = ExportOpenEMSDialog()
	panel.show()