import ctk
import logging
import os
import qt
import slicer
import unittest
import vtk
from slicer.ScriptedLoadableModule import *

################################################################################
#################  Textural Biomarkers of Arthritis ############################
################################################################################


class TexturalBiomarkersOfArthritis(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Textural Biomarkers Of Arthritis"
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
################  Textural Biomarkers of Arthritis Widget ######################
################################################################################


class TexturalBiomarkersOfArthritisWidget(ScriptedLoadableModuleWidget):

    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        print("-----  Textural Biomarkers of Arthritis widget setup -----")
        self.moduleName = 'TexturalBiomarkersOfArthritis'
        scriptedModulesPath = eval('slicer.modules.%s.path' % self.moduleName.lower())
        scriptedModulesPath = os.path.dirname(scriptedModulesPath)

        # - Initialisation of Textural Biomarkers of Arthritis and its logic - #

        self.logic = TexturalBiomarkersOfArthritisLogic()

        # -------------------------------------------------------------------- #
        # ----------------- Definition of the UI interface ------------------- #
        # -------------------------------------------------------------------- #

        # -------------------- Loading of the .ui file ----------------------- #

        loader = qt.QUiLoader()
        path = os.path.join(scriptedModulesPath, 'Resources', 'UI', '%s.ui' % self.moduleName)
        print(path)
        qfile = qt.QFile(path)
        qfile.open(qt.QFile.ReadOnly)
        widget = loader.load(qfile, self.parent)
        print widget
        self.layout = self.parent.layout()
        self.widget = widget
        self.layout.addWidget(widget)

        # ******************************************************************** #
        # ------------------------------ Algorithm --------------------------- #
        # ******************************************************************** #

    def cleanup(self):
        pass


################################################################################
#################  Textural Biomarkers Of Arthritis Logic ######################
################################################################################


class TexturalBiomarkersOfArthritisLogic(ScriptedLoadableModuleLogic):

    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def __init__(self):
        print "----- Textural Biomarkers of Arthritis logic init -----"

    # ************************************************************************ #
    # ------------------------------ Algorithm ------------------------------- #
    # ************************************************************************ #

################################################################################
#################  Textural Biomarkers Of Arthritis Test #######################
################################################################################


class TexturalBiomarkersOfArthritisTest(ScriptedLoadableModuleTest):
    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def setUp(self):
        print "----- Textural Biomarkers of Arthritis test setup -----"
        # reset the state - clear scene
        self.delayDisplay("Clear the scene")
        slicer.mrmlScene.Clear(0)

        # ******************************************************************** #
        # ---------- Testing of Textural Biomarkers Of Arthritis ------------- #
        # ******************************************************************** #

    def runTest(self):
        self.setUp()
        self.test_TexturalBiomarkersOfArthritis1()

    def test_TexturalBiomarkersOfArthritis1(self):
        self.delayDisplay("Starting the test")
