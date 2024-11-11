import logging
import os
from typing import Annotated, Optional
import csv
import os
import qt
import slicer
import vtk


from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
# Use segment statistics to compute good default parameters for texture modules.
import SegmentStatistics

import math  # for ceil
import VectorToScalarVolume # For extra widget, handling input vector/RGB images.

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLSegmentationNode, vtkMRMLVolumeNode


#
# Bone Texture
#


class BoneTexture(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Bone Texture"  
        self.parent.categories = ["Quantification"]
        self.parent.dependencies = []
        self.parent.contributors = ["Jean-Baptiste VIMORT (Kitware Inc.)"]
        self.parent.helpText = """
        This module is based on two texture analysis filters that are used to compute
        feature maps of N-Dimensional images using two well-known texture analysis methods.
        The two filters used in this module are itkCoocurrenceTextureFeaturesImageFilter
        (which computes textural features based on intensity-based co-occurrence matrices in
        the image) and itkRunLengthTextureFeaturesImageFilter (which computes textural
        features based on equally valued intensity clusters of different sizes or run lengths
        in the image). The output of this module is a vector image of the same size than the
        input that contains a multidimensional vector in each pixel/voxel. Filters can be configured
        based in the locality of the textural features (neighborhood size), offset directions
        for co-ocurrence and run length computation, the number of bins for the intensity
        histograms, the intensity range or the range of run lengths.
        """
        self.parent.acknowledgementText = """
        This work was supported by the National Institute of Health (NIH) National Institute for
        Dental and Craniofacial Research (NIDCR) R01EB021391 (Textural Biomarkers of Arthritis for
        the Subchondral Bone in the Temporomandibular Joint)
        """

class TableCopyFilter(qt.QWidget):
    def eventFilter(self, source, event):
        if event.type() == qt.QEvent.KeyPress and event.matches(qt.QKeySequence.Copy):
            self.copySelected(source)
            return True
        return False

    def copySelected(self, table):
        selection = table.selectedIndexes()

        if selection:
            rows = sorted(set(index.row() for index in selection))
            cols = sorted(set(index.column() for index in selection))

            # allow looking up index data by coordinate
            data = {(index.row(), index.column()): index.data() for index in selection}

            # fetch a full grid of rows x columns. missing (unselected) values are ''
            parts = [[data.get((row, col), '') for col in cols] for row in rows]

            # join table into tsv-formatted text
            text = '\n'.join('\t'.join(part) for part in parts)

            slicer.app.clipboard().setText(text)

#
# BoneTextureParameterNode
#


@parameterNodeWrapper
class BoneTextureParameterNode:
    pass


#
# BoneTextureWidget
#


class BoneTextureWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/BoneTexture.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = BoneTextureLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
        self.ui.InputScanComboBox.currentNodeChanged.connect(self.onInputScanChanged)
        self.ui.vectorToScalarVolumeMethodSelectorComboBox.currentIndexChanged.connect(self.updateVectorToScalarVolumeGUI)

        # Setup VectorToScalarConversion ComboBox
        self.setupVectorToScalarConversion()

        # Buttons
        
        # ----------- Compute Parameters Based on Inputs Button -------------- #
        self.ui.ComputeParametersBasedOnInputsButton.connect('clicked()', self.onComputeParametersBasedOnInputs)

        # ---------------- Computation Collapsible Button -------------------- #
        self.ui.ComputeFeaturesPushButton.connect('clicked()', self.onComputeFeatures)
        self.ui.ComputeColormapsPushButton.connect('clicked()', self.onComputeColormaps)

        # ----------------- Results Collapsible Button ----------------------- #

        self.featureSetMRMLNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.onFeatureSetChanged)
        self.featureComboBox.connect("currentIndexChanged(int)", self.onFeatureChanged)
        self.ui.SaveTablePushButton.connect('clicked()', self.onSaveTable)
        copy_filter = TableCopyFilter(self.displayFeaturesTableWidget)
        self.displayFeaturesTableWidget.installEventFilter(copy_filter)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())


    def setParameterNode(self, inputParameterNode: Optional[BoneTextureParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            # self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
          
    def setupVectorToScalarConversion(self):
        self.vectorToScalarVolumeConversionMethods = VectorToScalarVolume.ConversionMethods
        # Set up Method ComboBox options
        for i, method in enumerate(self.vectorToScalarVolumeConversionMethods):
            title, tooltip = method.value
            self.ui.vectorToScalarVolumeMethodSelectorComboBox.addItem(title, method)
            self.ui.vectorToScalarVolumeMethodSelectorComboBox.setItemData(i, tooltip, qt.Qt.ToolTipRole)
        self.ui.SingleComponentSpinBox.visible = False # Only display for single component conversion method

    def updateVectorToScalarVolumeGUI(self):
            """ When the conversion method is changed, display the component spinbox
            if the single component method is selected"""

            conversionMethod = self.ui.vectorToScalarVolumeMethodSelectorComboBox.currentData
            isMethodSingleComponent = conversionMethod is self.ui.vectorToScalarVolumeConversionMethods.SINGLE_COMPONENT
            self.ui.SingleComponentSpinBox.visible = isMethodSingleComponent

    def onInputScanChanged(self):
        """ Check if input is vector image, and allow conversion enabling VectorToScalarVolume widget """
        inputScan = self.ui.InputScanComboBox.currentNode()
        if inputScan is None:
            self.ui.vectorToScalarVolumeGroupBox.enabled = False
            return
        if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):
            self.ui.vectorToScalarVolumeGroupBox.enabled = True
        else:
            self.ui.vectorToScalarVolumeGroupBox.enabled = False

    def onVectorToScalarVolumePushButtonClicked(self):
        """
        Convert current input VectorVolume to a ScalarVolume.
        And set that ScalarVolume as the new input.
        """
        # create and add output node to scene (hide this selection from user)
        inputVolumeNode = self._parameterNode.inputVolume
        conversionMethod = self.vectorToScalarVolumeMethodSelectorComboBox.currentData

        inputName = inputVolumeNode.GetName()
        methodName = '_ToScalarMethod_'
        outputName = inputName + methodName + conversionMethod.value[0].replace(" ","")
        if conversionMethod == self.vectorToScalarVolumeConversionMethods.SINGLE_COMPONENT:
            componentToExtract = self.ui.SingleComponentSpinBox.value

            # SINGLE_COMPONENT: Check that input has enough components for the given componentToExtract
            inputImage = inputVolumeNode.GetImageData()
            numberOfComponents = inputImage.GetNumberOfScalarComponents()

            # componentToExtract is an index with valid values in the range: [0, numberOfComponents-1]
            if not 0 <= componentToExtract < numberOfComponents:
                msg = f"component to extract ({componentToExtract}) is invalid. Image has only {numberOfComponents} components."
                logging.debug("Vector to Scalar Conversion failed: %s" % msg)
                raise ValueError(msg)
            else:
                outputName += str(componentToExtract)
        else:
            componentToExtract = 0
        outputVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", slicer.mrmlScene.GetUniqueNameByString(outputName))
        
        # run conversion
        self.logic.convertInputVectorToScalarVolume(inputVolumeNode,
                                                              outputVolumeNode,
                                                              conversionMethod,
                                                              componentToExtract)

        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActiveVolumeID(outputVolumeNode.GetID())
        slicer.app.applicationLogic().PropagateVolumeSelection(0)

        # set the output as the new input for this module.
        self.inputScanMRMLNodeComboBox.setCurrentNode(outputVolumeNode)

    def onGLCMFeaturesValueDictModified(self, key, value):
        self.GLCMFeaturesValueDict[key] = value

    def onGLRLMFeaturesValueDictModified(self, key, value):
        self.GLRLMFeaturesValueDict[key] = value

    def onBMFeaturesValueDictModified(self, key, value):
        self.BMFeaturesValueDict[key] = value

        # ---------------- Computation Collapsible Button -------------------- #

    def onComputeParametersBasedOnInputs(self):
        inputScan = self._parameterNode.inputVolume
        inputSegmentation = self.inputSegmentationMRMLNodeComboBox.currentNode()
        isValid = self.logic.inputDataVerification(inputScan, inputSegmentation)
        if isValid is False:
            return

        minIntensityValue, maxIntensityValue = self.logic.computeLabelStatistics(inputScan, inputSegmentation)
        numBins = self.logic.computeBinsBasedOnIntensityRange(minIntensityValue, maxIntensityValue)

        self.GLCMnumberOfBinsSpinBox.value = numBins
        self.GLCMminVoxelIntensitySpinBox.value = minIntensityValue
        self.GLCMmaxVoxelIntensitySpinBox.value = maxIntensityValue
        self.GLRLMnumberOfBinsSpinBox.value = numBins
        self.GLRLMminVoxelIntensitySpinBox.value = minIntensityValue
        self.GLRLMmaxVoxelIntensitySpinBox.value = maxIntensityValue

    def onComputeFeatures(self):
        # This will run async, and populate self.logic.featuresXXX
        self.logic.computeFeatures(self._parameterNode.inputScan,
                                   self.inputSegmentationMRMLNodeComboBox.currentNode(),
                                   self.gLCMFeaturesCheckBox.isChecked(),
                                   self.gLRLMFeaturesCheckBox.isChecked(),
                                   self.bMFeaturesCheckBox.isChecked(),
                                   self.GLCMFeaturesValueDict,
                                   self.GLRLMFeaturesValueDict,
                                   self.BMFeaturesValueDict)

    def onDisplayFeatures(self):
        if self.logic.featuresGLCM is not None:
            for i in range(8):
                self.displayFeaturesTableWidget.item(i,1).setText(self.logic.featuresGLCM[i])

        if self.logic.featuresGLRLM is not None:
            for i in range(10):
                self.displayFeaturesTableWidget.item(i, 3).setText(self.logic.featuresGLRLM[i])

        if self.logic.featuresBM is not None:
            for i in range(5):
                self.displayFeaturesTableWidget.item(i, 5).setText(self.logic.featuresBM[i])

    def onComputeColormaps(self):
        self.logic.computeColormaps(self.inputScanMRMLNodeComboBox.currentNode(),
                                    self.inputSegmentationMRMLNodeComboBox.currentNode(),
                                    self.gLCMFeaturesCheckBox.isChecked(),
                                    self.gLRLMFeaturesCheckBox.isChecked(),
                                    self.bMFeaturesCheckBox.isChecked(),
                                    self.GLCMFeaturesValueDict,
                                    self.GLRLMFeaturesValueDict,
                                    self.BMFeaturesValueDict)

        # ----------------- Results Collapsible Button ----------------------- #

    def onFeatureSetChanged(self, node):

        self.featureComboBox.clear()

        if node is None:
            return

        # Set the festureSet displayed in Slicer to the selected module
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActiveVolumeID(node.GetID())
        mode = slicer.vtkMRMLApplicationLogic.BackgroundLayer
        applicationLogic = slicer.app.applicationLogic()
        applicationLogic.PropagateVolumeSelection(mode, 0)

        # Set the good feature names in the featureCombobox
        if node.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 8:
            self.featureComboBox.addItems(self.CFeatures)
        elif node.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 10:
            self.featureComboBox.addItems(self.RLFeatures)
        elif node.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 5:
            self.featureComboBox.addItems(self.BMFeatures)

    def onFeatureChanged(self, index):
        if self.featureSetMRMLNodeComboBox.currentNode():
            # Change the feature displayed to the one wanted by the user
            self.featureSetMRMLNodeComboBox.currentNode().GetDisplayNode().SetDiffusionComponent(index)

    def onSaveTable(self):
        self.logic.SaveTableAsCSV(self.displayFeaturesTableWidget,self.CSVPathLineEdit.currentPath)

    def cleanup(self):
        pass


#
# BoneTextureLogic
#


class BoneTextureLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return BoneTextureParameterNode(super().getParameterNode())

    def isClose(self, a, b, rel_tol=0.0, abs_tol=0.0):
        for i in range(len(a)):
            if not (abs(a[i] - b[i]) <= max(rel_tol * max(abs(a[i]), abs(b[i])), abs_tol)):
                return False
        return True

    def computeLabelStatistics(self, inputScan, inputLabelMapNode):
        """ Use slicer core module to get the min/max intensity value inside the mask.
        Returns tuple (min, max) with intensity values inside the mask. """
        # Export lapel map node into a segmentation node
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(inputLabelMapNode, segmentationNode)

        # Compute statistics (may take time)
        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
        segStatLogic.getParameterNode().SetParameter("ScalarVolume", inputScan.GetID())

        # Disable all plugins
        for plugin in segStatLogic.plugins:
          pluginName = plugin.__class__.__name__
          segStatLogic.getParameterNode().SetParameter(f"{pluginName}.enabled", str(False))

        # Explicitly enable ScalarVolumeSegmentStatistics
        segStatLogic.getParameterNode().SetParameter("ScalarVolumeSegmentStatisticsPlugin.enabled", str(True))
        segStatLogic.computeStatistics()
        stats = segStatLogic.getStatistics()

        # Remove temporary segmentation node
        slicer.mrmlScene.RemoveNode(segmentationNode)

        segmentId = stats["SegmentIDs"][0]
        minIntensityValue = stats[segmentId, "ScalarVolumeSegmentStatisticsPlugin.min"]
        maxIntensityValue = stats[segmentId, "ScalarVolumeSegmentStatisticsPlugin.max"]

        return minIntensityValue, maxIntensityValue

    def computeBinsBasedOnIntensityRange(self, minIntensityValue, maxIntensityValue):
        """ Compute number of bins based on the intensity range min/max.
        The formula is ad-hoc, and add 100 bins for each 1000 value difference between min and max.
        Example: min = -500,  max = 3000, numBins = 400
        The minimum number of bins is 100, indepedently of the input.
        Returns integer number of bins.
        """
        numBins = 100 * int(math.ceil(abs(maxIntensityValue - minIntensityValue)/1000.0))
        return numBins


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
        if not(inputScan):
            slicer.util.warningDisplay("Please specify an input scan")
            return False
        else:
            if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):
                slicer.util.warningDisplay("The input scan has a vector pixel type, please transform it to a scalar type first.")
                return False

        if inputScan and inputSegmentation:
            if inputScan.GetImageData().GetDimensions() != inputSegmentation.GetImageData().GetDimensions():
                slicer.util.warningDisplay("The input scan and the input segmentation must be the same size")
                return False
            if not self.isClose(inputScan.GetSpacing(), inputSegmentation.GetSpacing(), 0.0, 1e-04) or \
                    not self.isClose(inputScan.GetOrigin(), inputSegmentation.GetOrigin(), 0.0, 1e-04):
                slicer.util.warningDisplay("The input scan and the input segmentation must overlap: same origin, spacing and orientation")
                return False
        return True

    # ---------------- Convert Vector Input to Scalar ---------------------- #
    def convertInputVectorToScalarVolume(self, inputScan, outputScalarVolume, conversionMethod, componentToExtract):
        externalLogic = VectorToScalarVolume.VectorToScalarVolumeLogic()
        # externalLogic.run performs the validation of parameters.
        externalLogic.runWithVariables(inputScan, outputScalarVolume, conversionMethod, componentToExtract)

    # ---------------- Computation of the wanted features---------------------- #

    def computeFeatures(self,
                        inputScan,
                        inputSegmentation,
                        computeGLCMFeatures,
                        computeGLRLMFeatures,
                        computeBMFeatures,
                        GLCMFeaturesValueDict,
                        GLRLMFeaturesValueDict,
                        BMFeaturesValueDict):

        if not (self.inputDataVerification(inputScan, inputSegmentation)):
            return
        if not (computeGLCMFeatures or computeGLRLMFeatures or computeBMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return

        # Create the CLInodes, and observe them for async logic
        if computeGLCMFeatures:
            logging.info('Computing GLCM Features ...')
            _module = slicer.modules.computeglcmfeatures
            GLCMParameters = dict(GLCMFeaturesValueDict)
            GLCMParameters["inputVolume"] = inputScan
            GLCMParameters["inputMask"] = inputSegmentation
            GLCMNode = slicer.cli.createNode(_module, GLCMParameters)
            self.addObserver(GLCMNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onGLCMNodeModified)
            GLCMNode = slicer.cli.run(_module, node=GLCMNode, parameters=GLCMParameters, wait_for_completion=False)

        if computeGLRLMFeatures:
            logging.info('Computing GLRLM Features ...')
            _module = slicer.modules.computeglrlmfeatures
            GLRLMParameters = dict(GLRLMFeaturesValueDict)
            GLRLMParameters["inputVolume"] = inputScan
            GLRLMParameters["inputMask"] = inputSegmentation
            GLRLMNode = slicer.cli.createNode(_module, GLRLMParameters)
            self.addObserver(GLRLMNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onGLRLMNodeModified)
            # self.GLRLMNodeObserver = GLRLMNode.AddObserver(slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onGLRLMNodeModified)
            GLRLMNode = slicer.cli.run(_module, node=GLRLMNode, parameters=GLRLMParameters, wait_for_completion=False)

        if computeBMFeatures:
            logging.info('Computing BM Features ...')
            _module = slicer.modules.computebmfeatures
            BMParameters = dict(BMFeaturesValueDict)
            BMParameters["inputVolume"] = inputScan
            BMParameters["inputMask"] = inputSegmentation
            BMNode = slicer.cli.createNode(_module, BMParameters)
            self.addObserver(BMNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onBMNodeModified)
            BMNode = slicer.cli.run(_module, node=BMNode, parameters=BMParameters, wait_for_completion=False)

    def onGLCMNodeModified(self, cliNode, event):
        if not cliNode.IsBusy():
          self.removeObservers(self.onGLCMNodeModified)
          logging.info('GLCM status: %s' % cliNode.GetStatusString())
          if cliNode.GetStatusString() == 'Completed':
            self.featuresGLCM = list(map(float, cliNode.GetParameterValue(2, 0).split(",")))
            if self.interface is not None:
                self.interface.onDisplayFeatures()

    def onGLRLMNodeModified(self, cliNode, event):
        if not cliNode.IsBusy():
          self.removeObservers(self.onGLRLMNodeModified)
          logging.info('GLRLM status: %s' % cliNode.GetStatusString())
          if cliNode.GetStatusString() == 'Completed':
            self.featuresGLRLM = list(map(float, cliNode.GetParameterValue(2, 0).split(",")))
            if self.interface is not None:
                self.interface.onDisplayFeatures()

    def onBMNodeModified(self, cliNode, event):
        if not cliNode.IsBusy():
          self.removeObservers(self.onBMNodeModified)
          logging.info('BM status: %s' % cliNode.GetStatusString())
          if cliNode.GetStatusString() == 'Completed':
            self.featuresBM = list(map(float, cliNode.GetParameterValue(2, 0).split(",")))
            if self.interface is not None:
                self.interface.onDisplayFeatures()

    # def computeSingleFeatureSet(self,
    #                            inputScan,
    #                            inputSegmentation,
    #                            CLIname,
    #                            valueDict):
    #     parameters = dict(valueDict)
    #     parameters["inputVolume"] = inputScan
    #     parameters["inputMask"] = inputSegmentation
    #     CLI = slicer.cli.run(CLIname,
    #                          None,
    #                          parameters,
    #                          wait_for_completion=True)
    #     return list(map(float, CLI.GetParameterValue(2, 0).split(",")))

    # --------------- Computation of the wanted colormaps --------------------- #

    def computeColormaps(self,
                         inputScan,
                         inputSegmentation,
                         computeGLCMFeatures,
                         computeGLRLMFeatures,
                         computeBMFeatures,
                         GLCMFeaturesValueDict,
                         GLRLMFeaturesValueDict,
                         BMFeaturesValueDict):

        if not (self.inputDataVerification(inputScan, inputSegmentation)):
            return
        if not (computeGLCMFeatures or computeGLRLMFeatures or computeBMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return

        if computeGLCMFeatures:
            self.computeSingleColormap(inputScan,
                                       inputSegmentation,
                                       slicer.modules.computeglcmfeaturemaps,
                                       GLCMFeaturesValueDict,
                                       "GLCM_ColorMaps")

        if computeGLRLMFeatures:
            self.computeSingleColormap(inputScan,
                                       inputSegmentation,
                                       slicer.modules.computeglrlmfeaturemaps,
                                       GLRLMFeaturesValueDict,
                                       "GLRLM_ColorMaps")

        if computeBMFeatures:
            self.computeSingleColormap(inputScan,
                                       inputSegmentation,
                                       slicer.modules.computebmfeaturemaps,
                                       BMFeaturesValueDict,
                                       "BM_ColorMaps")

    def computeSingleColormap(self,
                              inputScan,
                              inputSegmentation,
                              CLIname,
                              valueDict,
                              outputName):
        parameters = dict(valueDict)
        parameters["inputVolume"] = inputScan
        parameters["inputMask"] = inputSegmentation
        volumeNode = slicer.vtkMRMLDiffusionWeightedVolumeNode()
        slicer.mrmlScene.AddNode(volumeNode)
        displayNode = slicer.vtkMRMLDiffusionWeightedVolumeDisplayNode()
        slicer.mrmlScene.AddNode(displayNode)
        colorNode = slicer.util.getNode('Rainbow')
        displayNode.SetAndObserveColorNodeID(colorNode.GetID())
        volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        volumeNode.SetName(outputName)
        parameters["outputVolume"] = volumeNode
        slicer.cli.run(CLIname,
                       None,
                       parameters,
                       wait_for_completion=False)

    def SaveTableAsCSV(self,
                       table,
                       fileName):
        if fileName is None:
            slicer.util.warningDisplay("Please specify an output file")
        if (not (fileName.endswith(".csv"))):
            slicer.util.warningDisplay("The output file must be a csv file")
        file = open(fileName, 'w')
        cw = csv.writer(file, delimiter=',')

        for j in range(6):
            row = []
            for i in range(10):
                if table.item(i, j):
                    row.append(table.item(i, j).text())
            cw.writerow(row)
        file.close()

#
# BoneTextureTest
#


class BoneTextureTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        logging.debug("----- Bone Texture test setup -----")
        # reset the state - clear scene
        self.delayDisplay("Clear the scene")
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_BoneTexture1()

    def test_BoneTexture1(self):
        self.delayDisplay("Starting the test")
