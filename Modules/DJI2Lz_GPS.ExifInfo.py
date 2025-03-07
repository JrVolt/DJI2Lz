# MetaExtract v1 

import subprocess
import json
import argparse
import os

def extract_metadata(filename, metadata_fields):
    try:
        result = subprocess.run(['exiftool', '-j', filename], capture_output=True, text=True, check=True)
        exif_data = json.loads(result.stdout)[0]
        
        extracted_data = {}
        for field in metadata_fields:
            if field in exif_data:
                extracted_data[field] = exif_data[field]
                print(f"Extracted {field}: {exif_data[field]}")
            else:
                print(f"{field}: Metadata not present")
                extracted_data[field] = "Metadata not present"
                
        return extracted_data

    except subprocess.CalledProcessError as e:
        print(f"Error extracting metadata: {e}")
        return {field: "Metadata not present" for field in metadata_fields}
    except json.JSONDecodeError as e:
        print(f"Error parsing ExifTool output: {e}")
        return {field: "Metadata not present" for field in metadata_fields}

def remove_metadata(filename, fields_to_remove):
    try:
        commands = ['-' + field + '=' for field in fields_to_remove]
        result = subprocess.run(['exiftool'] + commands + [filename], capture_output=True, text=True, check=True)
        print(f"Successfully removed metadata fields: {', '.join(fields_to_remove)}")
    except subprocess.CalledProcessError as e:
        print(f"Error removing metadata: {e}")

def save_metadata_to_file(metadata, filename):
    try:
        with open(filename, 'w') as f:
            for field, value in metadata.items():
                f.write(f"{field}: {value}\n")
        print(f"Metadata saved to {filename}")
    except Exception as e:
        print(f"Error saving metadata to file: {e}")

metadata_fields = [
    "Model",
    "GPSAltitude",
    "GPSLatitude",
    "GPSLongitude",
    "GPSPosition",
    "GPSLatitudeRef",
    "GPSLongitudeRef",
    "GPSAltitudeRef",
    "AbsoluteAltitude",
    "RelativeAltitude",
    "ShutterSpeedValue",
    "ApertureValue",
    "ExposureCompensation",
    "ExposureTime",
    "ExposureProgram",
    "ISO"
]

metadata_to_remove = [
    "Comment"
]

def validate_file(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist")
    
    ext = filename.lower().split('.')[-1]
    valid_extensions = {'mp4', 'dng', 'jpg', 'jpeg'}
    if ext not in valid_extensions:
        raise ValueError(f"Unsupported file extension. Supported types: {', '.join(valid_extensions)}")
    
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""
        DJI EXIF Extractor.

        Extract metadata from DJI files (MP4/JPG/DNG).
        If no arguments provided, will prompt for input file.

        Examples:
        %(prog)s input.MP4
        %(prog)s -o output.txt input.jpg
        %(prog)s --remove-sn input.dng
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input', nargs='?', type=str, help='Path to the input file')
    parser.add_argument('-f', '--fields', nargs='+', default=metadata_fields, help='Metadata fields to extract')
    parser.add_argument('-o', '--output', type=str, help='Output file name')
    parser.add_argument('--remove-sn', action='store_true', help='Remove serial number metadata')
    
    args = parser.parse_args()

    if not args.input:
        args.input = (input("Enter path to input file: ")).strip("'")

    try:
        validate_file(args.input)
        
        if args.output:
            output_filename = args.output
        else:
            out_path = os.path.dirname(args.input) or '.'
            base_name = os.path.splitext(os.path.basename(args.input))[0]
            output_filename = os.path.join(out_path, f"{base_name}_metadata.txt")

        extracted_data = extract_metadata(args.input, args.fields)
        save_metadata_to_file(extracted_data, output_filename)

        if args.remove_sn:
            remove_metadata(args.input, metadata_to_remove)
            
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        exit(1)