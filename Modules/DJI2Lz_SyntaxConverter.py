import re
import sys
import argparse
from pathlib import Path

def extract_bracket_data(text):
    patterns = {
        'iso': r'\[iso\s*:\s*(\d+)\]',
        'shutter': r'\[shutter\s*:\s*([^\]]+)\]',
        'fnum': r'\[fnum\s*:\s*(\d+)\]',
        'ev': r'\[ev\s*:\s*([+-]?\d+(?:\.\d+)?)\]',
        'latitude': r'\[latitude:\s*([^\]]+)\]',
        'longitude': r'\[longitude:\s*([^\]]+)\]',
        'altitude': r'\[altitude:\s*([^\]]+)\]',
        'ct': r'\[ct\s*:\s*(\d+)\]',
        'focal_len': r'\[focal_len\s*:\s*(\d+)\]'
    }
    
    data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = match.group(1).strip()
    
    return data

def convert_to_standard_format(data):
    aperture = float(data.get('fnum', '280')) / 100.0
    shutter_speed = data.get('shutter', '1/100')
    if '/' in shutter_speed:
        parts = shutter_speed.split('/')
        if len(parts) == 2 and parts[0] == '1':
            shutter_speed = parts[1]
    
    iso = data.get('iso', '100')
    ev = data.get('ev', '0')
    longitude = data.get('longitude', '0')
    latitude = data.get('latitude', '0')
    altitude = data.get('altitude', '0')
    
    # Below some spoofed value from the bracketed telemtry file.
    # Edit your preferred one [D, H.S, V.S also third value of GPS section that is for satellite count]
    standard_line = (
        f"F/{aperture:.1f}, SS {shutter_speed}, ISO {iso}, EV {ev}, "
        f"GPS ({longitude}, {latitude}, 0), " 
        f"D 0.00m, H {altitude}m, H.S 0.00m/s, V.S 0.00m/s" 
    )
    
    return standard_line

def convert_bracket_srt_to_standard(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    converted_blocks = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        
        if len(lines) < 3:
            continue
        
        subtitle_number = lines[0].strip()
        timestamp = lines[1].strip()
        telemetry_line = None
        
        for line in lines[2:]:
            clean_line = re.sub(r'<[^>]+>', '', line)
            if '[iso :' in clean_line and '[longitude:' in clean_line:
                telemetry_line = clean_line
                break
        
        if telemetry_line:
            bracket_data = extract_bracket_data(telemetry_line)
            
            if bracket_data:
                standard_telemetry = convert_to_standard_format(bracket_data)
                new_block = f"{subtitle_number}\n{timestamp}\n{standard_telemetry}"
                converted_blocks.append(new_block)
            else:
                converted_blocks.append(block)
        else:
            converted_blocks.append(block)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(converted_blocks))
        if converted_blocks:
            f.write('\n\n')

def process_path(input_path):
    if isinstance(input_path, str):
        input_path = Path(input_path.strip().strip("'").strip('"'))
    elif not isinstance(input_path, Path):
        input_path = Path(str(input_path))
    
    if input_path.is_file():
        if input_path.suffix.lower() == '.srt':
            output_path = input_path.parent / f"{input_path.stem}_Converted{input_path.suffix}"
            try:
                convert_bracket_srt_to_standard(input_path, output_path)
                print(f"Converted: {output_path}")
            except Exception as e:
                print(f"Error converting {input_path}: {e}")
    
    elif input_path.is_dir():
        srt_files = list(input_path.rglob('*.srt')) + list(input_path.rglob('*.SRT'))
        input_path = input_path.resolve()
        if not srt_files:
            print(f"No SRT files found in: {input_path}")
            return
            
        print(f"\nFound {len(srt_files)} SRT files to convert")
        for srt_file in sorted(srt_files):
            output_path = srt_file.parent / f"{srt_file.stem}_Converted{srt_file.suffix}"
            try:
                convert_bracket_srt_to_standard(srt_file, output_path)
                print(f"Converted: {output_path}")
            except Exception as e:
                print(f"Error converting {srt_file}: {e}")
    else:
        print(f"Invalid path: {input_path}")

def main():
    parser = argparse.ArgumentParser(description='Convert bracketed SRT telemetry to standard format')
    parser.add_argument('input', nargs='?', help='Input SRT file or folder')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.input:
        print("\nBracket SRT Format Converter")
        print("-" * 30)
        args.input = input("\nInput SRT file or directory path: ")
    
    input_path = Path(args.input.rstrip('/')).resolve()
    
    if not input_path.exists():
        print(f"Error: Path '{input_path}' does not exist")
        sys.exit(1)
        
    try:
        process_path(input_path)
        print("\nConversion complete!")
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()