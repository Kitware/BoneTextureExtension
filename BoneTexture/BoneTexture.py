import ctk
import logging
import os
import qt
import math
import slicer
import unittest
import vtk
from slicer.ScriptedLoadableModule import *

################################################################################
############################  Bone Texture #####################################
################################################################################


class BoneTexture(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Bone Texture"
        self.parent.categories = ["Examples"]
        self.parent.dependencies = []
        self.parent.contributors = ["Jean-Baptiste VIMORT (Kitware Inc..)"]
        self.parent.helpText = """
    TODO
    """
        self.parent.acknowledgementText = """
    TODO
"""

################################################################################
##########################  Bone Texture Widget ################################
################################################################################


class BoneTextureWidget(ScriptedLoadableModuleWidget):

    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        print("-----  Bone Texture widget setup -----")
        self.moduleName = 'BoneTexture'
        scriptedModulesPath = eval('slicer.modules.%s.path' % self.moduleName.lower())
        scriptedModulesPath = os.path.dirname(scriptedModulesPath)

        # - Initialisation of Bone Texture and its logic - #

        self.logic = BoneTextureLogic(self)
        self.CFeatures = ["energy", "entropy",
                          "correlation", "inverseDifferenceMoment",
                          "inertia", "clusterShade",
                          "clusterProminence", "haralickCorrelation"]
        self.RLFeatures = ["shortRunEmphasis", "longRunEmphasis",
                           "greyLevelNonuniformity", "runLengthNonuniformity",
                           "lowGreyLevelRunEmphasis" , "highGreyLevelRunEmphasis" ,
                           "shortRunLowGreyLevelEmphasis", "shortRunHighGreyLevelEmphasis",
                           "longRunLowGreyLevelEmphasis", "longRunHighGreyLevelEmphasis"]

        # -------------------------------------------------------------------- #
        # ----------------- Definition of the UI interface ------------------- #
        # -------------------------------------------------------------------- #

        # -------------------- Loading of the .ui file ----------------------- #

        loader = qt.QUiLoader()
        path = os.path.join(scriptedModulesPath, 'Resources', 'UI', '%s.ui' % self.moduleName)
        qfile = qt.QFile(path)
        qfile.open(qt.QFile.ReadOnly)
        widget = loader.load(qfile, self.parent)
        self.layout = self.parent.layout()
        self.widget = widget
        self.layout.addWidget(widget)

        # ---------------- Input Data Collapsible Button --------------------- #

        self.inputDataCollapsibleButton = self.logic.get("InputDataCollapsibleButton")
        self.singleCaseRadioButton = self.logic.get("SingleCaseRadioButton")
        self.multiCaseRadioButton = self.logic.get("MultiCaseRadioButton")
        self.singleCaseGroupBox = self.logic.get("SingleCaseGroupBox")
        self.multiCaseGroupBox = self.logic.get("MultiCaseGroupBox")
        self.inputScanMRMLNodeComboBox = self.logic.get("InputScanMRMLNodeComboBox")
        self.inputScanMRMLNodeComboBox.setMRMLScene(slicer.mrmlScene)
        self.inputSegmentationMRMLNodeComboBox = self.logic.get("InputSegmentationMRMLNodeComboBox")
        self.inputSegmentationMRMLNodeComboBox.setMRMLScene(slicer.mrmlScene)
        self.inputScanDirectoryButton = self.logic.get("InputScanDirectoryButton")
        self.inputSegmentationDirectoryButton = self.logic.get("InputSegmentationsPathLineEdit")


        # ---------------- Computation Collapsible Button -------------------- #

        self.computationCollapsibleButton = self.logic.get("ComputationCollapsibleButton")
        self.featureChoiceCollapsibleGroupBox = self.logic.get("FeatureChoiceCollapsibleGroupBox")
        self.gLCMFeaturesCheckBox = self.logic.get("GLCMFeaturesCheckBox")
        self.gLRLMFeaturesCheckBox = self.logic.get("GLRLMFeaturesCheckBox")
        self.computeFeaturesPushButton = self.logic.get("ComputeFeaturesPushButton")
        self.computeColormapsPushButton = self.logic.get("ComputeColormapsPushButton")
        self.parametersCollapsibleGroupBox = self.logic.get("ParametersCollapsibleGroupBox")
        self.insideMaskValueSpinBox = self.logic.get("InsideMaskValueSpinBox")
        self.numberOfBinsSpinBox = self.logic.get("NumberOfBinsSpinBox")
        self.minVoxelIntensitySpinBox = self.logic.get("MinVoxelIntensitySpinBox")
        self.maxVoxelIntensitySpinBox = self.logic.get("MaxVoxelIntensitySpinBox")
        self.minDistanceSpinBox = self.logic.get("MinDistanceSpinBox")
        self.maxDistanceSpinBox = self.logic.get("MaxDistanceSpinBox")
        self.neighborhoodRadiusSpinBox = self.logic.get("NeighborhoodRadiusSpinBox")

        # ----------------- Results Collapsible Button ----------------------- #

        self.resultsCollapsibleButton = self.logic.get("ResultsCollapsibleButton")
        self.featureSetMRMLNodeComboBox = self.logic.get("featureSetMRMLNodeComboBox")
        self.featureSetMRMLNodeComboBox.setMRMLScene(slicer.mrmlScene)
        self.featureComboBox = self.logic.get("featureComboBox")
        self.featuresableWidget = self.logic.get("FeaturesableWidget")
        self.displayColormapsCollapsibleGroupBox = self.logic.get("DisplayColormapsCollapsibleGroupBox")
        self.displayColormapsMRMLTreeView = self.logic.get("DisplayColormapsMRMLTreeView")

        # ---------------- Exportation Collapsible Button -------------------- #

        self.exportationCollapsibleButton = self.logic.get("ExportationCollapsibleButton")
        self.outputPathLineEdit = self.logic.get("OutputPathLineEdit")
        self.saveFeaturesPushButton = self.logic.get("SaveFeaturesPushButton")
        self.saveColormapsPushButton = self.logic.get("SaveColormapsPushButton")

        # -------------------------------------------------------------------- #
        # ---------------------------- Connections --------------------------- #
        # -------------------------------------------------------------------- #

        # ---------------- Input Data Collapsible Button --------------------- #

        self.singleCaseRadioButton.connect('clicked()', self.onSingleCaseComputationSelected)
        self.multiCaseRadioButton.connect('clicked()', self.onMultiCaseComputationSelected)

        # ---------------- Computation Collapsible Button -------------------- #

        self.computeFeaturesPushButton.connect('clicked()', self.onComputeFeatures)
        self.computeColormapsPushButton.connect('clicked()', self.onComputeColormaps)

        # ----------------- Results Collapsible Button ----------------------- #

        self.featureSetMRMLNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.onFeatureSetChanged)
        self.featureComboBox.connect("currentIndexChanged(int)", self.onFeatureChanged)

        # ---------------- Exportation Collapsible Button -------------------- #

        # -------------------------------------------------------------------- #
        # -------------------------- Initialisation -------------------------- #
        # -------------------------------------------------------------------- #

        self.onSingleCaseComputationSelected()

        # ******************************************************************** #
        # ----------------------- Algorithm ---------------------------------- #
        # ******************************************************************** #

        # ---------------- Input Data Collapsible Button --------------------- #

    def onSingleCaseComputationSelected(self):
        self.singleCaseGroupBox.show()
        self.multiCaseGroupBox.hide()

    def onMultiCaseComputationSelected(self):
        self.multiCaseGroupBox.show()
        self.singleCaseGroupBox.hide()

        # ---------------- Computation Collapsible Button -------------------- #

    def onComputeFeatures(self):
        self.logic.computeFeatures(self.inputScanMRMLNodeComboBox.currentNode(),
                                   self.inputSegmentationMRMLNodeComboBox.currentNode())

    def onComputeColormaps(self):
        self.logic.computeColormaps(self.inputScanMRMLNodeComboBox.currentNode(),
                                    self.inputSegmentationMRMLNodeComboBox.currentNode(),
                                    self.gLCMFeaturesCheckBox.isChecked(),
                                    self.gLRLMFeaturesCheckBox.isChecked(),
                                    self.insideMaskValueSpinBox.value,
                                    self.numberOfBinsSpinBox.value,
                                    self.minVoxelIntensitySpinBox.value,
                                    self.maxVoxelIntensitySpinBox.value,
                                    self.minDistanceSpinBox.value,
                                    self.maxDistanceSpinBox.value,
                                    self.neighborhoodRadiusSpinBox.value)

        # ----------------- Results Collapsible Button ----------------------- #

        # ---------------- Exportation Collapsible Button -------------------- #

    def onFeatureSetChanged(self, node):

        self.featureComboBox.clear()

        if node is None:
            return

        #Set the festureSet displayed in Slicer to the selected module
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActiveVolumeID(node.GetID())
        mode = slicer.vtkMRMLApplicationLogic.BackgroundLayer
        applicationLogic = slicer.app.applicationLogic()
        applicationLogic.PropagateVolumeSelection(mode, 0)

        #Set the good feature names in the featureCombobox
        if node.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 8:
            self.featureComboBox.addItems(self.CFeatures)
        else:
            self.featureComboBox.addItems(self.RLFeatures)

    def onFeatureChanged(self, index):
        #Change the feature displayed to the one wanted by the user
        self.featureSetMRMLNodeComboBox.currentNode().GetDisplayNode().SetDiffusionComponent(index)

    def cleanup(self):
        pass


################################################################################
############################  Bone Texture Logic ###############################
################################################################################


class BoneTextureLogic(ScriptedLoadableModuleLogic):

    # ************************************************************************ #
    # ----------------------- Initialisation --------------------------------- #
    # ************************************************************************ #

    def __init__(self, interface):
        print("----- Bone Texture logic init -----")
        self.interface = interface

    # ************************************************************************ #
    # ------------------------ Algorithm ------------------------------------- #
    # ************************************************************************ #

    # ----------- Useful functions to access the .ui file elements ----------- #

    def get(self, objectName):
        return self.findWidget(self.interface.widget, objectName)

    def findWidget(self, widget, objectName):
        if widget.objectName == objectName:
            return widget
        else:
            for w in widget.children():
                resulting_widget = self.findWidget(w, objectName)
                if resulting_widget:
                    return resulting_widget
            return None

    # ------- Test to ensure that the input data exist and are conform ------- #

    def inputDataVerification(self, inputScan, inputSegmentation):
        if not(inputScan and inputSegmentation):
            return False
        else:
            return True

    # ---------------- Computation of the wanted features---------------------- #



    # --------------- Computation of the wanted colormaps --------------------- #

    def computeColormaps(self, inputScan,
                               inputSegmentation,
                               computeGLCMFeatures,
                               computeGLRLMFeatures,
                               insideMaskValue,
                               numberOfBins,
                               minVoxelIntensity,
                               maxVoxelIntensity,
                               minDistance,
                               maxDistance,
                               neighborhoodRadius):

        if not (computeGLCMFeatures or computeGLRLMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return
        if not (self.inputDataVerification(inputScan, inputSegmentation)):
            slicer.util.warningDisplay("Please specify an input scan and an input segmentation")
            return
        parameters = {}
        parameters["inputVolume"] = inputScan
        parameters["inputMask"] = inputSegmentation
        parameters["insideMask"] = insideMaskValue
        parameters["binNumber"] = numberOfBins
        parameters["pixelIntensityMin"] = minVoxelIntensity
        parameters["pixelIntensityMax"] = maxVoxelIntensity
        parameters["neighborhoodRadius"] = neighborhoodRadius
        if computeGLCMFeatures:
            volumeNode = slicer.vtkMRMLDiffusionWeightedVolumeNode()
            slicer.mrmlScene.AddNode(volumeNode)
            displayNode = slicer.vtkMRMLDiffusionWeightedVolumeDisplayNode()
            slicer.mrmlScene.AddNode(displayNode)
            colorNode = slicer.util.getNode('Rainbow')
            displayNode.SetAndObserveColorNodeID(colorNode.GetID())
            volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
            volumeNode.SetName("GLCM_ColorMaps")
            parameters["outputVolume"] = volumeNode
            slicer.cli.run(slicer.modules.computeglcmfeatures,
                           None,
                           parameters,
                           wait_for_completion=False)

        parameters["distanceMin"] = minDistance
        parameters["distanceMax"] = maxDistance
        if computeGLRLMFeatures:
            volumeNode = slicer.vtkMRMLDiffusionWeightedVolumeNode()
            slicer.mrmlScene.AddNode(volumeNode)
            displayNode = slicer.vtkMRMLDiffusionWeightedVolumeDisplayNode()
            slicer.mrmlScene.AddNode(displayNode)
            colorNode = slicer.util.getNode('Rainbow')
            displayNode.SetAndObserveColorNodeID(colorNode.GetID())
            volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
            volumeNode.SetName("GLRLM_ColorMaps")
            parameters["outputVolume"] = volumeNode
            slicer.cli.run(slicer.modules.computeglrlmfeatures,
                           None,
                           parameters,
                           wait_for_completion=False)

################################################################################
###########################  Bone Texture Test #################################
################################################################################


class BoneTextureTest(ScriptedLoadableModuleTest):
    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def setUp(self):
        print("----- Bone Texture test setup -----")
        # reset the state - clear scene
        self.delayDisplay("Clear the scene")
        slicer.mrmlScene.Clear(0)

        # ******************************************************************** #
        # -------------------- Testing of Bone Texture ----------------------- #
        # ******************************************************************** #

    def runTest(self):
        self.setUp()
        self.test_BoneTexture1()

    def test_BoneTexture1(self):
        self.delayDisplay("Starting the test")
