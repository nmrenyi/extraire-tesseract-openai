#!/usr/bin/env python3

import subprocess
import os
import sys
import argparse
from pathlib import Path
from tqdm import tqdm

def batch_ocr(directory_name, language='fra', psm='3'):
    """
    Run OCR on all PNG files in the specified directory.
    
    Args:
        directory_name (str): Name of the directory under rosenwald-images/
        language (str): Tesseract language code (default: 'fra')
        psm (str): Page segmentation mode (default: '3')
    """
    # Set up paths
    image_dir = Path(f"rosenwald-images/{directory_name}")
    output_dir = Path(f"rosenwald-tesseract-ocr/{directory_name}")
    
    # Check if input directory exists
    if not image_dir.exists():
        print(f"Error: Directory '{image_dir}' does not exist")
        return False
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing PNG files in: {image_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Using language: {language}, PSM: {psm}")
    print("")
    
    # Find all PNG files and sort them
    png_files = sorted(image_dir.glob("*.png"))
    
    if not png_files:
        print(f"No PNG files found in {image_dir}")
        return False
    
    # Process each PNG file with progress bar
    success_count = 0
    failed_files = []
    total_count = len(png_files)
    
    with tqdm(png_files, desc=f"OCR {directory_name}", unit="file") as pbar:
        for png_file in pbar:
            filename = png_file.stem  # filename without extension
            output_file = output_dir / f"{filename}.txt"
            
            # Update progress bar description
            pbar.set_description(f"OCR {directory_name}: {png_file.name}")
            
            # Run tesseract
            result = subprocess.run([
                'tesseract', str(png_file), str(output_file.with_suffix('')),
                '-l', language,         # Language
                '--psm', psm           # Page segmentation mode
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                success_count += 1
                pbar.set_postfix({"Success": f"{success_count}/{total_count}"})
            else:
                failed_files.append((png_file.name, result.stderr.strip()))
                pbar.set_postfix({"Success": f"{success_count}/{total_count}", "Status": "FAILED"})
    
    # Report results
    if failed_files:
        print(f"\n⚠️  {len(failed_files)} file(s) failed OCR processing:")
        for filename, error in failed_files:
            print(f"  {filename}: {error}")
    
    print(f"\n✓ Completed! Processed {success_count}/{total_count} files successfully.")
    print(f"OCR text files saved in: {output_dir}")
    
    return success_count == total_count

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Batch OCR processing for PNG files using Tesseract',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s 1887                    # Process all PNGs in rosenwald-images/1887/
  %(prog)s 1888                    # Process all PNGs in rosenwald-images/1888/
        '''
    )
    
    parser.add_argument(
        'directory',
        help='Directory name under rosenwald-images/ to process'
    )
    
    parser.add_argument(
        '--language', '-l',
        default='fra',
        help='Tesseract language code (default: fra for French)'
    )
    
    parser.add_argument(
        '--psm',
        default='3',
        help='Page segmentation mode (default: 3 for automatic page segmentation)'
    )
    
    args = parser.parse_args()
    
    # Run batch OCR
    success = batch_ocr(args.directory, args.language, args.psm)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()