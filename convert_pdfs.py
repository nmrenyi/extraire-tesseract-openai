#!/usr/bin/env python3
"""
Convert PDFs to PNG images using pdftoppm
Output structure: ./rosenwald-images/YEAR/YEAR-page-X.png
"""

import os
import subprocess
import glob
from pathlib import Path

def convert_pdf_to_png(pdf_path, output_dir):
    """
    Convert a single PDF to PNG pages using pdftoppm
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory where PNG files will be saved
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
        # -r 300: resolution 300 DPI for good quality
        cmd = [
            "pdftoppm",
            "-png",
            "-r", "300",
            pdf_path,
            str(output_prefix)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ Successfully converted {pdf_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error converting {pdf_path}: {e}")
        print(f"Error output: {e.stderr}")
    except FileNotFoundError:
        print("✗ Error: pdftoppm command not found. Make sure it's installed and in your PATH.")
        return False
    
    return True

def main():
    # Define paths
    current_dir = Path(__file__).parent
    pdfs_dir = current_dir / "pdfs"
    output_dir = current_dir / "rosenwald-images"
    
    # Check if pdfs directory exists
    if not pdfs_dir.exists():
        print(f"Error: {pdfs_dir} directory not found!")
        return
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Find all PDF files
    pdf_files = sorted(glob.glob(str(pdfs_dir / "*.pdf")))
    
    if not pdf_files:
        print(f"No PDF files found in {pdfs_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to convert:")
    for pdf in pdf_files:
        print(f"  - {Path(pdf).name}")
    
    print("\nStarting conversion...")
    
    # Convert each PDF
    successful = 0
    for pdf_path in pdf_files:
        if convert_pdf_to_png(pdf_path, output_dir):
            successful += 1
    
    print(f"\nConversion complete! {successful}/{len(pdf_files)} files processed successfully.")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    main()