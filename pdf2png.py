#!/usr/bin/env python3
"""
Convert PDFs to PNG images using pdftoppm
Output structure: ./rosenwald-images/YEAR/YEAR-page-X.png
"""

import os
import re
import subprocess
import glob
import argparse
import sys
from pathlib import Path
from tqdm import tqdm

def get_pdf_page_count(pdf_path):
    """
    Get the number of pages in a PDF file using PyMuPDF (fitz)
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        int or None: Number of pages, or None if unable to determine
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        doc.close()
        return page_count
    except (ImportError, Exception):
        # Fallback: assume a reasonable number for progress bar
        # The actual conversion will handle any page count issues
        return 1000  # Default assumption for large PDFs
        
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None

def convert_single_page_to_png(pdf_path, page_num, output_dir, dpi=300):
    """
    Convert a single page from PDF to PNG
    
    Args:
        pdf_path (str): Path to the PDF file
        page_num (int): Page number to convert (1-based)
        output_dir (str): Directory where PNG file will be saved
        dpi (int): Resolution for output image (default: 300)
    
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    # Extract year from filename (e.g., "1887.pdf" -> "1887")
    year = Path(pdf_path).stem
    
    # Create year-specific directory
    year_dir = Path(output_dir) / year
    year_dir.mkdir(parents=True, exist_ok=True)
    
    # Verify page exists
    page_count = get_pdf_page_count(pdf_path)
    if page_count and page_num > page_count:
        print(f"❌ Error: Page {page_num} does not exist in {pdf_path} (PDF has {page_count} pages)")
        return False
    
    # Target output file with 4-digit formatting
    target_output_file = year_dir / f"{year}-page-{page_num:04d}.png"
    
    print(f"\nConverting page {page_num} from {pdf_path}...")
    print(f"Output: {target_output_file}")
    
    # Use -singlefile with a unique temp prefix per page to avoid collisions under concurrency
    temp_prefix = year_dir / f"{year}-page-temp-{page_num:04d}-{os.getpid()}"
    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
        "-f", str(page_num),  # first page
        "-l", str(page_num),  # last page
        "-singlefile",        # Don't add digits to filename
        pdf_path,
        str(temp_prefix)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # pdftoppm with -singlefile creates: temp_prefix.png
        temp_file = Path(str(temp_prefix) + ".png")
        
        if temp_file.exists():
            # Rename to our 4-digit format
            temp_file.rename(target_output_file)
            print(f"✅ Successfully converted page {page_num} from {pdf_path}")
            return True
        else:
            print(f"❌ Error: Expected output file {temp_file} was not created")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error converting page {page_num} from {pdf_path}: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ Error: pdftoppm command not found. Make sure it's installed and in your PATH.")
        return False

def convert_pdf_to_png_with_progress(pdf_path, output_dir, dpi=300):
    """
    Convert PDF to PNG files page by page with 4-digit formatting
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory where PNG files will be saved
        dpi (int): Resolution for output images (default: 300)
    
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    # Extract year from filename (e.g., "1887.pdf" -> "1887")
    year = Path(pdf_path).stem
    
    # Create year-specific directory
    year_dir = Path(output_dir) / year
    year_dir.mkdir(parents=True, exist_ok=True)
    
    # Get page count first
    page_count = get_pdf_page_count(pdf_path)
    if not page_count:
        print(f"❌ Error: Could not determine page count for {pdf_path}")
        return False
    
    print(f"\nConverting {page_count} pages from {pdf_path}...")
    print(f"Output directory: {year_dir}")
    
    # Convert pages one by one to ensure 4-digit formatting
    successful_pages = 0
    failed_pages = []
    
    with tqdm(range(1, page_count + 1), desc=f"Converting {year}", unit="page") as pbar:
        for page_num in pbar:
            # Target output file with 4-digit formatting
            target_output_file = year_dir / f"{year}-page-{page_num:04d}.png"
            
            # Skip if file already exists
            if target_output_file.exists():
                successful_pages += 1
                pbar.set_postfix({"Success": f"{successful_pages}/{page_count}", "Status": "EXISTS"})
                continue
            
            # Use -singlefile to avoid pdftoppm's automatic numbering
            temp_prefix = year_dir / f"{year}-page-temp-{page_num}"
            cmd = [
                "pdftoppm",
                "-png",
                "-r", str(dpi),
                "-f", str(page_num),  # first page
                "-l", str(page_num),  # last page
                "-singlefile",        # Don't add digits to filename
                pdf_path,
                str(temp_prefix)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # pdftoppm with -singlefile creates: temp_prefix.png
                temp_file = Path(str(temp_prefix) + ".png")
                
                if temp_file.exists():
                    # Rename to our 4-digit format
                    temp_file.rename(target_output_file)
                    successful_pages += 1
                    pbar.set_postfix({"Success": f"{successful_pages}/{page_count}", "Status": "OK"})
                else:
                    failed_pages.append((page_num, "Output file not created"))
                    pbar.set_postfix({"Success": f"{successful_pages}/{page_count}", "Status": "FAILED"})
                
            except subprocess.CalledProcessError as e:
                failed_pages.append((page_num, e.stderr.strip() if e.stderr else str(e)))
                pbar.set_postfix({"Success": f"{successful_pages}/{page_count}", "Status": "ERROR"})
    
    # Report results
    if failed_pages:
        print(f"\n⚠️  {len(failed_pages)} page(s) failed to convert:")
        for page_num, error in failed_pages[:5]:  # Show first 5 errors
            print(f"  Page {page_num}: {error}")
        if len(failed_pages) > 5:
            print(f"  ... and {len(failed_pages) - 5} more errors")
    
    print(f"✅ Successfully converted {successful_pages}/{page_count} pages from {pdf_path}")
    return successful_pages == page_count

def convert_pdf_to_png_fallback(pdf_path, output_dir, dpi=300):
    """
    Fallback method: Convert entire PDF at once (original method)
    """
    year = Path(pdf_path).stem
    year_dir = Path(output_dir) / year
    year_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = year_dir / f"{year}-page"
    
    try:
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
  %(prog)s 1887                   # Convert entire 1887.pdf
  %(prog)s 1887 --page 32         # Convert only page 32 from 1887.pdf
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
        '--page',
        type=int,
        help='Convert only a specific page number (1-based). Can only be used with a single PDF.'
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
    
    # Validate arguments
    if args.page and (not args.pdfs or len(args.pdfs) != 1):
        print("❌ Error: --page can only be used with exactly one PDF file")
        print("Example: python pdf2png.py 1887 --page 32")
        sys.exit(1)
    
    if args.page and args.page < 1:
        print("❌ Error: Page number must be 1 or greater")
        sys.exit(1)
    
    # Define paths
    current_dir = Path(__file__).parent
    pdfs_dir = current_dir / args.pdfs_dir
    output_dir = current_dir / args.output_dir
    
    # Check if pdfs directory exists
    if not pdfs_dir.exists():
        print(f"❌ Error: {pdfs_dir} directory not found!")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Get PDF files to process
    pdf_files = get_pdf_files(pdfs_dir, args.pdfs if args.pdfs else None)
    
    if not pdf_files:
        if args.pdfs:
            print(f"❌ No specified PDF files found in {pdfs_dir}")
        else:
            print(f"❌ No PDF files found in {pdfs_dir}")
        sys.exit(1)
    
    # Handle single page conversion
    if args.page:
        pdf_path = pdf_files[0]
        print(f"🔍 Converting page {args.page} from {Path(pdf_path).name}")
        print(f"Output directory: {output_dir}")
        
        success = convert_single_page_to_png(pdf_path, args.page, output_dir, args.dpi)
        
        if success:
            print(f"\n✅ Page conversion complete!")
        else:
            print(f"\n❌ Page conversion failed!")
            sys.exit(1)
        return
    
    # Handle full PDF conversion
    print(f"🔍 Found {len(pdf_files)} PDF file(s) to convert:")
    for pdf in pdf_files:
        print(f"  - {Path(pdf).name}")
    
    print(f"\n📄 Starting conversion with {args.dpi} DPI...")
    
    # Convert each PDF
    successful = 0
    for pdf_path in pdf_files:
        if convert_pdf_to_png_with_progress(pdf_path, output_dir, args.dpi):
            successful += 1
    
    print(f"\nConversion complete! {successful}/{len(pdf_files)} files processed successfully.")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    main()