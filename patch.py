#!/usr/bin/env python3
import shutil
import os
import argparse
import subprocess
import logging
import json
import urllib.request
import urllib.error
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

def download_apk(output_path="output.apk"):
    """Fetches the APK download link from RuStore and saves the file using built-in libs."""
    api_url = "https://backapi.rustore.ru/applicationData/v2/download-link"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    
    payload = {
        "appId": 2063618637,
        "firstInstall": True,
        "mobileServices": [],
        "supportedAbis": ["x86_64", "arm64-v8a", "x86", "armeabi-v7a", "armeabi"],
        "screenDensity": 0,
        "supportedLocales": ["ru_RU"],
        "sdkVersion": 26,
        "withoutSplits": True,
        "signatureFingerprint": None
    }

    try:
        # 1. Request the download URL
        logger.info("Requesting download URL from RuStore...")
        json_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=json_data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            data = json.loads(res_body)
        
        # 2. Extract APK URL
        apk_url = data['body']['downloadUrls'][0]['url']
        apk_version = data['body']['versionCode']
        logger.info(f"Downloading APK version {apk_version}")
        logger.info(f"Downloading APK from: {apk_url}")

        # 3. Download the file in chunks
        # Using a secondary Request for the file download to maintain User-Agent if needed
        file_req = urllib.request.Request(apk_url, headers={"User-Agent": headers["User-Agent"]})
        with urllib.request.urlopen(file_req) as response, open(output_path, 'wb') as out_file:
            while True:
                chunk = response.read(8192) # 8KB chunks
                if not chunk:
                    break
                out_file.write(chunk)
        
        logger.info(f"Successfully saved to {output_path}")

    except urllib.error.URLError as e:
        logger.error(f"Network error: {e}")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False
    return True
def main():
    parser = argparse.ArgumentParser(description='Decompile, patch, and rebuild APK.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-d', '--download', action='store_true', help='Download original APK')
    parser.add_argument('-k', '--keep-temp-files', action='store_true', help='Keep temporary files after patching')
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    if args.download:
        if download_apk("original.apk"):
            logger.info("APK downloaded successfully.")
        else:
            logger.error("Failed to download APK.")
        return

    for i in ['original', 'output.apk', 'output-aligned.apk', 'output-aligned-signed.apk', 'output-aligned-signed.apk.idsig']:
        if os.path.exists(i):
            shutil.rmtree(i) if os.path.isdir(i) else os.remove(i)
    if os.name == 'nt':
        decompile_cmd = "./bin/apktool.bat d original.apk"
    else:
        decompile_cmd = "./bin/apktool d original.apk"
    if not run_command(decompile_cmd, "Decompiling APK"):
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

    if os.name == 'nt':
        build_cmd = "./bin/apktool.bat b ./original -o ./output.apk"
    else:
        build_cmd = "./bin/apktool b ./original -o ./output.apk"
    sign_cmd = (
        "java -jar ./bin/uber-apk-signer.jar --apks ./output.apk "
        f"--ks {KS_PATH} --ksAlias {KS_ALIAS} --ksPass {KS_PASS} --ksKeyPass {KS_PASS}"
    )

    if run_command(build_cmd, "Rebuilding APK"):
        if run_command(sign_cmd, "Signing APK"):
            logger.info("APK successfully rebuilt and signed: output-aligned-signed.apk")
            if not args.keep_temp_files:
                for i in ['original', 'output.apk', 'output-aligned.apk', 'output-aligned-signed.apk.idsig']:
                    if os.path.exists(i):
                        shutil.rmtree(i) if os.path.isdir(i) else os.remove(i)

if __name__ == '__main__':
    main()