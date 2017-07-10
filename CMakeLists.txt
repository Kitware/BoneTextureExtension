cmake_minimum_required(VERSION 2.8.9)

project(BoneTextureExtension)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/BoneTextureExtension")
set(EXTENSION_CATEGORY "Quantification")
set(EXTENSION_CONTRIBUTORS "Jean-Baptiste VIMORT (Kitware Inc.)")
set(EXTENSION_DESCRIPTION "This extensions contain several modules that can be used to compute feature maps of N-Dimensional images using well-known texture analysis methods. Key Features: 8 coocurrence textural features: energy, entropy, correlation, inertia, cluster Shade... / 10 run length textural features: run length emphasis, grey level non uniformity, run length non uniformity, low grey level long run emphasis... / Input configurable parameters: locality of the texture, offset directions for co-ocurrence and run length computation, the number of bins for the intensity histograms, and the intensity range or the range of run lengths.")


set(EXTENSION_ICONURL "https://www.slicer.org/w/images/0/09/Logo-BoneTextureExtension.png")
set(EXTENSION_SCREENSHOTURLS "https://www.slicer.org/w/images/7/70/BoneTextureExtension-Slicer.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

set(EXTENSION_BUILD_SUBDIRECTORY BoneTextureExtension-build)
set(EXTENSION_STATUS Beta)

set(SUPERBUILD_TOPLEVEL_PROJECT BoneTextureExtension)

find_package(Git REQUIRED)
find_package(Subversion REQUIRED)
#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
mark_as_superbuild(Slicer_DIR)
mark_as_superbuild(PYTHON_EXECUTABLE)
mark_as_superbuild(PYTHON_INCLUDE_DIR)
mark_as_superbuild(PYTHON_LIBRARY)

#-----------------------------------------------------------------------------
option(${EXTENSION_NAME}_SUPERBUILD "Build ${EXTENSION_NAME} and the projects it depends on." ON)
mark_as_advanced(${EXTENSION_NAME}_SUPERBUILD)
if(${EXTENSION_NAME}_SUPERBUILD)
  include("${CMAKE_CURRENT_SOURCE_DIR}/SuperBuild.cmake")
  return()
endif()

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(ComputeGLCMFeatures)
add_subdirectory(ComputeGLRLMFeatures)
add_subdirectory(ComputeGLCMFeatureMaps)
add_subdirectory(ComputeGLRLMFeatureMaps)
add_subdirectory(BoneTexture)
add_subdirectory(BoneTextureSerializer)
add_subdirectory(SeparateVectorImage)

#-----------------------------------------------------------------------------
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${CMAKE_BINARY_DIR};${EXTENSION_NAME};ALL;/")
include(${Slicer_EXTENSION_CPACK})
