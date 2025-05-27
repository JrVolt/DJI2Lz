#Ver 4.5.2 / Waypoint meh / "n/a" fix / short clip hovering error for waypoint 
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

        draw_text_with_stroke(draw, (self.center[0] - 100, text_y), ms, SMALL_FONT, stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)              # Value in m/s
        draw_text_with_stroke(draw, (self.center[0] - 150, text_y + 100), kmh, SMALL_FONT, stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)       # Value in Km/h

def get_output_path(input_srt):
    base_dir = os.path.dirname(input_srt)
    processed_dir = os.path.join(base_dir, "Processed")
    srt_name = os.path.splitext(os.path.basename(input_srt))[0]
    return os.path.join(processed_dir, srt_name)

def fix_telemetry_line(line):
    original = line
    fixed = line.replace('n/a', '0.0')
    if original != fixed:
        print(f"\n Warning: Spoofed values in telemetry:")
        differences = []
        if 'n/a' in original:
            parts = original.split(',')
            for part in parts:
                if 'n/a' in part:
                    differences.append(part.strip())
        print(f"- Replaced 'n/a' with '0.0' in: {', '.join(differences)}")
    return fixed

def parse_telemetry_line(telemetry_line):
    fixed_line = fix_telemetry_line(telemetry_line.strip())
    
    pattern = (
        r"F/(?P<aperture>\d+\.\d+), SS (?P<shutter_speed>\d+\.\d+), ISO (?P<iso>\d+), "
        r"EV (?P<ev>[+-]?\d+(\.\d+)?)"
        r"(?:, DZOOM (?P<dzoom>\d+\.\d+))?"  # Make DZOOM optional
        r", GPS \((?P<longitude>[^,]+), "
        r"(?P<latitude>[^,]+), (?P<altitude>[^)]+)\), D (?P<distance>[^,m]+)(?:m)?, "
        r"H (?P<height>-?\d+\.\d+)m?, H\.S (?P<horizontal_speed>-?\d+\.\d+)m/s, "
        r"V\.S (?P<vertical_speed>-?\d+\.\d+)m/s"
    )
    
    match = re.match(pattern, fixed_line)
    if not match:
        print(f"Warning: Unable to parse telemetry: {fixed_line}")
        return None

    try:
        return {
            "aperture": float(match.group("aperture")),
            "shutter": float(match.group("shutter_speed")),
            "iso": int(match.group("iso")),
            "ev": float(match.group("ev")),
            "dzoom": float(match.group("dzoom")) if match.group("dzoom") is not None else 1.0,  # Default to 1.0 if not present
            "lat": float(match.group("latitude")),
            "lon": float(match.group("longitude")),
            "alt": float(match.group("altitude")),
            "distance": float(match.group("distance")),
            "height": float(match.group("height")),
            "h_speed": float(match.group("horizontal_speed")),
            "v_speed": float(match.group("vertical_speed"))
        }
    except (ValueError, TypeError) as e:
        print(f"Error converting values: {str(e)}\nLine: {fixed_line}")
        return None

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

    draw.line([x, zero_y, x + bar_width, zero_y], fill=LayoutConfig.COLORS['ALTITUDE_BAR_ZERO'], width=LayoutConfig.ALTITUDE_ZERO_LINE) # Zero line (0mt altitude)

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
    #DIOMERDA
    draw_text_with_stroke(draw, ( x - 100, text_y + 1450 ), f"{height:.1f}m", FONT, text_color=LayoutConfig.COLORS['TEXT_HIGHLIGHT'])
    # draw_text_with_stroke(draw, (x - LayoutConfig.ALTITUDE_TEXT_OFFSET + 75 , text_y), f"{height:.1f}m", FONT, text_color=LayoutConfig.COLORS['TEXT_HIGHLIGHT'])

def draw_text_with_stroke(draw, pos, text, font, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'], stroke_color=LayoutConfig.COLORS['STROKE'], stroke_width=LayoutConfig.DRAW_TEXT_STROKE_WIDTH):
    x, y = pos
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
            
    draw.text(pos, text, font=font, fill=text_color)

def draw_current_position(draw, x, y, alt):
    marker_size = 10
    draw.ellipse([x - marker_size, y - marker_size, x + marker_size, y + marker_size], outline=LayoutConfig.COLORS["WAYPOINT_POSITION"], width=2)
    draw.line([x - marker_size, y, x + marker_size, y], fill=LayoutConfig.COLORS["WAYPOINT_POSITION"], width=2)
    draw.line([x, y - marker_size, x, y + marker_size], fill=LayoutConfig.COLORS["WAYPOINT_POSITION"], width=2)

def draw_flight_statistics(draw, current_index, grid_scale, enable_config):
    if enable_config['area'] or enable_config['distance']:
        width, height = path_tracker.get_current_dimensions(current_index)
        distance = path_tracker.get_current_distance(current_index)
    
    if enable_config['area']:
        draw_text_with_stroke(draw, enable_config['area_pos'], f"Area: {width:.1f}m × {height:.1f}m", SMALL_FONT, text_color=LayoutConfig.COLORS["STATS_AREA"], stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)
    
    if enable_config['distance']:
        draw_text_with_stroke(draw, enable_config['distance_pos'],f"Dist: {distance:.1f}m", SMALL_FONT, text_color=LayoutConfig.COLORS["STATS_DISTANCE"], stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)
    
    if enable_config['unit']:
        draw_text_with_stroke(draw, enable_config['unit_pos'], f"Unit: {grid_scale}m", SMALL_FONT, text_color=LayoutConfig.COLORS["STATS_UNIT"], stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)

def draw_waypoints(draw, center, scaled_points, current_index):
    square_size = 500
    
    min_x = center[0] - square_size // 2
    max_x = center[0] + square_size // 2
    min_y = center[1] - square_size // 2
    max_y = center[1] + square_size // 2
    padding = 25

    draw.rectangle(
        [min_x, min_y, max_x, max_y],
        fill=(
            LayoutConfig.WAYPOINT_BACKGROUND[0],
            LayoutConfig.WAYPOINT_BACKGROUND[1],
            LayoutConfig.WAYPOINT_BACKGROUND[2],
            int(255 * LayoutConfig.WAYPOINT_OPACITY / 100)
        )
    )

    # Line scaling
    grid_scale = path_tracker.calculate_grid_scale()
    grid_divisions = 8
    cell_size = (square_size - 2 * padding) // grid_divisions

    for i in range(grid_divisions + 1):
        x = min_x + padding + (i * cell_size)
        y = min_y + padding + (i * cell_size)
        
        draw.line([(x, min_y + padding), (x, max_y - padding)],
                 fill=LayoutConfig.COLORS["WAYPOINT_GRID"], width=1)
        draw.line([(min_x + padding, y), (max_x - padding, y)],
                 fill=LayoutConfig.COLORS["WAYPOINT_GRID"], width=1)

    # Draw flight path and statistics
    if path_tracker.points:
        if len(scaled_points) > 1:
            path_points = path_tracker.points[:current_index + 1]
            
            box_width = max_x - min_x - 2 * padding
            box_height = max_y - min_y - 2 * padding
            
            scaled_path_points = []
            
            # Handle cases where min and max are equal (no movement)
            lon_range = path_tracker.max_lon - path_tracker.min_lon
            lat_range = path_tracker.max_lat - path_tracker.min_lat
            
            # If no movement, center the point
            if lon_range == 0 or lat_range == 0:
                x = min_x + padding + (box_width / 2)
                y = min_y + padding + (box_height / 2)
                scaled_path_points.append((x, y))
            else:
                for point in path_points:
                    lat, lon, _ = point
                    x_norm = (lon - path_tracker.min_lon) / lon_range
                    y_norm = (lat - path_tracker.min_lat) / lat_range
                    
                    x = min_x + padding + (x_norm * box_width)
                    y = min_y + padding + ((1 - y_norm) * box_height)  # Invert Y
                    scaled_path_points.append((x, y))
            
            # Draw path
            if len(scaled_path_points) > 1:
                draw.line(scaled_path_points,
                         fill=LayoutConfig.COLORS["WAYPOINT_LINE"],
                         width=2)

            # Draw current position
            if current_index < len(path_points):
                lat, lon, alt = path_points[current_index]
                
                # Use the same logic as above for consistency
                if lon_range == 0 or lat_range == 0:
                    x = min_x + padding + (box_width / 2)
                    y = min_y + padding + (box_height / 2)
                else:
                    x_norm = (lon - path_tracker.min_lon) / lon_range
                    y_norm = (lat - path_tracker.min_lat) / lat_range
                    x = min_x + padding + (x_norm * box_width)
                    y = min_y + padding + ((1 - y_norm) * box_height)
                
                draw_current_position(draw, x, y, alt)

    # Draw border
    draw.rectangle([min_x, min_y, max_x, max_y],
                  outline=LayoutConfig.COLORS["WAYPOINT_STROKE"],
                  width=LayoutConfig.WAYPOINT_FRAME_STROKE)

class PathTracker:
    def __init__(self, simplification_threshold=5.0):
        self.points = []
        self.simplified_points = []
        self.min_lat = float('inf')
        self.max_lat = float('-inf')
        self.min_lon = float('inf')
        self.max_lon = float('-inf')
        self.min_alt = float('inf')
        self.max_alt = float('-inf')
        self.threshold = simplification_threshold
        self.earth_radius = 6371000  # Earth's radius in meters
        self.total_distance = 0.0    # Track total flight distance
        self.current_width = 0.0    # Add these new variables
        self.current_height = 0.0
        self.current_distance = 0.0

    def add_point(self, lat, lon, alt):
        """Add a new waypoint and update bounds"""
        self.points.append((lat, lon, alt))
        
        # Update bounds
        self.min_lat = min(self.min_lat, lat)
        self.max_lat = max(self.max_lat, lat)
        self.min_lon = min(self.min_lon, lon)
        self.max_lon = max(self.max_lon, lon)
        self.min_alt = min(self.min_alt, alt)
        self.max_alt = max(self.max_alt, alt)
        
        # Update total distance
        if len(self.points) >= 2:
            self.total_distance += self.distance_between_points(
                self.points[-2], self.points[-1])
        
        self.simplify_path()

    def simplify_path(self):
        """Simplify path using Douglas-Peucker algorithm"""
        if len(self.points) < 3:
            self.simplified_points = self.points[:]
            return

        def point_line_distance(point, start, end):
            if start == end:
                return self.distance_between_points(point, start)
            
            lat, lon, _ = point
            lat1, lon1, _ = start
            lat2, lon2, _ = end
            
            # Calculate perpendicular distance
            nom = abs((lat2-lat1) * (lon1-lon) - (lat1-lat) * (lon2-lon1))
            denom = math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2)
            return nom/denom if denom != 0 else 0

        def douglas_peucker(points, epsilon):
            if len(points) <= 2:
                return points
                
            dmax = 0
            index = 0
            
            for i in range(1, len(points) - 1):
                d = point_line_distance(points[i], points[0], points[-1])
                if d > dmax:
                    index = i
                    dmax = d
                    
            if dmax > epsilon:
                results1 = douglas_peucker(points[:index + 1], epsilon)
                results2 = douglas_peucker(points[index:], epsilon)
                return results1[:-1] + results2
            else:
                return [points[0], points[-1]]
                
        self.simplified_points = douglas_peucker(self.points, self.threshold)

    def get_flight_dimensions(self):
        """Calculate flight dimensions in meters"""
        center_lat = (self.min_lat + self.max_lat) / 2
        width = self.distance_between_points(
            (center_lat, self.min_lon, 0),
            (center_lat, self.max_lon, 0))
        height = self.distance_between_points(
            (self.min_lat, self.min_lon, 0),
            (self.max_lat, self.min_lon, 0))
        return width, height

    def get_screen_position(self, lat, lon, screen_width, screen_height, padding=50):
        """Convert GPS coordinates to screen position"""
        usable_width = screen_width - 2 * padding
        usable_height = screen_height - 2 * padding
        
        # Calculate normalized position (0-1)
        x_norm = (lon - self.min_lon) / (self.max_lon - self.min_lon) if self.max_lon != self.min_lon else 0.5
        y_norm = (lat - self.min_lat) / (self.max_lat - self.min_lat) if self.max_lat != self.min_lat else 0.5
        
        # Convert to screen coordinates
        x = padding + (x_norm * usable_width)
        y = padding + ((1 - y_norm) * usable_height)  # Invert Y since screen coords go down
        
        return int(x), int(y)

    def distance_between_points(self, point1, point2):
        lat1, lon1, _ = point1
        lat2, lon2, _ = point2
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return self.earth_radius * c

    def calculate_grid_scale(self):
        width, height = self.get_flight_dimensions()
        max_dim = max(width, height)
        
        # Scale steps (meters)
        scales = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        
        # Find  scale
        for scale in scales:
            if max_dim / 8 < scale:
                return scale
        
        return scales[-1]

    def get_scaled_points(self, box_rect):
        min_x, min_y, max_x, max_y = box_rect
        padding = 25
        
        usable_width = max_x - min_x - 2 * padding
        usable_height = max_y - min_y - 2 * padding
        
        scaled_points = []
        
        # Handle single point or no movement case
        if len(self.points) == 1 or (self.max_lon == self.min_lon and self.max_lat == self.min_lat):
            x = min_x + padding + (usable_width / 2)  # Center point horizontally
            y = min_y + padding + (usable_height / 2)  # Center point vertically
            return [(x, y, self.points[0][2])] if self.points else []
            
        for lat, lon, alt in self.points:
            # Normalize coordinates (0-1) with safety checks
            x_norm = 0.5 if self.max_lon == self.min_lon else (lon - self.min_lon) / (self.max_lon - self.min_lon)
            y_norm = 0.5 if self.max_lat == self.min_lat else (lat - self.min_lat) / (self.max_lat - self.min_lat)
            
            # Transform to box coordinates
            x = min_x + padding + (x_norm * usable_width)
            y = min_y + padding + ((1 - y_norm) * usable_height)  # Invert Y
            
            scaled_points.append((x, y, alt))
        
        return scaled_points

    def get_current_dimensions(self, current_index):
        if current_index < 0 or not self.points:
            return 1.0, 1.0  # Return minimal dimensions instead of zero
            
        current_points = self.points[:current_index + 1]
        if not current_points:
            return 1.0, 1.0
            
        min_lat = min(p[0] for p in current_points)
        max_lat = max(p[0] for p in current_points)
        min_lon = min(p[1] for p in current_points)
        max_lon = max(p[1] for p in current_points)
        
        # If no movement (hovering), return minimal dimensions
        if min_lat == max_lat or min_lon == max_lon:
            return 1.0, 1.0
        
        center_lat = (min_lat + max_lat) / 2
        width = self.distance_between_points(
            (center_lat, min_lon, 0),
            (center_lat, max_lon, 0))
        height = self.distance_between_points(
            (min_lat, min_lon, 0),
            (max_lat, min_lon, 0))
            
        return width, height

    def get_current_distance(self, current_index):
        if current_index < 1:
            return 0.0
            
        distance = 0.0
        for i in range(current_index):
            distance += self.distance_between_points(
                self.points[i], self.points[i + 1])
        return distance

path_tracker = PathTracker(simplification_threshold=5.0)

def process_block(block, srt_name, output_dir, scaled_points, current_index):
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
                create_frame(parsed_data, output_frame_path, scaled_points, current_index)
                return True, index
            
        return False, f"Invalid block format: {lines[0] if lines else 'unknown'}"
    
    except Exception as e:
        print(f"\n << Process block error: {str(e)}")         #Debug
        return False, f"Error processing block {lines[0] if lines else 'unknown'}: {str(e)}"

def create_frame(data, output_frame_path, scaled_points, current_index):  # Instruments layout positions and configuration
    if not data:
        print("Warning: Empty data, skipping frame")
        return None
    
    rawlat = data['lat']
    rawlon = data['lon']

    def decimal_to_dms(decimal, is_latitude=True):
        if decimal == 0:
            if is_latitude:
                return "0°00'00\"N"
            return "0°00'00\"E"
            
        direction = 'N' if decimal >= 0 and is_latitude else 'S' if is_latitude else 'E' if decimal >= 0 else 'W'
        decimal = abs(decimal)
        degrees = int(decimal)
        minutes = int((decimal - degrees) * 60)
        seconds = int(((decimal - degrees) * 60 - minutes) * 60)
        
        return f"{degrees}°{minutes:02d}'{seconds:02d}\"{direction}"

    lat_str = decimal_to_dms(rawlat, is_latitude=True)
    lon_str = decimal_to_dms(rawlon, is_latitude=False)
    
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
    sat_range = (15 ,20)
    if sat_range[0] <= int(satellite[:-2]) <= sat_range[1]:
        sat_color = "gold" 
    elif int(satellite[:-2]) > sat_range[1]:
        sat_color = "limegreen"
    else:
        sat_color = "red"

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
        draw_altitude_bar(draw, data["height"], (right_margin - 100, LayoutConfig.RESOLUTION[1] // 2 - 950))                                                                                     # Altitude Bar
    
    if LayoutConfig.ENABLE_GPS == True :
        draw_text_with_stroke(draw, (center_x - 300, bottom_margin - 50), clean_coordinates, FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'])      # GPS Data [Formatted]
        # draw_text_with_stroke(draw, (bottom_margin + 300, center_x + 100), raw_coordinates, FONT,  stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'])

    if LayoutConfig.ENABLE_SATELLITE == True :
        draw_text_with_stroke(draw, (center_x + 600, bottom_margin - 50), "Sat: " + satellite, FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=sat_color)                               # Satellite count
    
    if LayoutConfig.ENABLE_RCDIST == True :
        draw_text_with_stroke(draw, (left_margin, top_margin), rc_dist, FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_INFO'])                               # RC Distance
    
    if LayoutConfig.ENABLE_PHOTO == True :
        draw_text_with_stroke(draw, (center_x - 300, top_margin), phexif, SMALL_FONT, stroke_width=LayoutConfig.STROKE_WIDTH, text_color=LayoutConfig.COLORS['TEXT_PRIMARY'])                    # Photo Data
    
    if LayoutConfig.ENABLE_WAYPOINT == True :
        draw_waypoints(draw, (right_margin - 240, bottom_margin - 250 ), scaled_points, current_index)  # Waypoints

    if LayoutConfig.ENABLE_STATS_AREA:
        width, height = path_tracker.get_current_dimensions(current_index)
        draw_text_with_stroke(draw, (left_margin + 800, top_margin + 100), f"Area: {width:.1f}m × {height:.1f}m", SMALL_FONT, text_color=LayoutConfig.COLORS["STATS_AREA"], stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)
    
    if LayoutConfig.ENABLE_STATS_DISTANCE:
        distance = path_tracker.get_current_distance(current_index)
        draw_text_with_stroke(draw, (left_margin, top_margin + 100), f"T.Dist: {distance:.1f}m", SMALL_FONT, text_color=LayoutConfig.COLORS["STATS_DISTANCE"], stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)
    
    if LayoutConfig.ENABLE_STATS_UNIT:
        draw_text_with_stroke(draw,(left_margin + 2000, top_margin + 100), f"Unit: {path_tracker.calculate_grid_scale()}m",SMALL_FONT, text_color=LayoutConfig.COLORS["STATS_UNIT"], stroke_width=LayoutConfig.LIGHT_STROKE_WIDTH)

    frame.save(output_frame_path, optimize=True, quality=LayoutConfig.FRAME_QUALITY)
    # print(f"Exported in: {output_frame_path}")        # Too slow in multithread // LoL // Kept for fun :)

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
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                telemetry_line = lines[2]
                parsed_data = parse_telemetry_line(telemetry_line)
                if parsed_data:
                    path_tracker.add_point(parsed_data['lat'], parsed_data['lon'], parsed_data['alt'])
        
        box_rect = (0, 0, LayoutConfig.RESOLUTION[0], LayoutConfig.RESOLUTION[1])
        scaled_points = path_tracker.get_scaled_points(box_rect)
        
        num_processes = max(1, multiprocessing.cpu_count() - 2)

        print(f"\rProcessing frames: 0/{len(blocks)}", end="", flush=True)
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = {
                executor.submit(process_block, block, srt_name, output_dir, scaled_points, i): block 
                for i, block in enumerate(blocks)
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