import os
import subprocess
import argparse

def extract_srt(video_path, output_dir=None):
    try:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = output_dir if output_dir else os.path.dirname(video_path)
        srt_file = os.path.join(output_path, f"{base_name}.srt")
        
        print(f"Processing: {video_path}")
        cmd = ['ffmpeg', '-i', video_path, '-map', '0:s:0', srt_file, '-y']
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Created: {srt_file}")

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")

    except Exception as e:
        print(f"Error: {str(e)}")

def process_directory(path, recursive=False, output_dir=None):
    for root, _, files in os.walk(path):
        mp4_files = [f for f in files if f.lower().endswith('.mp4')]
        for file in mp4_files:
            full_path = os.path.join(root, file)
            if not recursive and root != path:
                continue
            extract_srt(full_path, output_dir)
        if not recursive:
            break

def main():
    parser = argparse.ArgumentParser(
        description="""
        DJI SRT Extractor.

        Extracts embedded SRT data trrack from DJI MP4 videos.
        It can process single files or entire directories.
            Examples:
        %(prog)s video.mp4
        %(prog)s -o output/ folder/
        %(prog)s -r -o output/ folder/
                """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )
    parser.add_argument('input', nargs='?', help='Input MP4 file or directory')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process subdirectories recursively')
    parser.add_argument('-o', '--output', help='Output directory for SRT files')
    args = parser.parse_args()

    if not args.input:
        args.input = input("Enter path to MP4 file or directory: ")
    if args.output:
        os.makedirs(args.output, exist_ok=True)

    if os.path.isfile(args.input):
        extract_srt(args.input, args.output)
    elif os.path.isdir(args.input):
        process_directory(args.input, args.recursive, args.output)

if __name__ == '__main__':
    main()