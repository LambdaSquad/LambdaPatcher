#!/bin/python
import os
import argparse
from patched import replacement
def replace_in_file(filepath, verbose=False):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            for i in replacement:
                content = content.replace(i[0],i[1])
            
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
            if verbose:
                print(f"Modified: {filepath}")
            return 1       
    except UnicodeDecodeError:
        if verbose:
            print(f"Skipped binary file: {filepath}")
        return 0
    except Exception as e:
        print(f"Error processing {filepath}: {str(e)}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='Replace strings in all files recursively.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    os.system("rm maxorig -rf")
    os.system("./apktool d maxorig.apk ")

    if not os.path.isdir("maxorig"):
        print(f"Error: Directory maxorig does not exist.")
        return

    modified_count = 0
    
    for root, dirs, files in os.walk(os.path.join(os.path.curdir,"maxorig")):
        for filename in files:
            filepath = os.path.join(root, filename)
            modified_count += replace_in_file(
                filepath, 
                args.verbose
            )
    
    print(f"\nOperation completed. Modified {modified_count} files.")
    os.system("rm MAX -rf")
    os.system("mv maxorig MAX")
    os.system("cp --update=all -f -r ./replace/* ./MAX/")
    os.system("./build.sh")
    os.system("./sign.sh")

if __name__ == '__main__':
    main()