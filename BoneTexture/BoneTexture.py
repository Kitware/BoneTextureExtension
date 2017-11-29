import os
import qt

import slicer
from slicer.ScriptedLoadableModule import *

################################################################################
############################  Bone Texture #####################################
################################################################################


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
        self.BMFeatures = ["BVTV", "TbTh", "TbSp", "TbN", "BSBV" ]
        self.GLCMFeaturesValueDict = {}
        self.GLCMFeaturesValueDict["insideMask"] = 1
        self.GLCMFeaturesValueDict["binNumber"] = 10
        self.GLCMFeaturesValueDict["pixelIntensityMin"] = 0
        self.GLCMFeaturesValueDict["pixelIntensityMax"] = 4000
        self.GLCMFeaturesValueDict["neighborhoodRadius"] = 4
        self.GLRLMFeaturesValueDict = {}
        self.GLRLMFeaturesValueDict["insideMask"] = 1
        self.GLRLMFeaturesValueDict["binNumber"] = 10
        self.GLRLMFeaturesValueDict["pixelIntensityMin"] = 0
        self.GLRLMFeaturesValueDict["pixelIntensityMax"] = 4000
        self.GLRLMFeaturesValueDict["neighborhoodRadius"] = 4
        self.GLRLMFeaturesValueDict["distanceMin"] = 0.00
        self.GLRLMFeaturesValueDict["distanceMax"] = 1.00
        self.BMFeaturesValueDict = {}
        self.BMFeaturesValueDict["threshold"] = 1
        self.BMFeaturesValueDict["neighborhoodRadius"] = 4

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
        self.singleCaseGroupBox = self.logic.get("SingleCaseGroupBox")
        self.inputScanMRMLNodeComboBox = self.logic.get("InputScanMRMLNodeComboBox")
        self.inputScanMRMLNodeComboBox.setMRMLScene(slicer.mrmlScene)
        self.inputSegmentationMRMLNodeComboBox = self.logic.get("InputSegmentationMRMLNodeComboBox")
        self.inputSegmentationMRMLNodeComboBox.setMRMLScene(slicer.mrmlScene)

        # ---------------- Computation Collapsible Button -------------------- #

        self.computationCollapsibleButton = self.logic.get("ComputationCollapsibleButton")
        self.featureChoiceCollapsibleGroupBox = self.logic.get("FeatureChoiceCollapsibleGroupBox")
        self.gLCMFeaturesCheckBox = self.logic.get("GLCMFeaturesCheckBox")
        self.gLRLMFeaturesCheckBox = self.logic.get("GLRLMFeaturesCheckBox")
        self.bMFeaturesCheckBox = self.logic.get("BMFeaturesCheckBox")
        self.computeFeaturesPushButton = self.logic.get("ComputeFeaturesPushButton")
        self.computeColormapsPushButton = self.logic.get("ComputeColormapsPushButton")
        self.GLCMparametersCollapsibleGroupBox = self.logic.get("GLCMParametersCollapsibleGroupBox")
        self.GLCMinsideMaskValueSpinBox = self.logic.get("GLCMInsideMaskValueSpinBox")
        self.GLCMnumberOfBinsSpinBox = self.logic.get("GLCMNumberOfBinsSpinBox")
        self.GLCMminVoxelIntensitySpinBox = self.logic.get("GLCMMinVoxelIntensitySpinBox")
        self.GLCMmaxVoxelIntensitySpinBox = self.logic.get("GLCMMaxVoxelIntensitySpinBox")
        self.GLCMneighborhoodRadiusSpinBox = self.logic.get("GLCMNeighborhoodRadiusSpinBox")
        self.GLRLMparametersCollapsibleGroupBox = self.logic.get("GLRLMParametersCollapsibleGroupBox")
        self.GLRLMinsideMaskValueSpinBox = self.logic.get("GLRLMInsideMaskValueSpinBox")
        self.GLRLMnumberOfBinsSpinBox = self.logic.get("GLRLMNumberOfBinsSpinBox")
        self.GLRLMminVoxelIntensitySpinBox = self.logic.get("GLRLMMinVoxelIntensitySpinBox")
        self.GLRLMmaxVoxelIntensitySpinBox = self.logic.get("GLRLMMaxVoxelIntensitySpinBox")
        self.GLRLMminDistanceSpinBox = self.logic.get("GLRLMMinDistanceSpinBox")
        self.GLRLMmaxDistanceSpinBox = self.logic.get("GLRLMMaxDistanceSpinBox")
        self.GLRLMneighborhoodRadiusSpinBox = self.logic.get("GLRLMNeighborhoodRadiusSpinBox")
        self.bMparametersCollapsibleGroupBox = self.logic.get("BMParametersCollapsibleGroupBox")
        self.BMthresholdSpinBox = self.logic.get("BMThresholdSpinBox")
        self.BMneighborhoodRadiusSpinBox = self.logic.get("BMNeighborhoodRadiusSpinBox")

        # ----------------- Results Collapsible Button ----------------------- #

        self.resultsCollapsibleButton = self.logic.get("ResultsCollapsibleButton")
        self.featureSetMRMLNodeComboBox = self.logic.get("featureSetMRMLNodeComboBox")
        self.featureSetMRMLNodeComboBox.setMRMLScene(slicer.mrmlScene)
        self.featureComboBox = self.logic.get("featureComboBox")
        self.displayColormapsCollapsibleGroupBox = self.logic.get("DisplayColormapsCollapsibleGroupBox")
        self.displayFeaturesTableWidget = self.logic.get("displayFeaturesTableWidget")

        # -------------------------------------------------------------------- #
        # ---------------------------- Connections --------------------------- #
        # -------------------------------------------------------------------- #

        # ---------------- Input Data Collapsible Button --------------------- #

        self.GLCMinsideMaskValueSpinBox.connect('valueChanged(int)',lambda: self.onGLCMFeaturesValueDictModified("insideMask", self.GLCMinsideMaskValueSpinBox.value))
        self.GLCMnumberOfBinsSpinBox.connect('valueChanged(int)', lambda: self.onGLCMFeaturesValueDictModified("binNumber", self.GLCMnumberOfBinsSpinBox.value))
        self.GLCMminVoxelIntensitySpinBox.connect('valueChanged(int)', lambda: self.onGLCMFeaturesValueDictModified("pixelIntensityMin", self.GLCMminVoxelIntensitySpinBox.value))
        self.GLCMmaxVoxelIntensitySpinBox.connect('valueChanged(int)', lambda: self.onGLCMFeaturesValueDictModified("pixelIntensityMax", self.GLCMmaxVoxelIntensitySpinBox.value))
        self.GLCMneighborhoodRadiusSpinBox.connect('valueChanged(int)', lambda: self.onGLCMFeaturesValueDictModified("neighborhoodRadius", self.GLCMneighborhoodRadiusSpinBox.value))
        self.GLRLMinsideMaskValueSpinBox.connect('valueChanged(int)', lambda: self.onGLRLMFeaturesValueDictModified("insideMask", self.GLRLMinsideMaskValueSpinBox.value))
        self.GLRLMnumberOfBinsSpinBox.connect('valueChanged(int)', lambda: self.onGLRLMFeaturesValueDictModified("binNumber", self.GLRLMnumberOfBinsSpinBox.value))
        self.GLRLMminVoxelIntensitySpinBox.connect('valueChanged(int)', lambda: self.onGLRLMFeaturesValueDictModified("pixelIntensityMin", self.GLRLMminVoxelIntensitySpinBox.value))
        self.GLRLMmaxVoxelIntensitySpinBox.connect('valueChanged(int)', lambda: self.onGLRLMFeaturesValueDictModified("pixelIntensityMax", self.GLRLMmaxVoxelIntensitySpinBox.value))
        self.GLRLMminDistanceSpinBox.connect('valueChanged(double)', lambda: self.onGLRLMFeaturesValueDictModified("distanceMin", self.GLRLMminDistanceSpinBox.value))
        self.GLRLMmaxDistanceSpinBox.connect('valueChanged(double)', lambda: self.onGLRLMFeaturesValueDictModified("distanceMax", self.GLRLMmaxDistanceSpinBox.value))
        self.GLRLMneighborhoodRadiusSpinBox.connect('valueChanged(int)', lambda: self.onGLRLMFeaturesValueDictModified("neighborhoodRadius", self.GLRLMneighborhoodRadiusSpinBox.value))
        self.BMthresholdSpinBox.connect('valueChanged(int)', lambda: self.onBMFeaturesValueDictModified("threshold", self.BMthresholdSpinBox.value))
        self.BMneighborhoodRadiusSpinBox.connect('valueChanged(int)', lambda: self.onBMFeaturesValueDictModified("neighborhoodRadius", self.BMneighborhoodRadiusSpinBox.value))

        # ---------------- Computation Collapsible Button -------------------- #

        self.computeFeaturesPushButton.connect('clicked()', self.onComputeFeatures)
        self.computeColormapsPushButton.connect('clicked()', self.onComputeColormaps)

        # ----------------- Results Collapsible Button ----------------------- #

        self.featureSetMRMLNodeComboBox.connect("currentNodeChanged(vtkMRMLNode*)", self.onFeatureSetChanged)
        self.featureComboBox.connect("currentIndexChanged(int)", self.onFeatureChanged)

        # -------------------------------------------------------------------- #
        # -------------------------- Initialisation -------------------------- #
        # -------------------------------------------------------------------- #

        # ******************************************************************** #
        # ----------------------- Algorithm ---------------------------------- #
        # ******************************************************************** #

        # ---------------- Input Data Collapsible Button --------------------- #

    def onGLCMFeaturesValueDictModified(self, key, value):
        self.GLCMFeaturesValueDict[key] = value

    def onGLRLMFeaturesValueDictModified(self, key, value):
        self.GLRLMFeaturesValueDict[key] = value

    def onBMFeaturesValueDictModified(self, key, value):
        self.BMFeaturesValueDict[key] = value

        # ---------------- Computation Collapsible Button -------------------- #

    def onComputeFeatures(self):
        featureVector = self.logic.computeFeatures(self.inputScanMRMLNodeComboBox.currentNode(),
                                                   self.inputSegmentationMRMLNodeComboBox.currentNode(),
                                                   self.gLCMFeaturesCheckBox.isChecked(),
                                                   self.gLRLMFeaturesCheckBox.isChecked(),
                                                   self.bMFeaturesCheckBox.isChecked(),
                                                   self.GLCMFeaturesValueDict,
                                                   self.GLRLMFeaturesValueDict,
                                                   self.BMFeaturesValueDict)

        if featureVector[0]:
            for i in range(8):
                self.displayFeaturesTableWidget.item(i,1).setText(featureVector[0][i])

        if featureVector[1]:
            for i in range(10):
                self.displayFeaturesTableWidget.item(i, 3).setText(featureVector[1][i])

        if featureVector[2]:
            for i in range(5):
                self.displayFeaturesTableWidget.item(i, 5).setText(featureVector[2][i])




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

        # ---------------- Exportation Collapsible Button -------------------- #


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


    def isClose(self, a, b, rel_tol=0.0, abs_tol=0.0):
        for i in range(len(a)):
            if not (abs(a[i] - b[i]) <= max(rel_tol * max(abs(a[i]), abs(b[i])), abs_tol)):
                return flase
        return True

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
        if inputScan and inputSegmentation:
            if inputScan.GetImageData().GetDimensions() != inputSegmentation.GetImageData().GetDimensions():
                slicer.util.warningDisplay("The input san and the input segmentation must be the same size")
                return False
            if not self.isClose(inputScan.GetSpacing(), inputSegmentation.GetSpacing(), 0.0, 1e-04 )or \
                    not self.isClose(inputScan.GetOrigin(), inputSegmentation.GetOrigin(), 0.0, 1e-04 ):
                slicer.util.warningDisplay("The input san and the input segmentation must overlap: same origin, spacing and orientation")
                return False
        return True

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

        if not (computeGLCMFeatures or computeGLRLMFeatures or computeBMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return
        if not (self.inputDataVerification(inputScan, inputSegmentation)):
            return

        resultVector = [None, None, None]

        if computeGLCMFeatures:
            resultVector[0] = self.computeSingleFeatureSet(inputScan,
                                                           inputSegmentation,
                                                           slicer.modules.computeglcmfeatures,
                                                           GLCMFeaturesValueDict)

        if computeGLRLMFeatures:
            resultVector[1] = self.computeSingleFeatureSet(inputScan,
                                                           inputSegmentation,
                                                           slicer.modules.computeglrlmfeatures,
                                                           GLRLMFeaturesValueDict)

        if computeBMFeatures:
            resultVector[2] = self.computeSingleFeatureSet(inputScan,
                                                           inputSegmentation,
                                                           slicer.modules.computebmfeatures,
                                                           BMFeaturesValueDict)

        return resultVector

    def computeSingleFeatureSet(self,
                               inputScan,
                               inputSegmentation,
                               CLIname,
                               valueDict):
        parameters = dict(valueDict)
        parameters["inputVolume"] = inputScan
        parameters["inputMask"] = inputSegmentation
        CLI = slicer.cli.run(CLIname,
                             None,
                             parameters,
                             wait_for_completion=True)
        return list(map(float, CLI.GetParameterValue(2, 0).split(",")))

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

        if not (computeGLCMFeatures or computeGLRLMFeatures or computeBMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return
        if not (self.inputDataVerification(inputScan, inputSegmentation)):
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
