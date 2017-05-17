cmake_minimum_required(VERSION 2.8.9)

project(BoneTextureExtension)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "TODO")
set(EXTENSION_CATEGORY "Examples")
set(EXTENSION_CONTRIBUTORS "Jean-Baptiste VIMORT (Kitware Inc.)")
set(EXTENSION_DESCRIPTION "TODO")
set(EXTENSION_ICONURL "TODO")
set(EXTENSION_SCREENSHOTURLS "TODO")
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
add_subdirectory(BoneTexture)

#-----------------------------------------------------------------------------
set(CPACK_INSTALL_CMAKE_PROJECTS "${CPACK_INSTALL_CMAKE_PROJECTS};${CMAKE_BINARY_DIR};${EXTENSION_NAME};ALL;/")
include(${Slicer_EXTENSION_CPACK})
