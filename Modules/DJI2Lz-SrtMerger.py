import os
import re
import sys
import argparse

def merge_srt_files(srt_files):
    merged_srt = []
    index = 1

    for srt_file in sorted(srt_files):
        print(f"Processing: {srt_file}")
        with open(srt_file, 'r') as f:
            content = f.read().strip()
        
        chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
        
        for chunk in chunks:
            lines = chunk.splitlines()
            if len(lines) >= 3:
                merged_srt.append(f"{index}\n{lines[1]}\n{lines[2]}\n")
                index += 1

    return '\n'.join(merged_srt)

def main():
    parser = argparse.ArgumentParser(description="SRT File Merger with Sequential Indexing")
    parser.add_argument('input', nargs='*', help='Input SRT file(s) or directory containing SRT files')
    parser.add_argument('-o', '--output', help='Output file path', required=False)
    args = parser.parse_args()

    if not args.input:
        user_input = input("\nInput SRT file(s) or directory SRT \n>> ")
        input_strings = user_input.strip("'").split() 
        args.input = [string.strip("'") for string in input_strings] 

    srt_files = []
    for path in args.input:
        if os.path.isdir(path):
            found_files = sorted([os.path.join(path, f) for f in os.listdir(path) if f.endswith('.srt')])
            if not found_files:
                print(f"No SRT files found in: {path}")
            srt_files.extend(found_files)
        elif os.path.isfile(path) and path.endswith('.srt'):
            srt_files.append(path)
        else:
            print(f"Invalid SRT file or directory: {path}")

    if not srt_files:
        sys.exit("No valid SRT files found")

    print("\nMerging files in this order:")
    for f in srt_files:
        print(f"- {os.path.basename(f)}")

    merged_content = merge_srt_files(srt_files)

    if args.output:
        output_path = args.output
    else:
        directory = os.path.dirname(srt_files[0])
        output_filename = "-".join(os.path.basename(f).replace("DJI_","").split(".")[0] for f in srt_files)
        output_path = os.path.join(directory, f"DJI_MERGED_{output_filename}.srt")

    with open(output_path, 'w') as f:
        f.write(merged_content)

    print(f"\nMerged SRT saved as: {output_path}")

if __name__ == "__main__":
    main()