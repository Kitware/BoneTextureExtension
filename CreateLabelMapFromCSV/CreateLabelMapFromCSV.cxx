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
#include <fstream>
#include <string>
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

#include "CreateLabelMapFromCSVCLP.h"

namespace
{

template< typename TPixel >
int DoIt( int argc, char * argv[] )
{

    PARSE_ARGS;

    const unsigned int Dimension = 3;

    typedef TPixel                                       PixelType;
    typedef itk::Image< PixelType, Dimension >           InputImageType;
    typedef itk::ImageFileReader< InputImageType >       ReaderType;
    typedef itk::Image< unsigned int, Dimension >        OutImageType;
    typedef itk::ImageFileWriter< OutImageType >         WriterType;

    typename ReaderType::Pointer reader = ReaderType::New();
    reader->SetFileName( inputVolume );
    reader->Update();

    OutImageType::Pointer output = OutImageType::New();
    output->SetRegions(reader->GetOutput()->GetRequestedRegion());
    output->SetOrigin(reader->GetOutput()->GetOrigin());
    output->SetDirection(reader->GetOutput()->GetDirection());
    output->SetSpacing(reader->GetOutput()->GetSpacing());
    output->Allocate();

    typename OutImageType::IndexType pixelIndex;

    std::ifstream inputFile;
    inputFile.open(inputFileName.c_str(), std::ios::in);

    std::string line;
    while(std::getline(inputFile, line))
    {

        std::istringstream s(line);
        std::string field;

        getline(s, field,',');
        pixelIndex[0] = std::atoi(field.c_str());
        getline(s, field,',');
        pixelIndex[1] = std::atoi(field.c_str());
        getline(s, field,',');
        pixelIndex[2] = std::atoi(field.c_str());
        getline(s, field,',');

        std::string label = field.substr(0, field.size()-1);

        if(label == Label1.c_str())
        {
            output->SetPixel (pixelIndex, 1);
        }
        else if(label == Label2.c_str())
        {
            output->SetPixel (pixelIndex, 2);
        }
        else if(label == Label3.c_str())
        {
            output->SetPixel (pixelIndex, 3);
        }
        else if(label == Label4.c_str())
        {
            output->SetPixel (pixelIndex, 4);
        }
        else if(label == Label5.c_str())
        {
            output->SetPixel (pixelIndex, 5);
        }
        else
        {
            output->SetPixel (pixelIndex, 0);
        }

    }
    typename WriterType::Pointer writer = WriterType::New();
    writer->SetFileName( outputLabeMap );
    writer->SetInput( output );
    writer->Update();

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
