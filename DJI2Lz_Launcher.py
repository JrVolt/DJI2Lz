import os
import subprocess
from pathlib import Path
import signal
import shlex

class GracefulExit(Exception):
    pass


def signal_handler(signum, frame):
    raise GracefulExit()

def clean_path(path):
    return path.strip().strip("'").strip('"')

def get_file_input(file_path, check_mp4=True):
    path = Path(file_path)
    
    if path.is_file():
        if check_mp4:
            if path.suffix.lower() == '.mp4':
                return str(path), str(path.with_suffix('.srt'))
            print("The provided file is not an MP4. Please try again.")
            return None, None
        return str(path), str(path)
    elif path.is_dir():
        return str(path), str(path)
    
    print("File or directory not found. Please try again.")
    return None, None

def process_video(file_path, mode):
    try:
        input_path = clean_path(file_path)
        video_path, srt_path = get_file_input(input_path, check_mp4=(mode in [1, 3]))
        
        if not video_path:
            return
            
        if mode == 1:
            run_script("DJI2Lz-SrtExtractor.py", video_path)
        elif mode == 2:
            run_script("DJI2Lz-HUD_Generator.py", video_path)
        elif mode == 3:
            if run_script("DJI2Lz-SrtExtractor.py", video_path):
                import time
                time.sleep(1)
                
                if srt_path and Path(srt_path).exists():
                    run_script("DJI2Lz-HUD_Generator.py", srt_path)
                else:
                    print("\nError: SRT file was not generated at expected path:", srt_path)
    except (KeyboardInterrupt, GracefulExit):
        print("\nProcess interrupted by user.")
        raise

def print_help():
    help_text = """
    DJI Video and Photo Processing Unified Tool
    
    Available Options:
    1) Extract SRT Telemetry - Extracts telemetry data from MP4 videos
    2) Generate HUD Frame - Creates HUD overlay from SRT telemetry
    3) Extract + Generate HUD
    4) Extract EXIF - Gets photo metadata
    5) Merge multiple SRT from long flight and genereta a continuous sequence.
    6) Extract flight log from dji_logfile.txt
    7) Convert DJI .srt in 2Lz.csv 
    
    Usage:
    - Select desired option and provide needed file 
    """
    print(help_text)

def run_script(script_name, input_paths):
    script_dir = Path(__file__).resolve().parent
    script_path = script_dir / "Modules" / script_name

    if not script_path.exists():
        print(f"\nError: {script_path} not found.")
        return False

    if isinstance(input_paths, str):
        input_paths = [input_paths]

    command = ["python3", str(script_path)] + input_paths
    # print(f"\n>> Running command: {' '.join(command)}\n")

    env = os.environ.copy()
    env['PYTHONPATH'] = str(script_dir)

    process = None
    try:
        process = subprocess.Popen(
            command,
            env=env
        )
        process.wait()
        return process.returncode == 0
    except (KeyboardInterrupt, GracefulExit):
        if process:
            print("\n\nOperation aborted. Cleaning up...")
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        raise
    except subprocess.CalledProcessError as e:
        print(f"\nError running script: {e}")
        return False

def run_no_args(script_name):
    script_dir = Path(__file__).resolve().parent
    script_path = script_dir / "Modules" / script_name

    if not script_path.exists():
        print(f"\nError: {script_path} not found.")
        return False

    command = ["python3", str(script_path)]
    # print(f"\n>> Running command: {' '.join(command)}\n")

    env = os.environ.copy()
    env['PYTHONPATH'] = str(script_dir)

    process = None
    try:
        process = subprocess.Popen(
            command,
            env=env
        )
        process.wait()
        return process.returncode == 0
    except (KeyboardInterrupt, GracefulExit):
        if process:
            print("\n\nOperation aborted. Cleaning up...")
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        raise
    except subprocess.CalledProcessError as e:
        print(f"\nError running script: {e}")
        return False

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while True:
            print("\n[Menu]")
            print("----------------------------------")
            print("1) Extract SRT telemetry [.MP4]")
            print("2) Generate HUD frame [.SRT]")
            print("3) Extract and generate HUD")
            print("4) Extract EXIF info [.JPG .DNG]")
            print("5) SRT Merger")
            print("6) Flight log extractor")
            print("7) Convert DJI .srt in 2Lz.csv")
            print("0) Exit")
            
            try:
                choice = input("\nEnter your choice: ")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting program...\n")
                break
                
            if choice == "0":
                print("\nExiting program...\n")
                break
                
            if choice in ["1", "2", "3"]:
                try:
                    file_path = input("Enter file/directory path: ")
                    process_video(file_path, int(choice))
                except (KeyboardInterrupt, GracefulExit):
                    print("\nOperation cancelled.\n")
                    continue
                    
            if choice == "4":
                try:
                    file_path = input("Enter photo path: ")
                    photo_path, _ = get_file_input(clean_path(file_path), check_mp4=False)
                    if photo_path:
                        run_script("DJI2Lz_GPS.ExifInfo.py", photo_path)
                except (KeyboardInterrupt, GracefulExit):
                    print("\nOperation cancelled.\n")
                    continue
                    
            if choice == "5":
                try:
                    print("Enter SRT files to merge (space-separated):")
                    print("Example: file1.srt file2.srt file3.srt")
                    srt_files = input("> ")
                    
                    srt_paths = shlex.split(srt_files)
                    
                    if len(srt_paths) < 2:
                        print("Error: At least 2 SRT files are required for merging.")
                        continue
                    
                    srt_paths = [clean_path(path) for path in srt_paths]
                    run_script("DJI2Lz-SrtMerger.py", srt_paths)
                except (KeyboardInterrupt, GracefulExit):
                    print("\nOperation cancelled.\n")
                    continue

            if choice == "6":
                try:
                    run_no_args("DJI2Lz_LogWrapper.py")
                except (KeyboardInterrupt, GracefulExit):
                    print("\nOperation cancelled.\n")
                    continue

            elif choice == "7":
                try:
                    run_no_args("DJI2Lz_SrtConverter.py")
                except (KeyboardInterrupt, GracefulExit):
                    print("\nOperation cancelled.\n")
                    continue

    except (KeyboardInterrupt, GracefulExit):
        print("\nExiting program...\n")

if __name__ == "__main__":
    main()