#!/usr/bin/env python3

import subprocess
import argparse
import sys
from pathlib import Path

def run_single_ocr(image_path, output_path=None, language='fra', psm='3'):
    """
    Run OCR on a single image file.
    
    Args:
        image_path (str): Path to the input image
        output_path (str): Path for output text file (optional, prints to stdout if None)
        language (str): Tesseract language code (default: 'fra')
        psm (str): Page segmentation mode (default: '3')
    
    Returns:
        bool: True if successful, False if failed
    """
    # Convert to Path objects
    img_path = Path(image_path)
    
    if not img_path.exists():
        print(f"Error: Image file '{img_path}' does not exist")
        return False
    
    # Prepare tesseract command
    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            'tesseract', str(img_path), str(out_path.with_suffix('')),
            '-l', language, '--psm', psm
        ]
    else:
        cmd = [
            'tesseract', str(img_path), 'stdout',
            '-l', language, '--psm', psm
        ]
    
    # Run tesseract
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        if not output_path:
            print(result.stdout)
        else:
            print(f"✓ Success: {output_path}")
        return True
    else:
        print(f"✗ Failed: {img_path.name}")
        print(f"  Error: {result.stderr.strip()}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Single file OCR processing using Tesseract',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s 1887 1                 # Process 1887-page-001.png
  %(prog)s 1887 149               # Process 1887-page-149.png
  %(prog)s 1888 25 --language eng # Process with English language
        '''
    )
    
    parser.add_argument(
        'year',
        help='Year directory (e.g., 1887, 1888)'
    )
    
    parser.add_argument(
        'page',
        type=int,
        help='Page number (e.g., 1, 149, 025)'
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
    
    # Build file paths
    page_num = f"{args.page:03d}"  # Format as 001, 002, etc.
    image_path = f"rosenwald-images/{args.year}/{args.year}-page-{page_num}.png"
    output_path = f"rosenwald-ocr/{args.year}/{args.year}-page-{page_num}.txt"
    
    print(f"Processing: {args.year}-page-{page_num}.png")
    
    # Run single OCR
    success = run_single_ocr(image_path, output_path, args.language, args.psm)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()