/*=========================================================================
 *
 *  Copyright Insight Software Consortium
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0.txt
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *=========================================================================*/


// Use an anonymous namespace to keep class types and function names
// from colliding when module is used as shared object module.  Every
// thing should be in an anonymous namespace except for the module
// entry point, e.g. main()
//

#include "itkImageFileReader.h"
#include "itkImageFileWriter.h"
#include "itkFloatingPointExceptions.h"
#include "itkImage.h"
#include "itkVector.h"
#include "itkNeighborhood.h"
#include "itkMetaDataDictionary.h"
#include "itkMetaDataObject.h"

#include "itkVectorIndexSelectionCastImageFilter.h"

#include "itkPluginUtilities.h"

#include "SeparateVectorImageCLP.h"

// Feature name lists for GLCM, GLRM, and BM
std::vector<std::string> GLCMFeatures = {"Energy", "Entropy", "Correlation", "InverseDifferenceMoment", 
  "Inertia", "ClusterShade", "ClusterProminence", "HaralickCorrelation"};

std::vector<std::string> RLFeatures = {"ShortRunEmphasis", "LongRunEmphasis", 
"GreyLevelNonuniformity", "RunLengthNonuniformity", 
"LowGreyLevelRunEmphasis", "HighGreyLevelRunEmphasis", 
"ShortRunLowGreyLevelEmphasis", "ShortRunHighGreyLevelEmphasis", 
"LongRunLowGreyLevelEmphasis", "LongRunHighGreyLevelEmphasis"};

std::vector<std::string> BMFeatures = {"BoneVolumeDensity", "TrabecularThickness", 
"TrabecularSeparation", "TrabecularNumber", "BoneSurfaceDensity"};

namespace
{

template< typename TPixel >
int DoIt( int argc, char * argv[] )
{
  PARSE_ARGS;

  const unsigned int Dimension = 3;

  typedef TPixel                                       PixelType;
  typedef itk::VectorImage< PixelType, Dimension >     InputImageType;
  typedef itk::Image< PixelType, Dimension >           OutputImageType;
  
  typedef itk::ImageFileReader< InputImageType > ReaderType;
  typename ReaderType::Pointer reader = ReaderType::New();
  reader->SetFileName( inputVolume );
  reader->Update();

  unsigned int VectorComponentDimension = reader->GetOutput()->GetNumberOfComponentsPerPixel();

  typedef itk::VectorIndexSelectionCastImageFilter< InputImageType, OutputImageType > IndexSelectionType;
  typename IndexSelectionType::Pointer indexSelectionFilter = IndexSelectionType::New();
  indexSelectionFilter->SetInput( reader->GetOutput() );

  // Select the appropriate feature name list based on VectorComponentDimension
  std::vector<std::string> featureNames;

  if (VectorComponentDimension == 8) {
    featureNames = GLCMFeatures;
  } else if (VectorComponentDimension == 10) {
    featureNames = RLFeatures;
  } else if (VectorComponentDimension == 5) {
    featureNames = BMFeatures;
  } else {
      for (unsigned int i = 1; i <= VectorComponentDimension; ++i) {
        std::ostringstream ss;
        ss << i;
        featureNames.push_back(ss.str());
      }
  }

  for( unsigned int i = 0; i < VectorComponentDimension; i++ )
    {
    indexSelectionFilter->SetIndex(i);

    // Create and set up a writer
    typedef itk::ImageFileWriter< OutputImageType > WriterType;
    typename WriterType::Pointer writer = WriterType::New();
    std::string outputFilename = outputFileBaseName.c_str();;
    std::string suffix = featureNames[i];
    writer->SetFileName( outputFilename + "_" + suffix + ".nrrd" );
    writer->SetInput( indexSelectionFilter->GetOutput() );

    writer->Update();
    }



  return EXIT_SUCCESS;
}

} // end of anonymous namespace

int main( int argc, char * argv[] )
{
  PARSE_ARGS;

  itk::ImageIOBase::IOPixelType     inputPixelType;
  itk::ImageIOBase::IOComponentType inputComponentType;
  itk::FloatingPointExceptions::Enable();
  itk::FloatingPointExceptions::SetExceptionAction( itk::FloatingPointExceptions::ABORT );

  try
    {

    itk::GetImageType(inputVolume, inputPixelType, inputComponentType);

    switch( inputComponentType )
      {
      case itk::ImageIOBase::UCHAR:
        return DoIt< int >( argc, argv );
        break;
      case itk::ImageIOBase::USHORT:
        return DoIt< int >( argc, argv );
        break;
      case itk::ImageIOBase::SHORT:
        return DoIt< int >( argc, argv );
        break;
      case itk::ImageIOBase::FLOAT:
        return DoIt< float >( argc, argv );
        break;
      case itk::ImageIOBase::INT:
        return DoIt< int >( argc, argv );
        break;
      default:
        std::cerr << "Unknown input image pixel component type: "
          << itk::ImageIOBase::GetComponentTypeAsString( inputComponentType )
          << std::endl;
        return EXIT_FAILURE;
        break;
      }
    }
  catch( itk::ExceptionObject & excep )
    {
    std::cerr << argv[0] << ": exception caught !" << std::endl;
    std::cerr << excep << std::endl;
    return EXIT_FAILURE;
    }
  return EXIT_SUCCESS;
}
