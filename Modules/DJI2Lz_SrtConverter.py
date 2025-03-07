import argparse
import logging
import os
import sys
import re

def convert_srt_to_csv(in_file, out_file, debug=False):
    pattern = (
        r"F/(?P<aperture>\d+\.\d+), SS (?P<shutter_speed>\d+\.\d+), ISO (?P<iso>\d+), "
        r"EV (?P<ev>[+-]?\d+(\.\d+)?), DZOOM (?P<dzoom>\d+\.\d+), GPS \((?P<longitude>[^,]+), "
        r"(?P<latitude>[^,]+), (?P<altitude>[^)]+)\), D (?P<distance>[^,m]+)(?:m)?, "
        r"H (?P<height>-?\d+\.\d+)m?, H\.S (?P<horizontal_speed>-?\d+\.\d+)m/s, "
        r"V\.S (?P<vertical_speed>-?\d+\.\d+)m/s"
    )
    
    with open(out_file, 'w') as csv_file:
        # header = "Time,Aperture,ShutterSpeed,ISO,EV,Zoom,Longitude,Latitude,Altitude,Distance,Height,HorizontalSpeed,VerticalSpeed\n"
        header = "2Lz.Time,2Lz.Aperture,2Lz.ShutterSpeed,2Lz.ISO,2Lz.EV,2Lz.Zoom,2Lz.Longitude,2Lz.Latitude,2Lz.RcDist,2Lz.Distance,2Lz.Height,2Lz.HorizontalSpeed,2Lz.VerticalSpeed\n"
        csv_file.write(header)
        
        with open(in_file) as f:
            content = f.read()

        blocks = re.split(r'\n\n+', content)
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
                
            timestamp_line = lines[1]
            timestamp_parts = timestamp_line.split(' --> ')[0].strip().split(',')[0].split(':')
            time = ':'.join(timestamp_parts)
            
            date = ""
            for line in lines[2:]:
                if line.startswith('HOME'):
                    home_parts = line.split(' ')
                    if len(home_parts) > 1:
                        date = home_parts[1]
                    break
            
            for line in lines[2:]:
                match = re.search(pattern, line)
                if match:
                    data = match.groupdict()
                    
                    values = [
                        date,
                        time,
                        data.get('aperture', ''),
                        data.get('shutter_speed', ''),
                        data.get('iso', ''),
                        data.get('ev', ''),
                        data.get('dzoom', ''),
                        data.get('longitude', ''),
                        data.get('latitude', ''),
                        data.get('altitude', ''),
                        data.get('distance', ''),
                        data.get('height', ''),
                        data.get('horizontal_speed', ''),
                        data.get('vertical_speed', '')
                    ]
                    
                    csv_file.write(','.join(values) + '\n')
                    logging.debug(f"Processed data: {data}")
    
    logging.info(f'CSV output written to {out_file}')

def main():
    parser = argparse.ArgumentParser(description='DJI SRT to CSV Converter - Extract telemetry data from DJI drone subtitle files')
    parser.add_argument('--input', '-i', help='Input SRT file or directory containing SRT files', nargs='+', dest='input_paths')
    parser.add_argument('--output', '-o', help='Output CSV file (for single file conversion) or directory (for batch conversion)')
    parser.add_argument('--debug', '-d', help='Enable debug logging', action='store_true')
    parser.add_argument('--version', '-v', action='version', version='DJI SRT Converter 1.0')
    args = parser.parse_args()
    # set_logging_level(args.debug)
    input_files = []
    
    if args.input_paths:
        for path in args.input_paths:
            if os.path.isdir(path):
                found_files = sorted([os.path.join(path, f) for f in os.listdir(path) if f.endswith('.srt')])
                if not found_files:
                    logging.warning(f"No SRT files found in: {path}")
                input_files.extend(found_files)
            elif os.path.isfile(path) and path.endswith('.srt'):
                input_files.append(path)
            else:
                logging.warning(f"Invalid SRT file or directory: {path}")
    else:
        try:
            user_input = input("\nInput SRT file or directory containing SRT files\n>> ")
            input_strings = user_input.strip("'").split()
            paths = [string.strip("'") for string in input_strings]
            
            for path in paths:
                if os.path.isdir(path):
                    found_files = sorted([os.path.join(path, f) for f in os.listdir(path) if f.endswith('.srt')])
                    if not found_files:
                        logging.warning(f"No SRT files found in: {path}")
                    input_files.extend(found_files)
                elif os.path.isfile(path) and path.endswith('.srt'):
                    input_files.append(path)
                else:
                    logging.warning(f"Invalid SRT file or directory: {path}")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(0)
    
    if not input_files:
        logging.error("No valid SRT files found")
        sys.exit(1)
    
    if args.output and os.path.isdir(args.output):
        output_dir = args.output
        single_output_file = None
    elif args.output and len(input_files) == 1:
        output_dir = None
        single_output_file = args.output
    elif args.output and len(input_files) > 1:
        output_dir = args.output
        os.makedirs(output_dir, exist_ok=True)
        single_output_file = None
    else:
        output_dir = None
        single_output_file = None
    
    for in_file in input_files:
        if single_output_file:
            out_file = single_output_file
        elif output_dir:
            out_file = os.path.join(output_dir, os.path.basename(os.path.splitext(in_file)[0]) + '.csv')
        else:
            out_file = os.path.splitext(in_file)[0] + '.csv'
            
        logging.info(f'Converting {in_file} to {out_file}')
        convert_srt_to_csv(in_file, out_file, args.debug)
    
    if len(input_files) > 1:
        logging.info(f'Batch conversion complete. {len(input_files)} files converted.')

if __name__ == "__main__":
    main()