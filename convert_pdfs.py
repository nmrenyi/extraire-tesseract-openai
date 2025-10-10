#!/usr/bin/env python3
"""
Convert PDFs to PNG images using pdftoppm
Output structure: ./rosenwald-images/YEAR/YEAR-page-X.png
"""

import os
import subprocess
import glob
import argparse
import sys
from pathlib import Path

def convert_pdf_to_png(pdf_path, output_dir, dpi=300):
    """
    Convert a single PDF to PNG pages using pdftoppm
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory where PNG files will be saved
        dpi (int): Resolution for output images (default: 300)
    """
    # Extract year from filename (e.g., "1887.pdf" -> "1887")
    year = Path(pdf_path).stem
    
    # Create year-specific directory
    year_dir = Path(output_dir) / year
    year_dir.mkdir(parents=True, exist_ok=True)
    
    # Define output prefix for pdftoppm
    output_prefix = year_dir / f"{year}-page"
    
    print(f"Converting {pdf_path} to {year_dir}/...")
    
    try:
        # Use pdftoppm to convert PDF to PNG
        # -png: output format PNG
        # -r: resolution DPI for good quality
        cmd = [
            "pdftoppm",
            "-png",
            "-r", str(dpi),
            pdf_path,
            str(output_prefix)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ Successfully converted {pdf_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error converting {pdf_path}: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ Error: pdftoppm command not found. Make sure it's installed and in your PATH.")
        return False

def get_pdf_files(pdfs_dir, pdf_names=None):
    """
    Get list of PDF files to process
    
    Args:
        pdfs_dir (Path): Directory containing PDF files
        pdf_names (list): Specific PDF names to process, or None for all
    
    Returns:
        list: List of PDF file paths
    """
    if pdf_names:
        # Process specific PDFs
        pdf_files = []
        for name in pdf_names:
            # Add .pdf extension if not present
            if not name.endswith('.pdf'):
                name += '.pdf'
            
            pdf_path = pdfs_dir / name
            if pdf_path.exists():
                pdf_files.append(str(pdf_path))
            else:
                print(f"Warning: PDF file '{name}' not found in {pdfs_dir}")
        
        return sorted(pdf_files)
    else:
        # Process all PDFs
        return sorted(glob.glob(str(pdfs_dir / "*.pdf")))

def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF files to PNG images using pdftoppm',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s                        # Convert all PDFs in pdfs/ directory
  %(prog)s 1887                   # Convert only 1887.pdf
  %(prog)s 1887 1888 1889         # Convert specific PDFs
  %(prog)s 1887 --dpi 600         # Convert with higher resolution
        '''
    )
    
    parser.add_argument(
        'pdfs',
        nargs='*',
        help='Specific PDF files to convert (without .pdf extension). If none specified, converts all PDFs.'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='Output resolution in DPI (default: 300)'
    )
    
    parser.add_argument(
        '--pdfs-dir',
        default='pdfs',
        help='Directory containing PDF files (default: pdfs)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='rosenwald-images',
        help='Output directory for PNG files (default: rosenwald-images)'
    )
    
    args = parser.parse_args()
    
    # Define paths
    current_dir = Path(__file__).parent
    pdfs_dir = current_dir / args.pdfs_dir
    output_dir = current_dir / args.output_dir
    
    # Check if pdfs directory exists
    if not pdfs_dir.exists():
        print(f"Error: {pdfs_dir} directory not found!")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Get PDF files to process
    pdf_files = get_pdf_files(pdfs_dir, args.pdfs if args.pdfs else None)
    
    if not pdf_files:
        if args.pdfs:
            print(f"No specified PDF files found in {pdfs_dir}")
        else:
            print(f"No PDF files found in {pdfs_dir}")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF file(s) to convert:")
    for pdf in pdf_files:
        print(f"  - {Path(pdf).name}")
    
    print(f"\nStarting conversion with {args.dpi} DPI...")
    
    # Convert each PDF
    successful = 0
    for pdf_path in pdf_files:
        if convert_pdf_to_png(pdf_path, output_dir, args.dpi):
            successful += 1
    
    print(f"\nConversion complete! {successful}/{len(pdf_files)} files processed successfully.")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    main()