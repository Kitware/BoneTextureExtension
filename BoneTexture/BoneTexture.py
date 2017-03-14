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
        self.inputSegmentationMRMLNodeComboBox = self.logic.get("InputSegmentationMRMLNodeComboBox")
        self.inputScansPathLineEdit = self.logic.get("InputScansPathLineEdit")
        self.inputSegmentationsPathLineEdit = self.logic.get("InputSegmentationsPathLineEdit")


        # ---------------- Computation Collapsible Button -------------------- #

        self.computationCollapsibleButton = self.logic.get("ComputationCollapsibleButton")
        self.featureChoiceCollapsibleGroupBox = self.logic.get("FeatureChoiceCollapsibleGroupBox")
        self.gLCMFeaturesCheckableComboBox = self.logic.get("GLCMFeaturesCheckableComboBox")
        self.gLRLMFeaturesCheckableComboBox = self.logic.get("GLRLMFeaturesCheckableComboBox")
        self.computeFeaturesPushButton = self.logic.get("ComputeFeaturesPushButton")
        self.computeColormapsPushButton = self.logic.get("ComputeColormapsPushButton")
        self.advancedOptionsCollapsibleGroupBox = self.logic.get("AdvancedOptionsCollapsibleGroupBox")

        # ----------------- Results Collapsible Button ----------------------- #

        self.resultsCollapsibleButton = self.logic.get("ResultsCollapsibleButton")
        self.featuresTableCollapsibleGroupBox = self.logic.get("FeaturesTableCollapsibleGroupBox")
        self.featuresableWidget = self.logic.get("FeaturesableWidget")
        self.displayColormapsCollapsibleGroupBox = self.logic.get("DisplayColormapsCollapsibleGroupBox")
        self.displayColormapsMRMLTreeView = self.logic.get("DisplayColormapsMRMLTreeView")

        # ---------------- Exportation Collapsible Button -------------------- #

        self.exportationCollapsibleButton = self.logic.get("ExportationCollapsibleButton")
        self.outputPathLineEdit = self.logic.get("OutputPathLineEdit")
        self.saveFeaturesPushButton = self.logic.get("SaveFeaturesPushButton")
        self.saveColormapsPushButton = self.logic.get("SaveColormapsPushButton")


        # ******************************************************************** #
        # ----------------------- Algorithm ---------------------------------- #
        # ******************************************************************** #


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
        print "----- Bone Texture logic init -----"
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

################################################################################
###########################  Bone Texture Test #################################
################################################################################


class BoneTextureTest(ScriptedLoadableModuleTest):
    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def setUp(self):
        print "----- Bone Texture test setup -----"
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
