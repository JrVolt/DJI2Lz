import os
import re
import sys
import argparse

def merge_srt_files(srt_files):
    """
    Merges multiple .srt files, sorts them by name, and reindexes the chunks.

    Args:
        srt_files: A list of paths to the .srt files to be merged.

    """
    merged_srt = ""
    chunk_count = 1

    for srt_file in sorted(srt_files):
        with open(srt_file, 'r') as f:
            srt_content = f.read()

        chunks = re.split(r'\n\n', srt_content.strip())

        for chunk in chunks:
            lines = chunk.splitlines()
            if re.match(r'^\d+$', lines[0]):
                lines.pop(0)
            lines.insert(0, str(chunk_count))
            merged_srt += '\n'.join(lines) + '\n\n'
            chunk_count += 1

    return merged_srt

def main():
    parser = argparse.ArgumentParser(description="SRT File Merger with Reindexing")
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
            found_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.srt')]
            if not found_files:
                print(f"No srt files found: {path}")
            srt_files.extend(found_files)
        elif os.path.isfile(path) and path.endswith('.srt'):
            srt_files.append(path)
        else:
            print(f"Invalid SRT file or directory: {path}")

    if not srt_files:
        sys.exit("No valid SRT files found ")

    merged_srt_content = merge_srt_files(srt_files)

    if args.output:
        output_path = args.output
    else:
        directory = os.path.dirname(srt_files[0])
        output_filename = "-".join(os.path.basename((f).replace("DJI_","")).split(".")[0] for f in srt_files)
        output_path = os.path.join(directory, "DJI_" + output_filename + ".srt")

    with open(output_path, 'w') as f:
        f.write(merged_srt_content)

    print(f"Merged SRT files saved as {output_path}")

if __name__ == "__main__":
    main()