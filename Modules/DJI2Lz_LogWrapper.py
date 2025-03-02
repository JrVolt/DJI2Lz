# THIS MODULE RELAY ON www.github.com/lvauvillier/dji-log-parser all credit for the core bin to him
import os
import subprocess
import argparse
import pandas as pd
from pathlib import Path
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import DJI_API_KEY     # External config (DJI_API_KEY.Py)

class DJILogWrapper:
    def __init__(self, api_key=None):
        self.api_key = api_key or DJI_API_KEY.API_KEY
        self.binary_name = Path(__file__).parent / 'dji-log'
        if not self.api_key:
            raise ValueError("API key is required. Set API_KEY variable or provide it during initialization.")
        
        # Data to keep
        self.required_columns = [
            'CUSTOM.dateTime',
            'OSD.flyTime',
            'OSD.latitude',
            'OSD.longitude',
            'OSD.height',
            'OSD.heightMax',
            'OSD.vpsHeight',
            'OSD.altitude',
            'OSD.xSpeed',
            'OSD.xSpeedMax',
            'OSD.ySpeed',
            'OSD.ySpeedMax',
            'OSD.zSpeed',
            'OSD.zSpeedMax',
            'OSD.pitch',
            'OSD.roll',
            'OSD.yaw',
            'OSD.gpsNum',
            'OSD.gpsLevel',
            'OSD.droneType',
            'GIMBAL.mode',
            'GIMBAL.yaw',
            'RC.downlinkSignal',
            'RC.uplinkSignal',
            'BATTERY.chargeLevel',
            'BATTERY.voltage',
            'BATTERY.current',
            'BATTERY.currentCapacity',
            'BATTERY.fullCapacity',
            'BATTERY.cellVoltage1',
            'BATTERY.cellVoltage2',
            'BATTERY.cellVoltageDeviation',
            'BATTERY.temperature',
            'BATTERY.minTemperature',
            'BATTERY.maxTemperature'
        ]

    def _check_binary(self):
        try:
            subprocess.run([self.binary_name, '--version'], capture_output=True)
            return True
        except FileNotFoundError:
            raise Exception("dji-log binary not found in PATH")

    def simplify_csv(self, csv_path):
        try:
            log_csv = pd.read_csv(csv_path)
            missing_columns = [col for col in self.required_columns if col not in log_csv.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

            log_csv['CUSTOM.dateTime'] = pd.to_datetime(log_csv['CUSTOM.dateTime'], format='ISO8601')
            base_path = os.path.splitext(csv_path)[0]
            output_path = f"{base_path}.csv"
            log_csv[self.required_columns].to_csv(output_path, index=False)
            return output_path
            
        except Exception as e:
            raise Exception(f"Failed to simplify CSV: {str(e)}")

    def generate_output_filename(self, input_path, output_type='csv', simplified=False):
        """Generate appropriate output filename"""
        base_path = os.path.splitext(input_path)[0]
        suffix = "_Simplified" if simplified else "_Standard"
        return f"{base_path}{suffix}.{output_type}"

    def process_log(self, input_file, **kwargs):
        self._check_binary()
        input_file = input_file.strip("'")
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        base_dir = input_path.parent
        
        try:
            # Get output type and simplification flag
            output_type = next((k for k in kwargs.keys() if k != 'simplify'), 'csv')
            is_simplified = kwargs.get('simplify', False)
            
            # Generate output filename
            output_path = self.generate_output_filename(input_file, output_type, is_simplified)
            kwargs[output_type] = output_path
            
            print(f"\nProcessing: {os.path.basename(input_file)}")
            print(f"Output: {output_path}")
            
            # Run parser
            cmd = [str(self.binary_name)]
            if self.api_key:
                cmd.extend(['--api-key', self.api_key])
                
            if output_type == 'csv':
                cmd.extend(['-c', output_path])
                
            if output_type == 'kml':
                cmd.extend(['-k', output_path])
                
            if output_type == 'geojson':
                cmd.extend(['-g', output_path])
                
            if output_type == 'images':
                cmd.extend(['-i', output_path])
                
            if output_type == 'thumbnails':
                cmd.extend(['-t', output_path])
                
            if 'raw' in kwargs and kwargs['raw']:
                cmd.append('-r')
                
            cmd.append(str(input_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error processing log: {result.stderr}")
            
            if output_type == 'csv' and is_simplified:
                simplified_csv = self.simplify_csv(output_path)
                print(f"Simplified CSV saved to: {simplified_csv}")
                
            return result.stdout
        except Exception as e:
            raise Exception(f"Failed to process log: {str(e)}")

def main():
    print("DJI Log Processor")
    print("\n-----------------\n")
    
    input_file = input("Enter path to DJI log file: ").strip()
    api_key = None if DJI_API_KEY.API_KEY else input("Enter DJI API key: ").strip()
    output_type = input("Select output (csv/kml/geojson/images/thumbnails/json): ").strip().lower()
    
    if output_type == 'csv':
        simplify = input("Would you like to simplify the CSV output? (y/n): ").strip().lower() == 'y'
    else:
        simplify = False
    
    processor = DJILogWrapper(api_key)
    
    try:
        kwargs = {output_type: None, 'simplify': simplify}
        result = processor.process_log(input_file, **kwargs)
        print("\nCompleted!")
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()
