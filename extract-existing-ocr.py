#!/usr/bin/env python3
"""
PDF Text Extraction Module

This module extracts embedded OCR text from PDF files using PyMuPDF (fitz).
Supports both single PDF and batch processing with command-line interface.
"""

import fitz  # PyMuPDF
import argparse
import sys
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm


def extract_text_from_pdf(pdf_path: str, output_dir: str = None) -> bool:
    """
    Extract embedded OCR text from each page of a PDF file and save to individual text files.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Directory to save extracted text files
        
    Returns:
        bool: True if successful, False if failed
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: PDF file '{pdf_file}' does not exist")
        return False
    
    # Set up output directory
    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Open the PDF document
        doc = fitz.open(str(pdf_file))
        total_pages = len(doc)
        
        print(f"Processing PDF: {pdf_file.name}")
        print(f"Total pages: {total_pages}")
        print(f"Output directory: {out_dir if output_dir else 'stdout'}")
        print("")
        
        success_count = 0
        failed_pages = []
        
        # Extract text from each page with progress bar
        with tqdm(range(total_pages), desc=f"Extracting {pdf_file.stem}", unit="page") as pbar:
            for page_idx in pbar:
                try:
                    page = doc.load_page(page_idx)
                    text = page.get_text()
                    
                    if output_dir:
                        # Save to individual text file
                        page_num = page_idx + 1
                        output_file = out_dir / f"{pdf_file.stem}-page-{page_num:04d}.txt"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(text.strip())
                        
                        success_count += 1
                        pbar.set_postfix({"Success": f"{success_count}/{total_pages}"})
                    else:
                        # Print to stdout
                        print(f"=== PAGE {page_idx + 1} ===")
                        print(text.strip())
                        print("\n" + "="*50 + "\n")
                        success_count += 1
                        
                except Exception as e:
                    failed_pages.append((page_idx + 1, str(e)))
                    pbar.set_postfix({"Success": f"{success_count}/{total_pages}", "Status": "FAILED"})
        
        # Close the document
        doc.close()
        
        # Report results
        if failed_pages:
            print(f"\n⚠️  {len(failed_pages)} page(s) failed text extraction:")
            for page_num, error in failed_pages:
                print(f"  Page {page_num}: {error}")
        
        print(f"\n✓ Completed! Extracted text from {success_count}/{total_pages} pages successfully.")
        if output_dir:
            print(f"Text files saved in: {out_dir}")
        
        return success_count == total_pages
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return False


def batch_extract_existing_ocr(year: str) -> bool:
    """
    Extract embedded OCR text from a specific year's PDF file.
    
    Args:
        year (str): Year to process (e.g., '1887')
        
    Returns:
        bool: True if successful, False if failed
    """
    # Set up paths
    pdf_file = Path(f"pdfs/{year}.pdf")
    output_dir = Path(f"rosenwald-original-ocr/{year}")
    
    if not pdf_file.exists():
        print(f"Error: PDF file '{pdf_file}' does not exist")
        return False
    
    return extract_text_from_pdf(str(pdf_file), str(output_dir))


def get_pdf_info(pdf_path: str) -> Dict[str, any]:
    """
    Get basic information about the PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Dict[str, any]: PDF metadata and information
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: PDF file '{pdf_file}' does not exist")
        return None
    
    try:
        doc = fitz.open(str(pdf_file))
        
        info = {
            "file_name": pdf_file.name,
            "page_count": len(doc),
            "metadata": doc.metadata,
            "is_encrypted": doc.is_encrypted,
            "is_pdf": doc.is_pdf
        }
        
        doc.close()
        return info
        
    except Exception as e:
        print(f"Error getting PDF info: {str(e)}")
        return None


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Extract embedded OCR text from PDF files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s --year 1887                        # Extract from pdfs/1887.pdf to rosenwald-original-ocr/1887/
  %(prog)s --pdf path/to/file.pdf             # Extract to stdout
  %(prog)s --pdf path/to/file.pdf --output dir/  # Extract to specified directory
  %(prog)s --info path/to/file.pdf            # Show PDF information only
        '''
    )
    
    # Create mutually exclusive group for different modes
    mode_group = parser.add_mutually_exclusive_group(required=True)
    
    mode_group.add_argument(
        '--year', '-y',
        help='Year to process (extracts from pdfs/YEAR.pdf to rosenwald-original-ocr/YEAR/)'
    )
    
    mode_group.add_argument(
        '--pdf', '-p',
        help='Path to specific PDF file to process'
    )
    
    mode_group.add_argument(
        '--info', '-i',
        help='Show information about a PDF file (no extraction)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory for extracted text files (only with --pdf option)'
    )
    
    args = parser.parse_args()
    
    # Handle different modes
    if args.info:
        # Show PDF information
        info = get_pdf_info(args.info)
        if info:
            print("PDF Information:")
            print(f"  File: {info['file_name']}")
            print(f"  Pages: {info['page_count']}")
            print(f"  Encrypted: {info['is_encrypted']}")
            print(f"  Valid PDF: {info['is_pdf']}")
            if info['metadata']:
                print("  Metadata:")
                for key, value in info['metadata'].items():
                    if value:  # Only show non-empty metadata
                        print(f"    {key}: {value}")
        else:
            sys.exit(1)
            
    elif args.year:
        # Batch processing for a specific year
        success = batch_extract_existing_ocr(args.year)
        if not success:
            sys.exit(1)
            
    elif args.pdf:
        # Process specific PDF file
        success = extract_text_from_pdf(args.pdf, args.output)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()