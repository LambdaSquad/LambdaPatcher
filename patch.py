#!/usr/bin/env python3
import shutil
import os
import argparse
import subprocess
import logging
from pathlib import Path
from patched import replacement
from config import KS_PATH, KS_ALIAS, KS_PASS
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def replace_in_file(filepath, verbose=False):
    """Reads a file, applies string replacements, and saves it back."""
    try:
        content = filepath.read_text(encoding='utf-8')
        originalinal_content = content
        
        for old_str, new_str in replacement:
            content = content.replace(old_str, new_str)
            
        if content != originalinal_content:
            filepath.write_text(content, encoding='utf-8')
            if verbose:
                logger.info(f"Modified: {filepath}")
            return 1
    except (UnicodeDecodeError, ValueError):
        if verbose:
            logger.debug(f"Skipped non-text file: {filepath}")
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
    return 0

def run_command(command, description):
    """Helper to run shell commands safely."""
    logger.info(f"Running: {description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description='Decompile, patch, and rebuild APK.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if os.path.exists("original"):
        shutil.rmtree("original")

    if not run_command("./bin/apktool d original.apk", "Decompiling APK"):
        return

    modified_count = 0
    base_dir = Path("original")
    
    if not base_dir.exists():
        logger.error("Decompilation failed; 'original' directory not found.")
        return

    for file_path in base_dir.rglob('*'):
        if file_path.is_file():
            modified_count += replace_in_file(file_path, args.verbose)
    
    logger.info(f"Modifications complete. Updated {modified_count} files.")

    if os.path.exists('./replace'):
        shutil.copytree('./replace', './original', dirs_exist_ok=True)


    build_cmd = "./bin/apktool b ./original -o ./output.apk"
    sign_cmd = (
        "java -jar ./bin/uber-apk-signer.jar --apks ./output.apk "
        f"--ks {KS_PATH} --ksAlias {KS_ALIAS} --ksPass {KS_PASS}"
    )

    if run_command(build_cmd, "Rebuilding APK"):
        if os.path.exists("original"):
            shutil.rmtree("original")
        run_command(sign_cmd, "Signing APK")

if __name__ == '__main__':
    main()