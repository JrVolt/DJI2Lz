# Configuration file for layout of the frame generated by HUD_Generator

# Enabled Instruments
ENABLE_H_SPEEDOMETER = True
ENABLE_V_SPEEDOMETER = True
ENABLE_ALTIMETER = True
ENABLE_GPS = True
ENABLE_SATELLITE = True
ENABLE_RCDIST = True
ENABLE_PHOTO = True
ENABLE_WAYPOINT = True
ENABLE_STATS_DISTANCE = True
ENABLE_STATS_AREA = False
ENABLE_STATS_UNIT = False

# Turn off all unsupported instruments 
# 
# Set to TRUE to hide unsupported values
# Set to FALSE to show spoofed values

UNSUPPORTED = False 

if UNSUPPORTED == True:
    ENABLE_H_SPEEDOMETER = False
    ENABLE_V_SPEEDOMETER = False
    ENABLE_SATELLITE = False
    ENABLE_RCDIST = False

#[Global]
RESOLUTION = (3840, 2160)
LENS = ' Filter: CPL'
SUPPORTED_EXTENSIONS = ['.srt', '.csv']
FRAME_QUALITY = 100 
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' # >>>>> MUST (!!!!!) BE CHANGE TO MATCH YOUR OS <<<<<
FONT_SIZE = 60
SMALL_FONT_SIZE = 50
SMALLEST_FONT_SIZE = 40
EXTRA_SMALL_FONT_SIZE = 15
DRAW_TEXT_STROKE_WIDTH = 3
MARGIN = 100
LIGHT_STROKE_WIDTH = 2
STROKE_WIDTH = 4

COLORS = {
    'TEXT_PRIMARY': 'white',
    'TEXT_SECONDARY': 'blu',
    'TEXT_HIGHLIGHT': 'goldenrod',
    'TEXT_ALERT': 'red',
    'TEXT_INFO': 'limegreen',
    'STROKE': 'black',
    'SPEEDOMETER_PRIMARY': 'royalblue',
    'SPEEDOMETER_NUMBER': 'white',
    'SPEEDOMETER_SECONDARY': 'black',
    'SPEEDOMETER_NEEDLE': 'red',
    'SPEEDOMETER_INFO': 'silver',
    'ALTITUDE_PRIMARY': 'black',
    'ALTITUDE_BAR_MARKER': 'lightgrey',
    'ALTITUDE_BAR_FILL': 'coral',
    'ALTITUDE_BAR_ZERO': 'red',
    'ALTITUDE_BAR_CURRENT': 'firebrick',
    'ALTITUDE_TEXT': 'red',
    'STATS_AREA': '#8B4513',    # Disabled
    'STATS_DISTANCE': 'limegreen',
    'STATS_UNIT': '#CD853F',    # Disabled
    'WAYPOINT_POSITION': 'gold',
    'WAYPOINT_LINE': 'darkred',
    'WAYPOINT': 'dodgerblue',
    'WAYPOINT_STROKE': 'red',
    'WAYPOINT_BACKGROUND': (250, 250, 250),
    'WAYPOINT_OPACITY': 85,
    'WAYPOINT_GRID':'dimgray',
}

# Speedometer - Design 
SPEEDOMETER_RADIUS = 165 
SPEEDOMETER_THICKNESS = 4
HORIZONTAL_SPEEDOMETER = {
    'TICKS': 21,
    'RADIUS': 180
}

VERTICAL_SPEEDOMETER = {
    'TICKS': 21,
    'RADIUS': 180
}
NEEDLE_BASE_WIDTH = 15 
TICK_LONG = 7               # Thick tick marks
TICK_SHORT = 4              # Thin tick marks
DOUBLE_CIRCLE = 6           # Speedometer circle thickness

# Speedometer - Value 
MAX_HORIZONTAL_SPEED = 25   # Maximum horizontal speed (km/s)
MAX_VERTICAL_SPEED = 5      # Maximum vertical speed (m/s)
MIN_ALTITUDE = -20          # Minimum altitude (meters)
MAX_ALTITUDE = 750          # Maximum alt (meters)
CIRCLE_THICKNESS = 20
NUMBER_OFFSET = 70 

# Altitude Indicator 
ALTITUDE_MARK_WIDTH = 5
ALTITUDE_ZERO_LINE = 3
ALTITUDE_BAR_WIDTH = 100
ALTITUDE_BAR_HEIGHT = 1250
ALTITUDE_TEXT_OFFSET = 175 

# Waypoint Track
WAYPOINT_FRAME_STROKE = 4
WAYPOINT_BACKGROUND = (250, 250, 250)
WAYPOINT_OPACITY = 50
#DELETE ? #WAYPOINT_CONNECTION = 8

# WIP below

# Battery
BATTERY_THRESHOLDS = {
    'CELL_VOLTAGE': {
        'danger': 3.5,    # Red
        'warning': 3.7,   # Yellow
        'normal': 4.2     # Green
    },
    'TEMPERATURE': {
        'high': 40,       # Red
        'normal': 25      # Green
    }
}

# Signal power
SIGNAL_THRESHOLDS = {
    'strong': 80,     # Green
    'medium': 50,     # Yellow
    'weak': 30        # Red
}
