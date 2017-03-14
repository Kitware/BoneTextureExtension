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

        self.logic = BoneTextureLogic()

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

    def __init__(self):
        print "----- Bone Texture logic init -----"

    # ************************************************************************ #
    # ------------------------ Algorithm ------------------------------------- #
    # ************************************************************************ #

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
