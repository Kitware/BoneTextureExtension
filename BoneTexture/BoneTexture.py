import logging
import os
from typing import Optional, List, Tuple
import csv
import qt
import slicer
import vtk
import glob
from pathlib import Path

from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
    parameterPack
)
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
# Use segment statistics to compute good default parameters for texture modules.
import SegmentStatistics

import math  # for ceil
import VectorToScalarVolume # For extra widget, handling input vector/RGB images.

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLLabelMapVolumeNode, vtkMRMLDiffusionWeightedVolumeNode



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

@parameterPack
class GLCMFeaturesParameterNode:
    insideMask: int = 1
    binNumber: int = 10
    pixelIntensityMin : int = 0
    pixelIntensityMax : int = 4000
    neighborhoodRadius : int = 4

@parameterPack
class GLRLMFeaturesParameterNode:
    insideMask: int = 1
    binNumber: int = 10
    pixelIntensityMin : int = 0
    pixelIntensityMax : int = 4000
    neighborhoodRadius : int = 4
    distanceMin : float = 0
    distanceMax : float = 1

@parameterPack
class BMFeaturesParameterNode:
    threshold : int = 1
    neighborhoodRadius : int = 4

@parameterNodeWrapper
class BoneTextureParameterNode:
    inputVolume: vtkMRMLScalarVolumeNode
    inputLabelMap: vtkMRMLLabelMapVolumeNode
    GLCMFeaturesValue : GLCMFeaturesParameterNode
    GLRLMFeaturesValue : GLRLMFeaturesParameterNode
    BMFeaturesValue : BMFeaturesParameterNode

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

        # Convert to parameter Node
        self.computedFeatures = {'GLCMFeatures':None,
                                 'GLRLMFeatures': None,
                                 'BMFeatures': None
                            }
        
        self.serializerModeActive = False
        self.serializer_input_data = None
        self.use_image_mask = False
        self.output_csv = None

        self.CFeatures = ["Energy", "Entropy",
                          "Correlation", "Inverse Difference Moment",
                          "Inertia", "Cluster Shade",
                          "Cluster Prominence", "Haralick Correlation"]
        self.RLFeatures = ["Short Run Emphasis", "Long Run Emphasis",
                           "Grey Level Nonuniformity", "Run Length Non-uniformity",
                           "Low Grey Level Run Emphasis", "High Grey Level Run Emphasis",
                           "Short Run Low Grey Level Emphasis", "Short Run High Grey Level Emphasis",
                           "Long Run Low Grey Level Emphasis", "Long Run High Grey Level Emphasis"]
        self.BMFeatures = ["Bone volume density", "Trabecular thickness", 
                        "Trabecular separation", "Trabecular number",
                        "Bone surface density"]

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

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self.setMaskRelatedOptions(False)

        # Single vs. Serializer Mode
        self.ui.singleImagePushButton.clicked.connect(self.activateSingleImageMode)
        self.ui.serializerPushButton.clicked.connect(self.activateSeralizerMode)
        self.activateSingleImageMode()
        self.ui.SerializerConvertToScalarCheckBox.stateChanged.connect(self.enableVectorToScalarComboBox)
        self.ui.saveAsCSVCheckBox.stateChanged.connect(self.ui.writeCSVHeaderCheckBox.setEnabled)

        self.ui.defineMaskCheckBox.stateChanged.connect(self.defineMaskCheckStateChanged)
        self.ui.vectorToScalarVolumeMethodSelectorComboBox.currentIndexChanged.connect(self.updateVectorToScalarVolumeGUI)

        # Setup VectorToScalarConversion ComboBox
        self.setupVectorToScalarConversion()

        # Buttons
        self.ui.vectorToScalarVolumePushButton.clicked.connect(self.onVectorToScalarVolumePushButtonClicked)
        self.ui.processInputsPushButton.clicked.connect(self.getInputsFromDirectory)

        # ----------- Compute Parameters Based on Inputs Button -------------- #
        self.ui.ComputeParametersBasedOnInputsButton.clicked.connect(self.onComputeParametersBasedOnInputs)

        # ---------------- Computation Collapsible Button -------------------- #
        self.ui.ComputeFeaturesPushButton.clicked.connect(self.onComputeFeatures)
        self.ui.ComputeColormapsPushButton.clicked.connect(self.onComputeTextureMaps)
        self.ui.ComputeTextureMapsProgressBar.visible = False
        self.ui.ComputeFeaturesProgressBar.visible = False

        # ----------------- Results Collapsible Button ----------------------- #

        self.ui.featureSetComboBox.currentIndexChanged.connect(self.onFeatureSetChanged)
        self.ui.featureComboBox.currentIndexChanged.connect(self.onFeatureChanged)
        self.ui.SaveTablePushButton.connect('clicked()', self.onSaveTable)
        copy_filter = TableCopyFilter(self.ui.displayFeaturesTableWidget)
        self.ui.displayFeaturesTableWidget.installEventFilter(copy_filter)

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
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.onInputScanChanged)

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
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.onInputScanChanged)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.onInputScanChanged)
            self.onInputScanChanged()
          
    def setButtonColorSingleOrSerializerMode(self, isSerializerMode = False):
        if isSerializerMode:
            self.ui.singleImagePushButton.setStyleSheet('')
            self.ui.serializerPushButton.setStyleSheet("background-color : rgb(169, 169, 169)")
        else:
            self.ui.singleImagePushButton.setStyleSheet("background-color : rgb(169, 169, 169)")
            self.ui.serializerPushButton.setStyleSheet('')

    def activateSingleImageMode(self,):
        self.serializerModeActive = False
        self.ui.inputDataStackedWidget.setCurrentIndex(0)
        self.setButtonColorSingleOrSerializerMode(isSerializerMode = self.serializerModeActive)
        self.ui.ExportCollapsibleButton.hide()
        self.ui.ResultsCollapsibleButton.show()
        self.ui.inputsDisplayMessage.hide()
        self.ui.processInputsPushButton.hide()

        # Convert vector to scalar options
        self.ui.vectorToScalarVolumePushButton.show()
        self.ui.SerializerConvertToScalarCheckBox.hide()
        self.onInputScanChanged()
    
    def activateSeralizerMode(self):
        self.serializerModeActive = True
        self.ui.inputDataStackedWidget.setCurrentIndex(1)
        self.setButtonColorSingleOrSerializerMode(isSerializerMode = self.serializerModeActive)
        self.ui.ExportCollapsibleButton.show()
        self.ui.ResultsCollapsibleButton.hide()
        self.ui.ComputeParametersBasedOnInputsButton.hide()
        self.ui.inputsDisplayMessage.show()
        self.ui.processInputsPushButton.show()
        self.setMaskRelatedOptions(True)

        # Convert vector to scalar options
        self.ui.vectorToScalarVolumePushButton.hide()
        self.ui.SerializerConvertToScalarCheckBox.show()
        # self.ui.vectorToScalarVolumeGroupBox.enabled = True
        self.enableVectorToScalarComboBox()

    def setMaskRelatedOptions(self, bool = False):

        if not self.serializerModeActive:
            self.ui.InputSegmentationComboBox.enabled = bool
            self.ui.InputSegmentationLabel.enabled = bool

        self.ui.GLCMInsideMaskValueSpinBox.enabled = bool
        self.ui.GLCMMaskInsideValueLabel.enabled = bool
        self.ui.GLRLMInsideMaskValueSpinBox.enabled = bool
        self.ui.GLRLMMaskInsideValueLabel.enabled = bool

    def defineMaskCheckStateChanged(self):
        self.use_image_mask = self.ui.defineMaskCheckBox.isChecked()
        self.setMaskRelatedOptions(self.use_image_mask)

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
            isMethodSingleComponent = conversionMethod is self.vectorToScalarVolumeConversionMethods.SINGLE_COMPONENT
            self.ui.SingleComponentSpinBox.visible = isMethodSingleComponent

    def enableVectorToScalarComboBox(self, status = True):

        if self.serializerModeActive:
            self.ui.vectorToScalarVolumeGroupBox.enabled = True
            self.ui.vectorToScalarVolumeMethodSelectorComboBox.enabled = self.ui.SerializerConvertToScalarCheckBox.isChecked()
        else:
            self.ui.vectorToScalarVolumeGroupBox.enabled = status
            self.ui.vectorToScalarVolumeMethodSelectorComboBox.enabled = status

    def onInputScanChanged(self, caller = None, event = None) -> None:
        """ Check if input is vector image, and allow conversion enabling VectorToScalarVolume widget """
        if not self._parameterNode.inputVolume:
            self.ui.vectorToScalarVolumeGroupBox.enabled = False
            return
        
        inputScan = self._parameterNode.inputVolume

        if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):
            self.enableVectorToScalarComboBox(True)
        else:
            self.enableVectorToScalarComboBox(False)

    def onVectorToScalarVolumePushButtonClicked(self):
        """
        Convert current input VectorVolume to a ScalarVolume.
        And set that ScalarVolume as the new input.
        """
        # create and add output node to scene (hide this selection from user)
        inputVolumeNode = self._parameterNode.inputVolume
        conversionMethod = self.ui.vectorToScalarVolumeMethodSelectorComboBox.currentData

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

        slicer.util.setSliceViewerLayers(background = outputVolumeNode.GetID() )

        # set the output as the new input for this module.
        self.ui.InputScanComboBox.setCurrentNode(outputVolumeNode)

    def onGLCMFeaturesValueDictModified(self, key, value):
        self.GLCMFeaturesValueDict[key] = value

    def onGLRLMFeaturesValueDictModified(self, key, value):
        self.GLRLMFeaturesValueDict[key] = value

    def onBMFeaturesValueDictModified(self, key, value):
        self.BMFeaturesValueDict[key] = value

        # ---------------- Computation Collapsible Button -------------------- #

    def getAlgorithmInputs(self) -> List[Tuple[vtkMRMLScalarVolumeNode, vtkMRMLLabelMapVolumeNode]]:
        
        if self.serializerModeActive:
            if self.serializer_input_data:
                inputData = self.serializer_input_data
            else:
                slicer.util.errorDisplay('Input data needs to be processed first.')
                inputData = None
        else:
            if self.use_image_mask:
                inputData =  [(self._parameterNode.inputVolume, self._parameterNode.inputLabelMap)]
            else:
                inputData =  [(self._parameterNode.inputVolume, None)]
        
        return inputData
    
    def getInputsFromDirectory(self):
        """ The input data should be named in the folowing way: Scan_"ID".nrrd (for the input scan) 
        and Seg_"ID".nrrd (for the segmentation if it exist)
        """

        inputDir = self.ui.InputFolderDirectoryPathLineEdit.currentPath
        if not inputDir:
            slicer.util.errorDisplay("Please specify an input directory")
            return
        input_scans = glob.glob(inputDir + '/Scan_*.*')
        if not input_scans:
            slicer.util.errorDisplay("No cases were found in the selected input directory %s. "
                                        "Please check the required file naming convetion." % inputDir)
        
        display_message = ""
        display_message += f"{len(input_scans)} input scan(s) were found. "
        input_data = []
        mask_count = 0
        for file in input_scans:
            filename = Path(file).stem
            case_id = filename.split('Scan_')[1]
            
            #find seg file
            seg_file = glob.glob(inputDir + f'/Seg_{case_id}.*')
            if not seg_file:
                input_data.append((file, None))
            else:
                input_data.append((file, seg_file[0]))
                mask_count += 1
        
            inputScan = slicer.util.loadNodeFromFile(file,
                        'VolumeFile',
                        {'labelmap': False, 'show': False})

            if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):

                # Check for vector to scalar conversion
                if not self.ui.SerializerConvertToScalarCheckBox.isChecked():
                    slicer.util.warningDisplay("Detected an input scan that has a vector pixel type. Please enable the vector to scalar conversion option and select a method to transform the image to a scalar type first.")
                    return

        display_message += f"Corresponding segmentation masks were found for {mask_count}/{len(input_scans)} scans."

        self.serializer_input_data = input_data
        self.ui.inputsDisplayMessage.setText(display_message)

    def onComputeParametersBasedOnInputs(self):
        """ Populate the input parameters for computing the textue features 
        based on the image data. This option is only available in single image mode."""

        inputData = self.getAlgorithmInputs()
        for input in inputData:
            inputScan, inputSegmentation = input
            isValid = self.logic.inputDataVerification(inputScan, inputSegmentation)
            if not isValid:
                return

        if self.use_image_mask:
            minIntensityValue, maxIntensityValue = self.logic.computeLabelStatistics(inputScan, inputSegmentation)
        else:
            imageArray = slicer.util.arrayFromVolume(inputScan)
            minIntensityValue = imageArray.min()
            maxIntensityValue = imageArray.max()

        numBins = self.logic.computeBinsBasedOnIntensityRange(minIntensityValue, maxIntensityValue)

        self._parameterNode.GLCMFeaturesValue.binNumber = numBins
        self.ui.GLCMMinVoxelIntensitySpinBox.value = minIntensityValue
        self.ui.GLCMMaxVoxelIntensitySpinBox.value = maxIntensityValue
        self.ui.GLRLMNumberOfBinsSpinBox.value = numBins
        self.ui.GLRLMMinVoxelIntensitySpinBox.value = minIntensityValue
        self.ui.GLRLMMaxVoxelIntensitySpinBox.value = maxIntensityValue

    def SerializerModeVectorToScalarConversion(self, inputScan):

        conversionMethod = self.ui.vectorToScalarVolumeMethodSelectorComboBox.currentData
        if conversionMethod == self.vectorToScalarVolumeConversionMethods.SINGLE_COMPONENT:
            componentToExtract = self.ui.SingleComponentSpinBox.value

            # SINGLE_COMPONENT: Check that input has enough components for the given componentToExtract
            inputImage = inputScan.GetImageData()
            numberOfComponents = inputImage.GetNumberOfScalarComponents()

            # componentToExtract is an index with valid values in the range: [0, numberOfComponents-1]
            if not 0 <= componentToExtract < numberOfComponents:
                msg = f"Component to extract ({componentToExtract}) is invalid. Image has only {numberOfComponents} components."
                logging.debug("Vector to Scalar Conversion failed: %s" % msg)
                raise ValueError(msg)
        else:
            componentToExtract = 0

        outputVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", slicer.mrmlScene.GetUniqueNameByString(f"ConvertScan"))
        
        # run Conversion
        self.logic.convertInputVectorToScalarVolume(
            inputScan,
            outputVolumeNode,
            conversionMethod,
            componentToExtract)
    
        return outputVolumeNode

    def onComputeFeatures(self):

        if not (self.ui.GLCMFeaturesCheckBox.isChecked() or self.ui.GLRLMFeaturesCheckBox.isChecked() or self.ui.BMFeaturesCheckBox.isChecked()):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return

        inputData = self.getAlgorithmInputs()
            
        if not inputData:
            return
        
        if self.serializerModeActive:
            self.ComputeFeaturesSerializerMode(inputData)
        else:
            self.ComputeFeaturesSingleMode(inputData)

    def ComputeFeaturesSingleMode(self, inputData: List[Tuple[vtkMRMLScalarVolumeNode, vtkMRMLLabelMapVolumeNode]]):

        for input in inputData:

            inputScan, inputLabelMap = input

            isValid = self.logic.inputDataVerification(inputScan, inputLabelMap)
            if not isValid:
                return

            # This will run async, and populate self.logic.computedFeatures
            if self.ui.GLCMFeaturesCheckBox.isChecked():
                parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLCMFeaturesValue)
                GLCMFeaturesNode = self.logic.computeSingleFeature(slicer.modules.computeglcmfeatures,
                                        inputScan,
                                        parameters,
                                        "GLCMFeatures", inputLabelMap)
                self.addObserver(GLCMFeaturesNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onFeatureSetNodeModified)

            if self.ui.GLRLMFeaturesCheckBox.isChecked():
                parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLRLMFeaturesValue)
                GLRLMFeaturesNode = self.logic.computeSingleFeature(slicer.modules.computeglrlmfeatures,
                                        inputScan, 
                                        parameters,
                                        "GLRLMFeatures", inputLabelMap)
                self.addObserver(GLRLMFeaturesNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onFeatureSetNodeModified)

            if self.ui.BMFeaturesCheckBox.isChecked():
                parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().BMFeaturesValue)
                BMFeaturesNode = self.logic.computeSingleFeature(slicer.modules.computebmfeatures,
                                        inputScan,
                                        parameters,
                                        "BMFeatures", inputLabelMap)
                self.addObserver(BMFeaturesNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onFeatureSetNodeModified)

        self.ui.ResultsCollapsibleButton.collapsed = False
        self.ui.CollapsibleGroupBox.collapsed = False
  
    def ComputeFeaturesSerializerMode(self, inputData: List[Tuple[vtkMRMLScalarVolumeNode, vtkMRMLLabelMapVolumeNode]]):

        if not self.ui.OutputFolderDirectoryPathLineEdit.currentPath:
            slicer.util.errorDisplay("Please specify an output directory for saving results")
            return

        output_csv = Path(self.ui.OutputFolderDirectoryPathLineEdit.currentPath)/"TextureFeaturesTable.csv"
        

        stepsPerCase = sum((
            self.ui.GLCMFeaturesCheckBox.isChecked(),
            self.ui.GLRLMFeaturesCheckBox.isChecked(),
            self.ui.BMFeaturesCheckBox.isChecked(),
        ))

        self.ui.ComputeFeaturesProgressBar.value = 0
        self.ui.ComputeFeaturesProgressBar.minimum = 0 
        self.ui.ComputeFeaturesProgressBar.maximum = len(inputData) * stepsPerCase
        self.ui.ComputeFeaturesProgressBar.visible = True

        with open(output_csv, "w+") as file:
            print(file)
            cw = csv.writer(file, delimiter=',')

            # Write header information
            toWrite = ["Case ID"]
            if self.ui.GLCMFeaturesCheckBox.isChecked():
                toWrite += self.CFeatures
            if self.ui.GLRLMFeaturesCheckBox.isChecked():
                toWrite += self.RLFeatures
            if self.ui.BMFeaturesCheckBox.isChecked():
                toWrite += self.BMFeatures
            cw.writerow(toWrite)

            for input in inputData:

                inputScan, inputLabelMap = input
                case_id = self.getCaseID(inputScan)

                # Load in the input files
                inputScan = slicer.util.loadNodeFromFile(inputScan,
                    'VolumeFile',
                    {'labelmap': False, 'show': False}
                )
                if inputLabelMap:
                    inputLabelMap = slicer.util.loadNodeFromFile(inputLabelMap,
                        'VolumeFile',
                        {'labelmap': True, 'show': False}
                    )

                #If the scan is a vector image, convert to scalar
                if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):
                    if not self.ui.SerializerConvertToScalarCheckBox.isChecked():
                        slicer.util.warningDisplay("Detected an input scan that has a vector pixel type. Skipping texture map computation.")
                        continue
                    else:
                        inputScan = self.SerializerModeVectorToScalarConversion(inputScan)

                isValid = self.logic.inputDataVerification(inputScan, inputLabelMap)
                if not isValid:
                    self.ui.ComputeFeaturesProgressBar.visible = False
                    return

                # This will run async, and populate self.logic.computedFeatures
                if self.ui.GLCMFeaturesCheckBox.isChecked():
                    parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLCMFeaturesValue)
                    GLCMFeaturesNode = self.logic.computeSingleFeature(slicer.modules.computeglcmfeatures,
                                            inputScan,
                                            parameters,
                                            "GLCMFeatures", inputLabelMap, wait_for_completion= True)
                    self.ui.ComputeFeaturesProgressBar.value += 1
                    GLCMfeatures = [float(value) if value.replace('.','',1).isnumeric() else 'NaN' for value in GLCMFeaturesNode.GetParameterValue(2, 0).split(",")]                       

                if self.ui.GLRLMFeaturesCheckBox.isChecked():
                    parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLRLMFeaturesValue)
                    GLRLMFeaturesNode = self.logic.computeSingleFeature(slicer.modules.computeglrlmfeatures,
                                            inputScan, 
                                            parameters,
                                            "GLRLMFeatures", inputLabelMap, wait_for_completion=True)
                    self.GLRLMnode = GLRLMFeaturesNode
                    self.ui.ComputeFeaturesProgressBar.value += 1
                    GLRLMfeatures = [float(value) if value.replace('.','',1).isnumeric() else 'NaN' for value in GLRLMFeaturesNode.GetParameterValue(2, 0).split(",")]   
      
                if self.ui.BMFeaturesCheckBox.isChecked():
                    parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().BMFeaturesValue)
                    BMFeaturesNode = self.logic.computeSingleFeature(slicer.modules.computebmfeatures,
                                            inputScan,
                                            parameters,
                                            "BMFeatures", inputLabelMap, wait_for_completion=True)
                    self.ui.ComputeFeaturesProgressBar.value += 1
                    BMfeatures = [float(value) if value.replace('.','',1).isnumeric() else 'NaN' for value in BMFeaturesNode.GetParameterValue(2, 0).split(",")]    

                slicer.mrmlScene.RemoveNode(inputScan)
                slicer.mrmlScene.RemoveNode(inputLabelMap)
                toWrite = [case_id]
                if self.ui.GLCMFeaturesCheckBox.isChecked():
                    toWrite += GLCMfeatures
                if self.ui.GLRLMFeaturesCheckBox.isChecked():
                    toWrite += GLRLMfeatures
                if self.ui.BMFeaturesCheckBox.isChecked():
                    toWrite += BMfeatures
                cw.writerow(toWrite)

                file.flush()  
                self.ui.ComputeFeaturesProgressBar.visible = False
            
    def onColorMapNodeModifiedSerializer(self, cliMapNode, event):
        if not cliMapNode.IsBusy():
            self.removeObserver(cliMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModified)
            logging.info('%s Status: %s' % (cliMapNode.GetName(), cliMapNode.GetStatusString()))
            if cliMapNode.GetStatusString() == 'Completed':
                # Update progress bar
                self.ui.ComputeTextureMapsProgressBar.value += 1
                if self.ui.ComputeTextureMapsProgressBar.value == self.ui.ComputeTextureMapsProgressBar.maximum:
                    self.ui.ComputeTextureMapsProgressBar.visible = False

                outputDifussionWeightedVolumeNode = slicer.mrmlScene.GetNodeByID(cliMapNode.GetParameterValue(0,1))
                outputDir = self.ui.OutputFolderDirectoryPathLineEdit.currentPath
                self.exportVolumeToFile(outputDifussionWeightedVolumeNode, outputDir)
                
                # clear nodes from slicer
                slicer.mrmlScene.RemoveNode(outputDifussionWeightedVolumeNode)
                slicer.mrmlScene.RemoveNode(slicer.mrmlScene.GetNodeByID(cliMapNode.GetParameterValue(0,0))) # inputScan
                slicer.mrmlScene.RemoveNode(slicer.mrmlScene.GetNodeByID(cliMapNode.GetParameterValue(0,2))) #inputLabelMap
    
    def onColorMapNodeModified(self, cliMapNode, event):
        if not cliMapNode.IsBusy():
            self.removeObserver(cliMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModified)
            logging.info('%s Status: %s' % (cliMapNode.GetName(), cliMapNode.GetStatusString()))
            if cliMapNode.GetStatusString() == 'Completed':
                outputDifussionWeightedVolumeNode = slicer.mrmlScene.GetNodeByID(cliMapNode.GetParameterValue(0,1))
                item_count = self.ui.featureSetComboBox.count
                self.ui.featureSetComboBox.addItem(outputDifussionWeightedVolumeNode.GetName(), outputDifussionWeightedVolumeNode)  
                self.ui.featureSetComboBox.setCurrentIndex(item_count)      
    
    def onFeatureSetNodeModified(self, cliNode, event):
        """ Only called in single image mode """
        if not cliNode.IsBusy():
          self.removeObserver(cliNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onFeatureSetNodeModified)
          logging.info('%s status: %s' % (cliNode.GetName(),cliNode.GetStatusString()))
          if cliNode.GetStatusString() == 'Completed':
            self.computedFeatures[cliNode.GetName()] = list(map(float, cliNode.GetParameterValue(2, 0).split(",")))
            self.onDisplayFeatures()

    def exportVolumeToFile(self, volumeNode: vtkMRMLDiffusionWeightedVolumeNode, outputDir: str):
        if self.ui.separateFeaturesCheckBox.isChecked():
            parameters = dict()
            parameters["inputVolume"] = volumeNode
            parameters["outputFileBaseName"] = Path(outputDir)/volumeNode.GetName()
            slicer.cli.run(slicer.modules.separatevectorimage,
                        None,
                        parameters,
                        wait_for_completion=True)
        else:
            slicer.util.saveNode(volumeNode, Path(outputDir)/(volumeNode.GetName() + ".nhdr"))

    def onDisplayFeatures(self):
        if self.computedFeatures['GLCMFeatures'] is not None:
            for i in range(8):
                self.ui.displayFeaturesTableWidget.item(i,1).setText(self.computedFeatures['GLCMFeatures'][i])

        if self.computedFeatures['GLRLMFeatures'] is not None:
            for i in range(10):
                self.ui.displayFeaturesTableWidget.item(i, 3).setText(self.computedFeatures['GLRLMFeatures'][i])

        if self.computedFeatures['BMFeatures'] is not None:
            for i in range(5):
                self.ui.displayFeaturesTableWidget.item(i, 5).setText(self.computedFeatures['BMFeatures'][i])

    def getCaseID(self, file):
        filename = Path(file).stem
        case_id = filename.split('Scan_')[1]
        return case_id

    def onComputeTextureMaps(self):

        if not (self.ui.GLCMFeaturesCheckBox.isChecked() or self.ui.GLRLMFeaturesCheckBox.isChecked() or self.ui.BMFeaturesCheckBox.isChecked()):
            slicer.util.errorDisplay("Please select at least one type of features to compute")
            return

        inputData = self.getAlgorithmInputs()
    
        if not inputData:
            return
        
        if self.serializerModeActive:
            self.ComputeTextureMapsSerializerMode(inputData)
        else:
            self.ComputeTextureMapsSingleMode(inputData)
        
    def ComputeTextureMapsSingleMode(self, inputData):
        
        input = inputData[0] # In single mode, cannot be a list with len > 0
        inputScan, inputLabelMap = input
        case_id = inputScan.GetName()

        isValid = self.logic.inputDataVerification(inputScan, inputLabelMap)
        if not isValid:
            return

        if self.ui.GLCMFeaturesCheckBox.isChecked():
            parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLCMFeaturesValue)
            GLCMMapNode = self.logic.computeSingleTextureMap(slicer.modules.computeglcmfeaturemaps,
                                    inputScan,
                                    parameters,
                                    f"GLCMFeatureMaps_{case_id}",
                                    inputLabelMap)
            self.addObserver(GLCMMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModified)

        if self.ui.GLRLMFeaturesCheckBox.isChecked():
            parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLRLMFeaturesValue)
            GLRLMMapNode = self.logic.computeSingleTextureMap(slicer.modules.computeglrlmfeaturemaps,
                                    inputScan,
                                    parameters,
                                    f"GLRLMFeatureMaps_{case_id}",
                                    inputLabelMap)
            self.addObserver(GLRLMMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModified)

        if self.ui.BMFeaturesCheckBox.isChecked():
            parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().BMFeaturesValue)
            BMMapNode = self.logic.computeSingleTextureMap(slicer.modules.computebmfeaturemaps,
                                    inputScan,
                                    parameters,
                                    f"BMFeatureMaps_{case_id}",
                                    inputLabelMap)
            self.addObserver(BMMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModified)

        self.ui.ResultsCollapsibleButton.collapsed = False
        self.ui.DisplayColormapsCollapsibleGroupBox.collapsed = False

    def ComputeTextureMapsSerializerMode(self, inputData):

        if not self.ui.OutputFolderDirectoryPathLineEdit.currentPath:
            slicer.util.errorDisplay("Please specify an output directory for saving results")
            return
        
        stepsPerCase = sum((
            self.ui.GLCMFeaturesCheckBox.isChecked(),
            self.ui.GLRLMFeaturesCheckBox.isChecked(),
            self.ui.BMFeaturesCheckBox.isChecked(),
        ))

        self.ui.ComputeTextureMapsProgressBar.value = 0
        self.ui.ComputeTextureMapsProgressBar.minimum = 0 
        self.ui.ComputeTextureMapsProgressBar.maximum = len(inputData) * stepsPerCase
        self.ui.ComputeTextureMapsProgressBar.visible = True

        for input in inputData:

            inputScan, inputLabelMap = input

            # Get case ID
            case_id = self.getCaseID(inputScan)

            # Load in the input files
            inputScan = slicer.util.loadNodeFromFile(inputScan,
                'VolumeFile',
                {'labelmap': False, 'show': False},
            )
            
            if inputLabelMap:
                inputLabelMap = slicer.util.loadNodeFromFile(inputLabelMap,
                    'VolumeFile',
                    {'labelmap': True, 'show': False},
                )

            #If the scan is a vector image, convert to scalar
            if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):
                if not self.ui.SerializerConvertToScalarCheckBox.isChecked():
                    slicer.util.warningDisplay("Detected an input scan that has a vector pixel type. Skipping texture map computation.")
                    continue
                else:
                    inputScan = self.SerializerModeVectorToScalarConversion(inputScan)
                    
            isValid = self.logic.inputDataVerification(inputScan, inputLabelMap)
            if not isValid:
                self.ui.ComputeTextureMapsProgressBar.visible = False
                return

            if self.ui.GLCMFeaturesCheckBox.isChecked():
                parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLCMFeaturesValue)
                GLCMMapNode = self.logic.computeSingleTextureMap(slicer.modules.computeglcmfeaturemaps,
                                        inputScan,
                                        parameters,
                                        f"GLCMFeatureMaps_{case_id}",
                                        inputLabelMap)
                self.addObserver(GLCMMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModifiedSerializer)

            if self.ui.GLRLMFeaturesCheckBox.isChecked():
                parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().GLRLMFeaturesValue)
                GLRLMMapNode = self.logic.computeSingleTextureMap(slicer.modules.computeglrlmfeaturemaps,
                                        inputScan,
                                        parameters,
                                        f"GLRLMFeatureMaps_{case_id}",
                                        inputLabelMap)
                self.addObserver(GLRLMMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModifiedSerializer)

            if self.ui.BMFeaturesCheckBox.isChecked():
                parameters = self.logic.convertParameterPackToDict(self.logic.getParameterNode().BMFeaturesValue)
                BMMapNode = self.logic.computeSingleTextureMap(slicer.modules.computebmfeaturemaps,
                                        inputScan,
                                        parameters,
                                        f"BMFeatureMaps_{case_id}",
                                        inputLabelMap)
                self.addObserver(BMMapNode, slicer.vtkMRMLCommandLineModuleNode().StatusModifiedEvent, self.onColorMapNodeModifiedSerializer)

        # ----------------- Results Collapsible Button ----------------------- #

    def onFeatureSetChanged(self, index):

        currentFeatureMapNode = self.ui.featureSetComboBox.itemData(index)
        self.ui.featureComboBox.clear()
        if currentFeatureMapNode is None:
            return

        # Set the selected feature names in the featureCombobox
        if currentFeatureMapNode.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 8:
            self.ui.featureComboBox.addItems(self.CFeatures)
        elif currentFeatureMapNode.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 10:
            self.ui.featureComboBox.addItems(self.RLFeatures)
        elif currentFeatureMapNode.GetDisplayNode().GetInputImageData().GetNumberOfScalarComponents() == 5:
            self.ui.featureComboBox.addItems(self.BMFeatures)

        # # Set the feature Set displayed in Slicer to the selected module
        slicer.util.setSliceViewerLayers(background = currentFeatureMapNode.GetID())

    def onFeatureChanged(self, index):
        if self.ui.featureComboBox.currentText:
            selectedNode = self.ui.featureSetComboBox.currentData
            if selectedNode is not None:
                # Change the feature displayed to the one wanted by the user
                selectedNode.GetDisplayNode().SetDiffusionComponent(index)
        else:
            return

    def onSaveTable(self):
        self.logic.SaveTableAsCSV(self.ui.displayFeaturesTableWidget,self.ui.CSVPathLineEdit.currentPath)

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

    def computeLabelStatistics(self, inputScan, inputLabelMap):
        """ Use slicer core module to get the min/max intensity value inside the mask.
        Returns tuple (min, max) with intensity values inside the mask. """
        # Export lapel map node into a segmentation node
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(inputLabelMap, segmentationNode)

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

    # ------- Test to ensure that the input data exist and are conform ------- #

    def inputDataVerification(self, inputScan, inputLabelMap = None):
        
        if not(inputScan):
            slicer.util.warningDisplay("Please specify an input scan")
            return False
        else:
            if inputScan.IsTypeOf('vtkMRMLVectorVolumeNode'):
                slicer.util.warningDisplay("The input scan has a vector pixel type, please transform it to a scalar type first.")
                return False
        
        if inputScan and inputLabelMap:
            if inputScan.GetImageData().GetDimensions() != inputLabelMap.GetImageData().GetDimensions():
                slicer.util.warningDisplay("The input scan and the input segmentation must be the same size")
                return False
            if not self.isClose(inputScan.GetSpacing(), inputLabelMap.GetSpacing(), 0.0, 1e-04) or \
                    not self.isClose(inputScan.GetOrigin(), inputLabelMap.GetOrigin(), 0.0, 1e-04):
                slicer.util.warningDisplay("The input scan and the input segmentation must overlap: same origin, spacing and orientation")
                return False
        return True

    # ---------------- Convert Vector Input to Scalar ---------------------- #
    def convertInputVectorToScalarVolume(self, inputScan, outputScalarVolume, conversionMethod, componentToExtract):
        externalLogic = VectorToScalarVolume.VectorToScalarVolumeLogic()
        # externalLogic.run performs the validation of parameters.
        externalLogic.runWithVariables(inputScan, outputScalarVolume, conversionMethod, componentToExtract)

    # ---------------- Computation of the wanted features---------------------- #

    def convertParameterPackToDict(self, featureParameterPack):
        feature_dict = featureParameterPack.__dict__
        feature_dict.pop('_observedPackValues')
        for key_old in list(feature_dict.keys()):
            key_new = key_old.split('_')[2]
            feature_dict[key_new] = feature_dict.pop(key_old)

        return feature_dict
    
    def computeSingleFeature(self,
                              CLIname,
                              inputScan: vtkMRMLScalarVolumeNode,
                              parameters: dict,
                              outputName,
                              inputLabelMap : Optional[vtkMRMLLabelMapVolumeNode] = None, 
                              wait_for_completion: bool = False):
        """
        Args:

        Returns:
        """
        logging.info('Computing %s Features ...' % outputName)
        parameters["inputVolume"] = inputScan
        if inputLabelMap:
            parameters["inputMask"] = inputLabelMap
        run_node = slicer.cli.createNode(CLIname, parameters)
        run_node.SetName(outputName)
        run_node = slicer.cli.run(CLIname, node=run_node, parameters=parameters, wait_for_completion=wait_for_completion)
        return run_node
        
    # --------------- Computation of the wanted colormaps --------------------- #
    def computeSingleTextureMap(self,
                              CLIname, 
                              inputScan: vtkMRMLScalarVolumeNode, 
                              parameters: dict,
                              outputName: str, 
                              inputLabelMap: Optional[vtkMRMLLabelMapVolumeNode] = None, 
                              wait_for_completion: bool = False):
        """
        Args: 
        Returns the feature set node with rainbow colormap
        """
        parameters["inputVolume"] = inputScan
        if inputLabelMap:
            parameters["inputMask"] = inputLabelMap
        volumeNode = vtkMRMLDiffusionWeightedVolumeNode()
        slicer.mrmlScene.AddNode(volumeNode)
        displayNode = slicer.vtkMRMLDiffusionWeightedVolumeDisplayNode()
        slicer.mrmlScene.AddNode(displayNode)
        colorNode = slicer.util.getNode('Rainbow')
        displayNode.SetAndObserveColorNodeID(colorNode.GetID())
        volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        volumeNode.SetName(slicer.mrmlScene.GenerateUniqueName(outputName))
        parameters["outputVolume"] = volumeNode
        run_node = slicer.cli.createNode(CLIname)
        run_node.SetName(outputName)
        run_node = slicer.cli.run(CLIname,
                       node = run_node,
                       parameters = parameters,
                       wait_for_completion=wait_for_completion)
        return run_node

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
