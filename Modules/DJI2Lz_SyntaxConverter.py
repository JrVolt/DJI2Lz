import re
import sys
import argparse
from pathlib import Path

def extract_bracket_data(text):
    # Generic bracket parser: extracts key:value pairs from all [...] blocks.
    # Handles multiple key:val entries inside a single bracket (e.g. "rel_alt: 0.000 abs_alt: 58.644").
    bracket_contents = re.findall(r'\[([^\]]+)\]', text)
    data = {}
    # keys to ignore (we'll drop these or keep minimal mapping)
    ignore_keys = set(['pp_vsync', 'pp_timestamp', 'pp_target', 'pp_current', 'pp_limit_ratio',
                       'pp_over_image_border', 'pp_warp_status', 'pp_imu_td', 'vsync', 'eis', 'shift_x', 'shift_y'])

    for content in bracket_contents:
        # find all key: value pairs within the bracket content
        pairs = re.findall(r'([A-Za-z0-9 _]+)\s*:\s*([^:\]]+?)(?=(?:[A-Za-z0-9 _]+\s*:)|$)', content)
        if pairs:
            for k, v in pairs:
                key = k.strip().lower().replace(' ', '_')
                val = v.strip().strip(',')
                if key in ignore_keys or key.startswith('pp_'):
                    # still capture absolute alt specially if it appears in ignored block
                    if key == 'abs_alt':
                        data['absolute_alt'] = re.search(r'([+-]?\d+(?:\.\d+)?)', val).group(1) if re.search(r'([+-]?\d+(?:\.\d+)?)', val) else val
                    continue

                # numeric extraction where appropriate
                if key in ('rel_alt', 'abs_alt', 'altitude'):
                    m = re.search(r'([+-]?\d+(?:\.\d+)?)', val)
                    if m:
                        data[key if key != 'abs_alt' else 'abs_alt'] = m.group(1)
                        if key == 'abs_alt':
                            data['absolute_alt'] = m.group(1)
                        continue

                data[key] = val
        else:
            # fallback: tokens separated by spaces, handle simple key:val tokens
            tokens = re.split(r'\s+', content)
            for tok in tokens:
                if ':' in tok:
                    k, v = tok.split(':', 1)
                    key = k.strip().lower().replace(' ', '_')
                    val = v.strip().strip(',')
                    if key in ignore_keys or key.startswith('pp_'):
                        if key == 'abs_alt':
                            data['absolute_alt'] = re.search(r'([+-]?\d+(?:\.\d+)?)', val).group(1) if re.search(r'([+-]?\d+(?:\.\d+)?)', val) else val
                        continue
                    if key in ('rel_alt', 'abs_alt', 'altitude'):
                        m = re.search(r'([+-]?\d+(?:\.\d+)?)', val)
                        if m:
                            data[key if key != 'abs_alt' else 'abs_alt'] = m.group(1)
                            if key == 'abs_alt':
                                data['absolute_alt'] = m.group(1)
                            continue
                    data[key] = val

    return data

def convert_to_standard_format(data):
    # Normalize fnum: accept floats (2.2) or encoded ints (280 -> 2.8)
    def normalize_fnum(val):
        if val is None:
            return 2.8
        try:
            f = float(str(val))
            if f >= 100:
                return f / 100.0
            return f
        except Exception:
            # try to extract number
            m = re.search(r'([0-9]+(?:\.[0-9]+)?)', str(val))
            if m:
                f = float(m.group(1))
                if f >= 100:
                    return f / 100.0
                return f
        return 2.8

    aperture = normalize_fnum(data.get('fnum'))

    shutter_speed = data.get('shutter', '1/100')
    if '/' in shutter_speed:
        parts = shutter_speed.split('/')
        if len(parts) == 2 and parts[0] == '1':
            try:
                shutter_value = float(parts[1])
                shutter_speed = f"{shutter_value:.1f}"
            except ValueError:
                shutter_speed = parts[1]

    iso = data.get('iso', '100')
    ev = data.get('ev', '0')
    longitude = data.get('longitude', '0')
    latitude = data.get('latitude', '0')
    # prefer relative altitude if available
    altitude = data.get('rel_alt') or data.get('altitude') or data.get('abs_alt') or '0'

    # map abs_alt to absolute_alt in returned data if present
    absolute_alt = data.get('abs_alt') or data.get('absolute_alt')

    try:
        altitude_value = float(altitude)
    except ValueError:
        altitude_value = 0.0

    gps_alt_value = altitude_value
    if absolute_alt is not None:
        try:
            gps_alt_value = float(absolute_alt)
        except ValueError:
            gps_alt_value = altitude_value

    standard_line = (
        f"F/{aperture:.1f}, SS {shutter_speed}, ISO {iso}, EV {ev}, "
        f"GPS ({longitude}, {latitude}, {gps_alt_value:.1f}), "
        f"D 0.00m, H {altitude_value:.1f}m, H.S 0.00m/s, V.S 0.00m/s"
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
        # join remaining lines and strip HTML tags
        joined = ' '.join(lines[2:])
        clean_line = re.sub(r'<[^>]+>', '', joined)
        telemetry_line = None

        # detect if there are bracketed key:value pairs and an ISO (robust to spaces around ':')
        bracket_contents = re.findall(r'\[([^\]]+)\]', clean_line)
        if bracket_contents and any(re.search(r'\biso\b', bc, re.I) for bc in bracket_contents):
            telemetry_line = clean_line
        
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
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(converted_blocks))
            if converted_blocks:
                f.write('\n\n')
    except PermissionError:
        # fallback: write to a known directory when the input folder is not writable
        fallback_dir = Path.home() / 'Desktop' / 'DJI2Lz_Converted'
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback = fallback_dir / f"{Path(output_file).stem}{Path(output_file).suffix}"
        with open(fallback, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(converted_blocks))
            if converted_blocks:
                f.write('\n\n')
        print(f"Permission denied writing to {output_file}; wrote to fallback: {fallback}")

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