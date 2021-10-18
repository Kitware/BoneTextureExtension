import os
import re
import qt
import slicer
from slicer.ScriptedLoadableModule import *
import csv

class case(object):
    def __init__(self, ID):
        self.caseID = ID
        self.scanFilePath = None
        self.segmentationFilePath = None
        self.outputFilePath = None
        self.GLCMFeatures = None
        self.GLRLMFeatures = None
        self.BMFeatures = None

    def __str__(self):
        return ( 'caseID: %s \n scanFilePath: %s \n segmentationFilePath: %s \n outputFilePath: %s'
                % (self.caseID, self.scanFilePath, self.segmentationFilePath, self.outputFilePath) )

################################################################################
######################  Bone Texture Serializer ################################
################################################################################


class BoneTextureSerializer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Bone Texture Serializer"
        self.parent.categories = ["Quantification"]
        self.parent.dependencies = []
        self.parent.contributors = ["Jean-Baptiste VIMORT (Kitware Inc.)"]
        self.parent.helpText = """
        This module to serialyse the BoneTexture's algorythms on several cases contained in the same folder.
        The input data should be named in the folowing way: Scan"ID".nrrd (for the input scan) and Segm"ID".nrrd
        (for the segmentation if it exist)
        """
        self.parent.acknowledgementText = """
        This work was supported by the National Institute of Health (NIH) National Institute for
        Dental and Craniofacial Research (NIDCR) R01EB021391 (Textural Biomarkers of Arthritis for
        the Subchondral Bone in the Temporomandibular Joint)
        """

################################################################################
##########################  Bone Texture Widget ################################
################################################################################


class BoneTextureSerializerWidget(ScriptedLoadableModuleWidget):

    # ************************************************************************ #
    # -------------------------- Initialisation ------------------------------ #
    # ************************************************************************ #

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        print("-----  Bone Texture Serializer widget setup -----")
        self.moduleName = 'BoneTextureSerializer'
        scriptedModulesPath = eval('slicer.modules.%s.path' % self.moduleName.lower())
        scriptedModulesPath = os.path.dirname(scriptedModulesPath)

        # - Initialisation of Bone Texture Serializer and its logic - #

        self.logic = BoneTextureSerializerLogic(self)
        self.caseDict = dict()
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
        self.inputFolderDirectoryButton = self.logic.get("InputFolderDirectoryButton")

        # ---------------- Computation Collapsible Button -------------------- #

        self.computationCollapsibleButton = self.logic.get("ComputationCollapsibleButton")
        self.featureChoiceCollapsibleGroupBox = self.logic.get("FeatureChoiceCollapsibleGroupBox")
        self.gLCMFeaturesCheckBox = self.logic.get("GLCMFeaturesCheckBox")
        self.gLRLMFeaturesCheckBox = self.logic.get("GLRLMFeaturesCheckBox")
        self.bMFeaturesCheckBox = self.logic.get("BMFeaturesCheckBox")
        self.computeFeaturesPushButton = self.logic.get("ComputeFeaturesPushButton")
        self.computeColormapsPushButton = self.logic.get("ComputeColormapsPushButton")
        self.computationProgressBar = self.logic.get("ComputationProgressBar")
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

        # ---------------- Export Collapsible Button -------------------- #

        self.exportationCollapsibleButton = self.logic.get("ExportCollapsibleButton")
        self.outputFolderDirectoryButton = self.logic.get("OutputFolderDirectoryButton")
        self.separateFeaturesCheckBox = self.logic.get("separateFeaturesCheckBox")
        self.saveAsCSVCheckBox = self.logic.get("saveAsCSVCheckBox")
        self.writeCSVHeaderCheckBox = self.logic.get("writeCSVHeaderCheckBox")

        # there's probably a way to do this in the .ui file...
        self.saveAsCSVCheckBox.stateChanged.connect(self.writeCSVHeaderCheckBox.setEnabled)

        # -------------------------------------------------------------------- #
        # ---------------------------- Connections --------------------------- #
        # -------------------------------------------------------------------- #

        # ---------------- Input Data Collapsible Button --------------------- #

        self.inputFolderDirectoryButton.connect('directoryChanged(const QString &)', self.onDirectoryChanged)
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

        # ---------------- Export Collapsible Button -------------------- #

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

    def onDirectoryChanged(self):
        self.logic.updateCaseDictionary(self.caseDict,
                                        self.inputFolderDirectoryButton.directory)

        # ---------------- Computation Collapsible Button -------------------- #

    def onComputeFeatures(self):
        self.logic.computeFeatures(self.caseDict,
                                   self.gLCMFeaturesCheckBox.isChecked(),
                                   self.gLRLMFeaturesCheckBox.isChecked(),
                                   self.bMFeaturesCheckBox.isChecked(),
                                   self.GLCMFeaturesValueDict,
                                   self.GLRLMFeaturesValueDict,
                                   self.BMFeaturesValueDict,
                                   self.outputFolderDirectoryButton.directory)

    def onComputeColormaps(self):
        self.logic.computeColormaps(self.caseDict,
                                    self.gLCMFeaturesCheckBox.isChecked(),
                                    self.gLRLMFeaturesCheckBox.isChecked(),
                                    self.bMFeaturesCheckBox.isChecked(),
                                    self.GLCMFeaturesValueDict,
                                    self.GLRLMFeaturesValueDict,
                                    self.BMFeaturesValueDict,
                                    self.outputFolderDirectoryButton.directory,
                                    self.separateFeaturesCheckBox.isChecked(),
                                    self.saveAsCSVCheckBox.isChecked(),
                                    self.writeCSVHeaderCheckBox.isChecked())

        # ---------------- Export Collapsible Button -------------------- #

    def cleanup(self):
        pass


################################################################################
#####################  Bone Texture Serializer Logic ###########################
################################################################################


class BoneTextureSerializerLogic(ScriptedLoadableModuleLogic):

    # ************************************************************************ #
    # ----------------------- Initialisation --------------------------------- #
    # ************************************************************************ #

    def __init__(self, interface):
        print("----- Bone Texture Serializer logic init -----")
        self.interface = interface
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

    # ************************************************************************ #
    # ------------------------ Algorithm ------------------------------------- #
    # ************************************************************************ #

    # ----------- Useful functions to access the .ui file elements ----------- #

    def get(self, objectName):
        return self.findWidget(self.interface.widget, objectName)

    def isClose(self, a, b, rel_tol=0.0, abs_tol=0.0):
        for i in range(len(a)):
            if not (abs(a[i] - b[i]) <= max(rel_tol * max(abs(a[i]), abs(b[i])), abs_tol)):
                return False
        return True

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
                slicer.util.warningDisplay("The input scan and the input segmentation must be the same size")
                return False
            if not self.isClose(inputScan.GetSpacing(), inputSegmentation.GetSpacing(), 0.0, 1e-04 )or \
                   not self.isClose(inputScan.GetOrigin(), inputSegmentation.GetOrigin(), 0.0, 1e-04 ):
                slicer.util.warningDisplay("The input scan and the input segmentation must overlap: same origin, spacing and orientation")
                return False
        return True

    # ---------------- Fill the case dictionary ------------------------------- #

    def updateCaseDictionary(self,
                             caseDict,
                             inputDirectory):
        """ The input data should be named in the folowing way: Scan"ID".nrrd (for the input scan) and Segm"ID".nrrd
        (for the segmentation if it exist)
        """
        caseDict.clear()
        for fileName in os.listdir(inputDirectory):
            if fileName.endswith(".nrrd"):
                print(fileName)
                if fileName.startswith("Segm"):
                    caseID = re.search("Segm(.+?).nrrd", fileName).group(1)
                    if caseID in caseDict:
                        caseDict[caseID].segmentationFilePath = os.path.join(inputDirectory , fileName)
                    else:
                        temp = case(caseID)
                        temp.segmentationFilePath = os.path.join(inputDirectory , fileName)
                        caseDict[caseID] = temp
                elif fileName.startswith("Scan"):
                    caseID = re.search("Scan(.+?).nrrd", fileName).group(1)
                    if caseID in caseDict:
                        caseDict[caseID].scanFilePath = os.path.join(inputDirectory , fileName)
                    else:
                        temp = case(caseID)
                        temp.scanFilePath = os.path.join(inputDirectory , fileName )
                        caseDict[caseID] = temp
        for key in caseDict:
            print( caseDict[key] )

    # ---------------- Computation of the wanted features---------------------- #

    def computeFeatures(self,
                        caseDict,
                        computeGLCMFeatures,
                        computeGLRLMFeatures,
                        computeBMFeatures,
                        GLCMFeaturesValueDict,
                        GLRLMFeaturesValueDict,
                        BMFeaturesValueDict,
                        outputDirectory):

        if not (computeGLCMFeatures or computeGLRLMFeatures or computeBMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return

        stepsPerCase = sum((
            bool(computeGLCMFeatures),
            bool(computeGLRLMFeatures),
            bool(computeBMFeatures),
        ))

        progress = self.interface.computationProgressBar
        progress.value = 0
        progress.minimum = 0
        progress.maximum = len(caseDict) * stepsPerCase
        progress.visible = True

        properties = {}

        texturalFeaturesPath = os.path.join(outputDirectory, "TexturalFeatureTable.csv")
        with open(texturalFeaturesPath, "w+") as file:
            print(file)
            cw = csv.writer(file, delimiter=',')
            for case in caseDict.values():
                print('Computing case: %s' % (case))
                properties['labelmap'] = False
                inputScan = slicer.util.loadNodeFromFile(case.scanFilePath, 'VolumeFile', properties, returnNode=True)
                inputScan = inputScan[1]
                properties['labelmap'] = True
                inputSegmentation = slicer.util.loadNodeFromFile(case.segmentationFilePath, 'VolumeFile', properties, returnNode=True)
                inputSegmentation = inputSegmentation[1]
                if not (self.inputDataVerification(inputScan, inputSegmentation)):
                    return

                if computeGLCMFeatures:
                    case.GLCMFeatures = self.computeSingleFeatureSet(inputScan,
                                                                     inputSegmentation,
                                                                     slicer.modules.computeglcmfeatures,
                                                                     GLCMFeaturesValueDict)
                    progress.value += 1

                if computeGLRLMFeatures:
                    case.GLRLMFeatures = self.computeSingleFeatureSet(inputScan,
                                                                      inputSegmentation,
                                                                      slicer.modules.computeglrlmfeatures,
                                                                      GLRLMFeaturesValueDict)
                    progress.value += 1

                if computeBMFeatures:
                    case.BMFeatures = self.computeSingleFeatureSet(inputScan,
                                                                   inputSegmentation,
                                                                   slicer.modules.computebmfeatures,
                                                                   BMFeaturesValueDict)
                    progress.value += 1

                slicer.mrmlScene.RemoveNode(inputScan)
                slicer.mrmlScene.RemoveNode(inputSegmentation)
                toWrite = [case.caseID]
                if (case.GLCMFeatures):
                    toWrite += case.GLCMFeatures
                if (case.GLRLMFeatures):
                    toWrite += case.GLRLMFeatures
                if (case.BMFeatures):
                    toWrite += case.BMFeatures
                cw.writerow(toWrite)

            progress.visible = False

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
        return list(map(float, CLI.GetParameterDefault(2, 0).split(",")))

    # --------------- Computation of the wanted colormaps --------------------- #

    def computeColormaps(self,
                         caseDict,
                         computeGLCMFeatures,
                         computeGLRLMFeatures,
                         computeBMFeatures,
                         GLCMFeaturesValueDict,
                         GLRLMFeaturesValueDict,
                         BMFeaturesValueDict,
                         outputDirectory,
                         saparateFeatureMaps,
                         saveAsCSV, writeCSVHeader):

        if not (computeGLCMFeatures or computeGLRLMFeatures or computeBMFeatures):
            slicer.util.warningDisplay("Please select at least one type of features to compute")
            return

        stepsPerCase = sum((
            bool(computeGLCMFeatures),
            bool(computeGLRLMFeatures),
            bool(computeBMFeatures),
        ))

        progress = self.interface.computationProgressBar
        progress.value = 0
        progress.minimum = 0
        progress.maximum = len(caseDict) * stepsPerCase
        progress.visible = True

        properties = {}
        for case in caseDict.values():
            inputScan = slicer.util.loadNodeFromFile(case.scanFilePath, 'VolumeFile', properties, returnNode=True)
            inputScan = inputScan[1]
            properties['labelmap'] = True
            inputSegmentation = slicer.util.loadNodeFromFile(case.segmentationFilePath, 'VolumeFile', properties, returnNode=True)
            inputSegmentation = inputSegmentation[1]

            if not (self.inputDataVerification(inputScan, inputSegmentation)):
                return

            print(case.caseID)

            storageforCSV = {}
            if saveAsCSV and (not os.path.exists(os.path.join(outputDirectory , "CSVfeatureMaps"))):
                os.makedirs(os.path.join(outputDirectory , "CSVfeatureMaps"))

            if computeGLCMFeatures:
                volumeNode = self.computeSingleColormap(inputScan,
                                                        inputSegmentation,
                                                        slicer.modules.computeglcmfeaturemaps,
                                                        GLCMFeaturesValueDict,
                                                        "GLCM_ColorMaps")
                if saparateFeatureMaps:
                    param = dict()
                    param["inputVolume"] = volumeNode
                    param["outputFileBaseName"] = os.path.join(outputDirectory , case.caseID  + "_GLCMFeatureMap")
                    slicer.cli.run(slicer.modules.separatevectorimage,
                                   None,
                                   param,
                                   wait_for_completion=True)
                else:
                    slicer.util.saveNode(volumeNode, os.path.join(outputDirectory , case.caseID + "_GLCMFeatureMap.nhdr"))

                storageforCSV["GLCM"] = volumeNode
                progress.value += 1

            if computeGLRLMFeatures:
                volumeNode = self.computeSingleColormap(inputScan,
                                                        inputSegmentation,
                                                        slicer.modules.computeglrlmfeaturemaps,
                                                        GLRLMFeaturesValueDict,
                                                        "GLRLM_ColorMaps")
                if saparateFeatureMaps:
                    param = dict()
                    param["inputVolume"] = volumeNode
                    param["outputFileBaseName"] = os.path.join(outputDirectory , case.caseID  + "_GLRLMFeatureMap")
                    slicer.cli.run(slicer.modules.separatevectorimage,
                                   None,
                                   param,
                                   wait_for_completion=True)
                else:
                    slicer.util.saveNode(volumeNode, os.path.join(outputDirectory , case.caseID + "_GLRLMFeatureMap.nhdr"))

                storageforCSV["GLRLM"] = volumeNode
                progress.value += 1

            if computeBMFeatures:
                volumeNode = self.computeSingleColormap(inputScan,
                                                        inputSegmentation,
                                                        slicer.modules.computebmfeaturemaps,
                                                        BMFeaturesValueDict,
                                                        "BM_ColorMaps")
                if saparateFeatureMaps:
                    param = dict()
                    param["inputVolume"] = volumeNode
                    param["outputFileBaseName"] = os.path.join(outputDirectory,
                                                               case.caseID + "_BMFeatureMap")
                    slicer.cli.run(slicer.modules.separatevectorimage,
                                   None,
                                   param,
                                   wait_for_completion=True)
                else:
                    slicer.util.saveNode(volumeNode,
                                         os.path.join(outputDirectory,
                                                      case.caseID + "_BMFeatureMap.nhdr"))

                storageforCSV["BM"] = volumeNode
                progress.value += 1

            import csv

            if saveAsCSV:
                tempdir = slicer.util.tempDirectory(key='BoneTextureSerializer')

                readers = []
                headings = []

                if computeGLCMFeatures:
                    name = os.path.join(tempdir, case.caseID + '_GLCM.csv')
                    slicer.cli.run(
                        slicer.modules.savevectorimageascsv,
                        None,
                        {
                            'inputMask': inputSegmentation,
                            'inputVolume': storageforCSV['GLCM'],
                            'outputFileBaseName': name,
                        },
                        wait_for_completion=True,
                    )
                    readers.append(csv.reader(open(name)))  # going to close these
                    headings.append(self.CFeatures)

                if computeGLRLMFeatures:
                    name = os.path.join(tempdir, case.caseID + '_GLRLM.csv')
                    slicer.cli.run(
                        slicer.modules.savevectorimageascsv,
                        None,
                        {
                            'inputMask': inputSegmentation,
                            'inputVolume': storageforCSV['GLRLM'],
                            'outputFileBaseName': name,
                        },
                        wait_for_completion=True,
                    )
                    readers.append(csv.reader(open(name)))  # going to close these
                    headings.append(self.RLFeatures)

                if computeBMFeatures:
                    name = os.path.join(tempdir, case.caseID + '_BM.csv')
                    slicer.cli.run(
                        slicer.modules.savevectorimageascsv,
                        None,
                        {
                            'inputMask': inputSegmentation,
                            'inputVolume': storageforCSV['BM'],
                            'outputFileBaseName': name,
                        },
                        wait_for_completion=True,
                    )
                    readers.append(csv.reader(open(name)))  # going to close these
                    headings.append(self.BMFeatures)

                # now we need to merge the csvs, and add a header.
                # since they were all generated with the same segmentation,
                # we can assume the order of the files is the same.
                # so we just need to grab the x,y,z coords and each of the values,
                # then save those to one csv in the output directory.

                outPath = os.path.join(
                    outputDirectory,
                    "CSVfeatureMaps",
                    case.caseID + "_FeatureMap.csv",
                )


                with open(outPath, 'w') as outFile:
                    writer = csv.writer(outFile)

                    if writeCSVHeader:
                        allHeadings = [field for heading in headings for field in heading]
                        writer.writerow(('X', 'Y', 'Z', *allHeadings))

                    for rows in zip(*readers):
                        # Shouldn't be needed... but just in case we didn't actually
                        # compute anything.
                        x = y = z = None

                        allData = []
                        for row in rows:
                            x, y, z, *data = row
                            allData.extend(data)

                        writer.writerow((x, y, z, *allData))

                readers.clear()  # triggers deletion and closes the file handles

                for storageNode in storageforCSV.values():
                    slicer.mrmlScene.RemoveNode(storageNode)

                slicer.mrmlScene.RemoveNode(inputScan)
                slicer.mrmlScene.RemoveNode(inputSegmentation)

                self.renameSeparatedFeatures(outputDirectory)

        progress.visible = False


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
                       wait_for_completion=True)

        return volumeNode

    def renameSeparatedFeatures(self, outputDirectory):
        for fileName in os.listdir(outputDirectory):
            for i in range(8):
                if fileName.endswith("GLCMFeatureMap_" + str(i+1) + ".nrrd"):
                    os.rename(os.path.join(outputDirectory, fileName),
                              os.path.join(outputDirectory, fileName.replace(
                                  "GLCMFeatureMap_" + str(i+1) + ".nrrd", "GLCMFeatureMap_" + self.CFeatures[i] + ".nrrd")))
            for i in range(10):
                if fileName.endswith("GLRLMFeatureMap_" + str(i+1) + ".nrrd"):
                    os.rename(os.path.join(outputDirectory, fileName),
                              os.path.join(outputDirectory, fileName.replace(
                                  "GLRLMFeatureMap_" + str(i+1) + ".nrrd", "GLRLMFeatureMap_" + self.RLFeatures[i] + ".nrrd")))

################################################################################
####################  Bone Texture Serializer Test #############################
################################################################################


class BoneTextureSerializerTest(ScriptedLoadableModuleTest):
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
