import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging


#
# TexturalBiomarkersOfArthritis
#


class TexturalBiomarkersOfArthritis(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Textural Biomarkers Of Arthritis"
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["Jean-Baptiste VIMORT (Kitware Inc..)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    TODO
    """
    self.parent.acknowledgementText = """
    TODO
"""


#
# Textural Biomarkers of ArthritisWidget
#


class TexturalBiomarkersOfArthritisWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    print("-----  Textural Biomarkers of Arthritis widget setup -----")

    # Instantiate and connect widgets


  def cleanup(self):
    pass


#
# TexturalBiomarkersOfArthritisLogic
#


class TexturalBiomarkersOfArthritisLogic(ScriptedLoadableModuleLogic):
  def __init__(self):
    print "----- Textural Biomarkers of Arthritis logic init -----"


class TexturalBiomarkersOfArthritisTest(ScriptedLoadableModuleTest):

  def setUp(self):
    print "----- Textural Biomarkers of Arthritis test setup -----"
    # reset the state - clear scene
    self.delayDisplay("Clear the scene")
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    self.setUp()
    self.test_TexturalBiomarkersOfArthritis1()

  def test_TexturalBiomarkersOfArthritis1(self):
    self.delayDisplay("Starting the test")
