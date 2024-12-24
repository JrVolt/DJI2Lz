#Ver Chckpoint 4.4 / Multithread - Waypoint semi-ugly / Colored Satellite count // Increase Speedometer Amplitude
import argparse
import math
import os
import re
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFile
from math import sqrt
import chardet
import time

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import LayoutConfig     # External config (LayoutConfig.Py)

import multiprocessing
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    FONT = ImageFont.truetype(LayoutConfig.FONT_PATH, LayoutConfig.FONT_SIZE)
    SMALL_FONT = ImageFont.truetype(LayoutConfig.FONT_PATH, LayoutConfig.SMALL_FONT_SIZE)
    SMALLEST_FONT = ImageFont.truetype(LayoutConfig.FONT_PATH, LayoutConfig.SMALLEST_FONT_SIZE)
    EXTRA_SMALL_FONT = ImageFont.truetype(LayoutConfig.FONT_PATH, LayoutConfig.EXTRA_SMALL_FONT_SIZE)
except OSError:
    print(f"Warning: Could not load font from {LayoutConfig.FONT_PATH}, using default font")
    FONT = ImageFont.load_default()
    SMALL_FONT = ImageFont.load_default()
    SMALLEST_FONT = ImageFont.load_default()
    EXTRA_SMALL_FONT = ImageFont.load_default()


waypoints_history = []

class SpeedometerDrawer:

    def __init__(self, center, radius, max_speed, settings, allow_negative=False):
        self.center = center
        self.radius = radius
        self.max_speed = max_speed
        self.allow_negative = allow_negative        # Negative value in speedometer
        self.start_angle = 220                      # Speedometer Left Limit
        self.end_angle = -40                        # Speedometer Right Limit
        self.settings = settings    
        self.ticks = self.settings['TICKS']
        
    def draw_number(self, draw, angle, number):
        rad_angle = math.radians(angle)
        radius_offset = self.radius + LayoutConfig.NUMBER_OFFSET
        x = self.center[0] + radius_offset * math.cos(rad_angle)
        y = self.center[1] - radius_offset * math.sin(rad_angle)
        rotation = angle - 90 if angle <= 180 else angle + 90
        text = str(number)
        bbox = SMALLEST_FONT.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw rotated text
        for dx in range(-LayoutConfig.STROKE_WIDTH, LayoutConfig.STROKE_WIDTH + 1):
            for dy in range(-LayoutConfig.STROKE_WIDTH, LayoutConfig.STROKE_WIDTH + 1):
                draw.text((x - text_width/2 + dx, y - text_height/2 + dy), text, font=SMALL_FONT, fill="black")
        draw.text((x - text_width/2, y - text_height/2), text, font=SMALL_FONT, fill=LayoutConfig.COLORS['SPEEDOMETER_NUMBER'])

    def draw(self, draw, speed, label):
        for offset in [0, 4]:
            draw.ellipse([
                self.center[0] - self.radius - offset,
                self.center[1] - self.radius - offset,
                self.center[0] + self.radius + offset,
                self.center[1] + self.radius + offset
            ], outline=LayoutConfig.COLORS['SPEEDOMETER_PRIMARY'], width=LayoutConfig.DOUBLE_CIRCLE)

        # Draw tick
        tick_length = 20
        for i in range(self.ticks * 2):
            angle = self.start_angle - (i * (self.start_angle - self.end_angle) / (self.ticks * 2 - 1))
            rad_angle = math.radians(angle)
            
            inner_x = self.center[0] + (self.radius - tick_length) * math.cos(rad_angle)
            inner_y = self.center[1] - (self.radius - tick_length) * math.sin(rad_angle)
            outer_x = self.center[0] + self.radius * math.cos(rad_angle)
            outer_y = self.center[1] - self.radius * math.sin(rad_angle)
            
            tick_width = LayoutConfig.TICK_LONG if i % 2 == 0 else LayoutConfig.TICK_SHORT
            tick_color = LayoutConfig.COLORS['SPEEDOMETER_PRIMARY'] if i % 2 == 0 else LayoutConfig.COLORS['SPEEDOMETER_SECONDARY']
            draw.line([inner_x, inner_y, outer_x, outer_y], fill=tick_color, width=tick_width)

        # Draw numbers
        if self.allow_negative:
            for i in range(self.ticks):
                if i % 2 == 0:
                    angle = self.start_angle - (i * (self.start_angle - self.end_angle) / (self.ticks - 1))
                    speed_val = int(-self.max_speed + (i * 2 * self.max_speed / (self.ticks - 1)))
                    self.draw_number(draw, angle, speed_val)
        else:
            for i in range(self.ticks):
                if i % 2 == 0:
                    angle = self.start_angle - (i * (self.start_angle - self.end_angle) / (self.ticks - 1))
                    speed_val = int(i * self.max_speed / (self.ticks - 1))
                    self.draw_number(draw, angle, speed_val)

        # Draw needle
        needle_angle = self.start_angle - (
            ((speed + self.max_speed) / (2 * self.max_speed) if self.allow_negative 
             else min(speed, self.max_speed) / self.max_speed)) * (self.start_angle - self.end_angle)
        
        needle_rad = math.radians(needle_angle)
        needle_length = self.radius - 40
        x_end = self.center[0] + needle_length * math.cos(needle_rad)
        y_end = self.center[1] - needle_length * math.sin(needle_rad)

        draw.line([self.center[0], self.center[1], x_end, y_end], fill=LayoutConfig.COLORS['STROKE'], width=LayoutConfig.NEEDLE_BASE_WIDTH)
        draw.line([self.center[0], self.center[1], x_end, y_end], fill=LayoutConfig.COLORS['TEXT_PRIMARY'], width=LayoutConfig.SPEEDOMETER_THICKNESS)

        # Speed Value
        ms = f"{speed:.1f} m/s"
        kmh = f"[ {speed * 3.6:.1f} km/h ]"
        text_y = self.center[1] + self.radius + 50

        draw_text_with_stroke(draw, (self.center[0] - 100, text_y), ms, FONT, stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)              # Value in m/s
        draw_text_with_stroke(draw, (self.center[0] - 180, text_y + 100), kmh, FONT, stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)       # Value in Km/h

class WaypointBounds:

    def __init__(self, waypoints):
        self.min_lat = min(wp[0] for wp in waypoints)
        self.max_lat = max(wp[0] for wp in waypoints)
        self.min_lon = min(wp[1] for wp in waypoints)
        self.max_lon = max(wp[1] for wp in waypoints)
    
    def update(self, waypoints):
        self.min_lat = min(self.min_lat, min(wp[0] for wp in waypoints))
        self.max_lat = max(self.max_lat, max(wp[0] for wp in waypoints))
        self.min_lon = min(self.min_lon, min(wp[1] for wp in waypoints))
        self.max_lon = max(self.max_lon, max(wp[1] for wp in waypoints))

def get_output_path(input_srt):
    base_dir = os.path.dirname(input_srt)
    processed_dir = os.path.join(base_dir, "Processed")
    srt_name = os.path.splitext(os.path.basename(input_srt))[0]
    return os.path.join(processed_dir, srt_name)

def parse_telemetry_line(telemetry_line):
    pattern = (
        r"F/(?P<aperture>\d+\.\d+), SS (?P<shutter_speed>\d+\.\d+), ISO (?P<iso>\d+), "
        r"EV (?P<ev>[+-]?\d+(\.\d+)?), DZOOM (?P<dzoom>\d+\.\d+), GPS \((?P<longitude>-?\d+\.\d+), "
        r"(?P<latitude>-?\d+\.\d+), (?P<altitude>-?\d+(\.\d+)?)\), D (?P<distance>\d+\.\d+)m, "
        r"H (?P<height>-?\d+\.\d+)m, H\.S (?P<horizontal_speed>-?\d+\.\d+)m/s, "
        r"V\.S (?P<vertical_speed>-?\d+\.\d+)m/s"
    )
    
    match = re.match(pattern, telemetry_line.strip())
    if not match:
        print(f"Warning: Invalid telemetry format in line: {telemetry_line.strip()}")
        return None

    return {
        "aperture": float(match.group("aperture")),
        "shutter": float(match.group("shutter_speed")),
        "iso": int(match.group("iso")),
        "ev": float(match.group("ev")),
        "dzoom": float(match.group("dzoom")),
        "lat": float(match.group("latitude")),
        "lon": float(match.group("longitude")),
        "alt": float(match.group("altitude")),
        "distance": float(match.group("distance")),
        "height": float(match.group("height")),
        "h_speed": float(match.group("horizontal_speed")),
        "v_speed": float(match.group("vertical_speed"))
    }

def draw_altitude_bar(draw, height, pos):
    x, y = pos
    bar_width = LayoutConfig.ALTITUDE_BAR_WIDTH
    bar_height = LayoutConfig.ALTITUDE_BAR_HEIGHT
    altitude_range = LayoutConfig.MAX_ALTITUDE - LayoutConfig.MIN_ALTITUDE
    zero_height = bar_height * (abs(LayoutConfig.MIN_ALTITUDE) / altitude_range)
    zero_y = y + bar_height - zero_height
    text_y = y - 150

    # Fill indicator
    height_ratio = (height - LayoutConfig.MIN_ALTITUDE) / altitude_range
    fill_height = height_ratio * bar_height
    fill_y = y + bar_height - fill_height
    draw.rectangle([x, fill_y, x + bar_width, y + bar_height], fill=LayoutConfig.COLORS['ALTITUDE_BAR_FILL'])

    draw.line([x, zero_y, x + bar_width, zero_y], fill=LayoutConfig.COLORS['ALTITUDE_BAR_ZERO'], width=LayoutConfig.ALTITUDE_ZERO_LINE) # Zero line (0mt altitude indicator)

    # Height markers
    marker_step = 100
    for h in range(LayoutConfig.MIN_ALTITUDE, LayoutConfig.MAX_ALTITUDE + 1, marker_step):
        marker_ratio = (h - LayoutConfig.MIN_ALTITUDE) / altitude_range
        marker_y = y + bar_height - (marker_ratio * bar_height)
        max_y = y - 30  # Top position
        draw.line([x, marker_y, x + bar_width, marker_y], fill=LayoutConfig.COLORS['ALTITUDE_BAR_MARKER'], width=LayoutConfig.ALTITUDE_MARK_WIDTH)
        draw_text_with_stroke(draw, (x - LayoutConfig.ALTITUDE_TEXT_OFFSET, marker_y - 30), f"{h} m", SMALLEST_FONT, stroke_width=2)                    # Actual altitude
        draw_text_with_stroke(draw, (x - LayoutConfig.ALTITUDE_TEXT_OFFSET, max_y), f"{LayoutConfig.MAX_ALTITUDE} m", SMALLEST_FONT, stroke_width=2)    # Altitude Mark

    # Altitude Indicator
    for offset in [0, 4]:
        draw.rectangle([
            x - offset, y - offset,
            x + bar_width + offset, y + bar_height + offset
        ], outline=LayoutConfig.COLORS['ALTITUDE_PRIMARY'], width=7)

    # Current Altitude indicator
    draw.line([x, fill_y, x + bar_width, fill_y], LayoutConfig.COLORS['ALTITUDE_BAR_CURRENT'], width=5)
    draw_text_with_stroke(draw, (x - LayoutConfig.ALTITUDE_TEXT_OFFSET + 75 , text_y - 100), f"{height:.1f}m", FONT, text_color=LayoutConfig.COLORS['TEXT_HIGHLIGHT'])

def draw_text_with_stroke(draw, pos, text, font, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'], stroke_color=LayoutConfig.COLORS['STROKE'], stroke_width=LayoutConfig.DRAW_TEXT_STROKE_WIDTH):
    x, y = pos
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
            
    draw.text(pos, text, font=font, fill=text_color)

def draw_waypoints(draw, waypoints, center, bounds=None):
    # Fixed square dimensions
    square_size = 1000
    min_x = center[0] - square_size//2
    max_x = center[0] + square_size//2
    min_y = center[1] - square_size//2
    max_y = center[1] + square_size//2
    padding = 50  # Padding to keep points inside

    # Draw background and frame
    draw.rectangle(
        [min_x, min_y, max_x, max_y],
        fill=(
            LayoutConfig.WAYPOINT_BACKGROUND[0],
            LayoutConfig.WAYPOINT_BACKGROUND[1],
            LayoutConfig.WAYPOINT_BACKGROUND[2],
            int(255 * LayoutConfig.WAYPOINT_OPACITY / 100)
        )
    )
    draw.rectangle(
        [min_x, min_y, max_x, max_y],
        fill=None,
        outline=LayoutConfig.COLORS["WAYPOINT_STROKE"],
        width=LayoutConfig.WAYPOINT_FRAME_STROKE
    )

    if len(waypoints) <= 1:
        return bounds

    # Calculate bounds once and reuse
    if bounds is None:
        bounds = WaypointBounds(waypoints)

    # Scale to fit inside square with padding
    lat_range = bounds.max_lat - bounds.min_lat
    lon_range = bounds.max_lon - bounds.min_lon
    
    # Prevent division by zero
    scale_factor = min(
        (square_size - 2*padding) / max(lon_range, 0.0000001),
        (square_size - 2*padding) / max(lat_range, 0.0000001)
    )

    scaled_waypoints = []
    for lat, lon, alt in waypoints:
        x = min_x + padding + (lon - bounds.min_lon) * scale_factor
        y = max_y - padding - (lat - bounds.min_lat) * scale_factor
        scaled_waypoints.append((int(x), int(y), alt))

    # Draw waypoint lines
    for i in range(len(scaled_waypoints) - 1):
        draw.line(
            [scaled_waypoints[i][:2], scaled_waypoints[i + 1][:2]],
            fill=LayoutConfig.COLORS["WAYPOINT_LINE"],
            width=2
        )

    # Draw waypoints
    for x, y, alt in scaled_waypoints:
        draw.ellipse(
            (x - LayoutConfig.WAYPOINT_RADIUS, y - LayoutConfig.WAYPOINT_RADIUS,
             x + LayoutConfig.WAYPOINT_RADIUS, y + LayoutConfig.WAYPOINT_RADIUS),
            fill=LayoutConfig.COLORS["WAYPOINT"],
            outline=None
        )
        draw.text(
            (x + LayoutConfig.WAYPOINT_OFFSET_TEXT, y - LayoutConfig.WAYPOINT_OFFSET_TEXT),
            f"{alt:.1f}",
            font=EXTRA_SMALL_FONT,
            fill=LayoutConfig.COLORS["ALTITUDE_TEXT"]
        )

    return bounds

def filter_close_waypoints(waypoints, min_distance=0.0001):
    filtered = [waypoints[0]]  # Always include the first waypoint
    for wp in waypoints[1:]:
        prev_wp = filtered[-1]
        dist = sqrt((wp[0] - prev_wp[0])**2 + (wp[1] - prev_wp[1])**2)
        if dist >= min_distance:
            filtered.append(wp)
    return filtered

def calculate_average_distance(waypoints):
    if len(waypoints) < 2:
        return 1  # Default scale factor for small data
    distances = []
    for i in range(len(waypoints) - 1):
        lat1, lon1, _ = waypoints[i]
        lat2, lon2, _ = waypoints[i + 1]
        # Simple Euclidean distance for scaling
        distances.append(sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2))
    return sum(distances) / len(distances) if distances else 1

def process_block(block, srt_name, output_dir):
    try:
        if not block.strip():
            print(f"Empty block detected") # Debug
            return False, "Empty block"
            
        lines = block.strip().split('\n')
        # print(f"<< Block lines: {lines}")  # Debug

        if len(lines) >= 3:
            index = lines[0]
            telemetry_line = lines[2]
            parsed_data = parse_telemetry_line(telemetry_line)
            
            if parsed_data is None:         # Debug
                print(f"<< Failed to parse telemetry: {telemetry_line}") # Debug
                return False, f"Failed telemetry parse: {telemetry_line}"

            if parsed_data:
                frame_name = f"HUD_{srt_name}_{index.zfill(6)}.png"
                output_frame_path = os.path.join(output_dir, frame_name)
                create_frame(parsed_data, output_frame_path)
                return True, index
            
        return False, f"Invalid block format: {lines[0] if lines else 'unknown'}"
    
    except Exception as e:
        print(f"Process block error: {str(e)}")         #Debug
        return False, f"Error processing block {lines[0] if lines else 'unknown'}: {str(e)}"

def create_frame(data, output_frame_path):  # Instruments layout positions and configuration
    global waypoints_history

    current_waypoint = (data['lat'], data['lon'], data['alt'])
    waypoints_history.append(current_waypoint)

    if not data:
        print("Warning: Empty data, skipping frame")
        return None
    
    rawlat = data['lat']
    rawlon = data['lon']

    def decimal_to_dms(coord):
        degrees = int(coord)
        minutes = int((abs(coord) - abs(degrees)) * 60)
        seconds = round(((abs(coord) - abs(degrees)) * 60 - minutes) * 60, 2)
        return degrees, minutes, seconds

    lat_deg, lat_min, lat_sec = decimal_to_dms(rawlat)
    lon_deg, lon_min, lon_sec = decimal_to_dms(rawlon)
    
    lat_dir = "N" if rawlat >= 0 else "S"
    lon_dir = "E" if rawlon >= 0 else "W"
    
    lat_str = f"{abs(lat_deg)}° {lat_min}' {lat_sec}\" {lat_dir}"
    lon_str = f"{abs(lon_deg)}° {lon_min}' {lon_sec}\" {lon_dir}"
    
    frame = Image.new("RGBA", LayoutConfig.RESOLUTION, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # Grid Layout
    left_margin = LayoutConfig.MARGIN
    right_margin = LayoutConfig.RESOLUTION[0] - LayoutConfig.MARGIN
    center_x = LayoutConfig.RESOLUTION[0] // 2
    center_y = LayoutConfig.RESOLUTION[1] // 2 
    top_margin = LayoutConfig.MARGIN
    bottom_margin = LayoutConfig.RESOLUTION[1] - LayoutConfig.MARGIN

    raw_coordinates = f"GPS: ({data['lat']:.4f}, {data['lon']:.4f}, {data['alt']:.1f}m)"                            # GPS Data [RAW] - Disabled below
    clean_coordinates = f"{lat_str}, {lon_str}"                                                                     # GPS Data [Formatted]
    satellite = f"{data['alt']:.1f}"
    phexif = (f"F/{data['aperture']:.1f}  SS 1/{data['shutter']:.0f}  ISO {data['iso']}  EV {data['ev']:+.1f} {LayoutConfig.LENS}")     # Photo Data
    rc_dist = f"RC Dist: {data['distance']:03.1f}m"                                                                 # RC Distance

    # Satellite Count


    # sat_color = "gold" 
    sat_range = (15 ,20)
    if sat_range[0] <= int(satellite[:-2]) <= sat_range[1]:
        sat_color = "gold" 
    elif int(satellite[:-2]) > sat_range[1]:
        sat_color = "limegreen"
    else:
        sat_color = "red"
    
    # print(sat_colors)

    # Speedometers
    h_speed_pos = (left_margin + 280, bottom_margin - 400)                               # Horizontal Speedometer
    v_speed_pos = (left_margin + 1000  , bottom_margin - 400)                            # Vertical Speedometer
    h_speedometer = SpeedometerDrawer(h_speed_pos, LayoutConfig.SPEEDOMETER_RADIUS, LayoutConfig.MAX_HORIZONTAL_SPEED, LayoutConfig.HORIZONTAL_SPEEDOMETER, allow_negative=False)
    v_speedometer = SpeedometerDrawer(v_speed_pos, LayoutConfig.SPEEDOMETER_RADIUS, LayoutConfig.MAX_VERTICAL_SPEED, LayoutConfig.VERTICAL_SPEEDOMETER, allow_negative=True)

    if LayoutConfig.ENABLE_H_SPEEDOMETER == True :
        h_speedometer.draw(draw, data["h_speed"], "Horizontal Speed")                                                                                                                            # Horizontal Speedometer
        draw_text_with_stroke(draw, (left_margin + 150 , bottom_margin), "Horizontal", SMALL_FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['SPEEDOMETER_INFO'])   # Horizontal Label                                                                                                                 # Vertical Speedometer
    
    if LayoutConfig.ENABLE_V_SPEEDOMETER == True :
        v_speedometer.draw(draw, data["v_speed"], "Vertical Speed")                                                                                                                              # Vertical Speedometer
        draw_text_with_stroke(draw, (left_margin + 900, bottom_margin), "Vertical", SMALL_FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['SPEEDOMETER_INFO'])      # Vertical Label

    if LayoutConfig.ENABLE_ALTIMETER == True :
        draw_altitude_bar(draw, data["height"], (right_margin - 100, LayoutConfig.RESOLUTION[1] // 2 - 700))                                                                                     # Altitude Bar
    
    if LayoutConfig.ENABLE_GPS == True :
        draw_text_with_stroke(draw, (bottom_margin, center_x + 100), clean_coordinates, FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'])      # GPS Data [Formatted]
        # draw_text_with_stroke(draw, (bottom_margin + 300, center_x + 100), raw_coordinates, FONT,  stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'])

    if LayoutConfig.ENABLE_SATELLITE == True :
        draw_text_with_stroke(draw, (right_margin - 300, center_x + 100), "Sat: " + satellite, FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=sat_color)                               # Satellite count
    
    if LayoutConfig.ENABLE_RCDIST == True :
        draw_text_with_stroke(draw, (left_margin, top_margin), rc_dist, FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_INFO'])                               # RC Distance
    
    if LayoutConfig.ENABLE_PHOTO == True :
        draw_text_with_stroke(draw, (center_x - 300, top_margin), phexif, SMALL_FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'])                    # Photo Data
    
    if LayoutConfig.ENABLE_WAYPOINT == True :
        draw_waypoints(draw, waypoints_history, (center_x + 200, center_y))                                                                                                                      # Waypoints

    frame.save(output_frame_path, optimize=True, quality=LayoutConfig.FRAME_QUALITY)
    # print(f"Exported in: {output_frame_path}")        # Too slow in multithread // LoL

    return frame

def create_frames_from_srt(input_srt):
    output_dir = get_output_path(input_srt)
    srt_name = os.path.splitext(os.path.basename(input_srt))[0]
    os.makedirs(output_dir, exist_ok=True)
    failed_blocks = []
    frames_processed = 0
    bounds = None  # Store bounds globally
    
    try:
        with open(input_srt, "r", encoding="utf-8") as file:
            content = file.read()
        blocks = [block for block in content.split('\n\n') if block.strip()]
        num_processes = max(1, multiprocessing.cpu_count() - 2)

        print(f"\rProcessing frames: 0/{len(blocks)}", end="", flush=True)
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = {
                executor.submit(process_block, block, srt_name, output_dir): block 
                for block in blocks
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    success, msg = future.result()
                    if success:
                        frames_processed += 1
                    print(f"\rProcessing frames: {i+1}/{len(blocks)}", end="", flush=True)
                except Exception as e:
                    failed_blocks.append(futures[future])

        print(f"\nExported {frames_processed} frames successfully")
        if failed_blocks:
            print(f"Failed blocks: {len(failed_blocks)}")

    except Exception as e:
        raise RuntimeError(f"Processing failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="DJI Telemetry Overlay Generator")
    parser.add_argument('input', nargs='?', help='Input SRT file or directory')
    parser.add_argument('-o', '--output', help='Output directory')
    args = parser.parse_args()
    

    try:
        if not args.input:
            args.input = input("\nEnter path to SRT file or directory: \n>> ").strip()

        if not os.path.exists(args.input):
            sys.exit("Error: Input path does not exist.")

        if os.path.isfile(args.input):
            if not any(args.input.lower().endswith(ext) for ext in LayoutConfig.SUPPORTED_EXTENSIONS):
                sys.exit(f"Unsupported | Only: {', '.join(LayoutConfig.SUPPORTED_EXTENSIONS)}")
            
            print ("\n[   Processing...   ]\n")
            print(f"\n>> Processing single file: {args.input}")
            create_frames_from_srt(args.input)
            
        elif os.path.isdir(args.input):
            print ("\n[   Processing...   ]\n")
            print(f"\n >> Processing directory: {args.input}")
            processed_files = 0
            error_files = 0
            
            for root, _, files in os.walk(args.input):
                srt_files = [f for f in files if f.lower().endswith('.srt')]
                
                if srt_files:
                    print(f"\n>> Found {len(srt_files)} SRT files in {root}")
                    
                    for file in srt_files:
                        srt_path = os.path.join(root, file)
                        print(f"\n>> Processing: {srt_path}")
                        
                        try:
                            create_frames_from_srt(srt_path)
                            processed_files += 1
                        except Exception as e:
                            error_files += 1
                            print(f"Error processing {srt_path}: {str(e)}")
            
            if error_files:
                print(f"- Failed to process: {error_files} files")
        
        print("\nAll operations completed \n\n Bye \n")
        
    except KeyboardInterrupt:
        print("\n Operation aborted :( )")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)




if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()