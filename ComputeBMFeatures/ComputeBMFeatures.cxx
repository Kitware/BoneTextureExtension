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

#include "itkBoneMorphometryFeaturesFilter.h"

#include "itkPluginUtilities.h"

#include "ComputeBMFeaturesCLP.h"

namespace
{

template< typename TPixel >
int DoIt( int argc, char * argv[] )
{
  PARSE_ARGS;

  const unsigned int Dimension = 3;

  typedef TPixel                                 PixelType;
  typedef itk::Image< PixelType, Dimension >     InputImageType;

  typedef itk::ImageFileReader< InputImageType > ReaderType;
  typename ReaderType::Pointer reader = ReaderType::New();
  reader->SetFileName( inputVolume );
  reader->Update();

  typedef itk::BoneMorphometryFeaturesFilter<InputImageType, InputImageType> FilterType;
  typename FilterType::Pointer filter = FilterType::New();
  filter->SetInput(reader->GetOutput());

  if(inputMask != "")
  {
    typename ReaderType::Pointer maskReader = ReaderType::New();
    maskReader->SetFileName( inputMask );
    maskReader->Update();
    filter->SetMaskImage(maskReader->GetOutput());
  }

  filter->SetThreshold( threshold );
  filter->Update();

  std::ofstream rts;
  rts.open(returnParameterFile.c_str() );
  rts << "outputVector = "<<filter->GetBVTV()<<","
      <<filter->GetTbTh()<<","
     <<filter->GetTbSp()<<","
    <<filter->GetTbN()<<","
   <<filter->GetBSBV()<< std::endl;
  rts<<"BVTV = "<< filter->GetBVTV() << std::endl;
  rts<<"TbTh = "<< filter->GetTbTh() << std::endl;
  rts<<"TbSp = "<< filter->GetTbSp() << std::endl;
  rts<<"TbN = "<< filter->GetTbN() << std::endl;
  rts<<"BSBV = "<< filter->GetBSBV() << std::endl;

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
//      case itk::ImageIOBase::FLOAT:
//        return DoIt< float >( argc, argv );
//        break;
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
