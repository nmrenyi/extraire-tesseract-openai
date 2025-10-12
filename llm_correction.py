#!/usr/bin/env python3
"""
LLM-Powered OCR Post-Correction Pipeline

This module processes OCR text through LLM models (GPT-5 series, Gemini 2.5 series) 
to correct errors and extract structured medical directory data.

Features:
- Support for multiple LLM models (GPT-5, GPT-5-mini, GPT-5-nano, Gemini 2.5)
- Batch processing with configurable delays
- Comprehensive error handling and retry logic
- Progress tracking and detailed logging
- Choice between original PDF OCR and Tesseract OCR input
- Structured TSV output matching medical directory format
"""

import argparse
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
import logging
from dataclasses import dataclass
from openai import OpenAI

# Optional import for Gemini support
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_correction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of processing a single page"""
    page_file: str
    success: bool
    output_data: Optional[str] = None
    error_message: Optional[str] = None
    model_used: Optional[str] = None
    processing_time: Optional[float] = None
    retry_count: int = 0

class LLMCorrector:
    """Main class for LLM-powered OCR correction"""
    
    # Supported models
    GPT_MODELS = ['gpt-5', 'gpt-5-mini', 'gpt-5-nano']
    GEMINI_MODELS = ['gemini-2.5-pro', 'gemini-2.5-flash'] if GEMINI_AVAILABLE else []
    
    def __init__(self, model: str = 'gpt-5', delay_between_pages: float = 1.0):
        """
        Initialize AI corrector
        
        Args:
            model: AI model to use
            delay_between_pages: Delay in seconds between processing pages
        """
        self.model = model
        self.delay_between_pages = delay_between_pages
        self.openai_client = None
        self.genai_model = None
        
        # Load prompt template
        self.instructions = self._load_prompt_template()
        
        # Initialize the appropriate client
        self._initialize_client()
    
    def _load_prompt_template(self) -> str:
        """Load the instruction template from instructions-raw.txt and example-output.tsv"""
        try:
            # Load main instructions
            instructions_file = Path("instructions-raw.txt")
            if not instructions_file.exists():
                raise FileNotFoundError("instructions-raw.txt not found in current directory")
            
            with open(instructions_file, 'r', encoding='utf-8') as f:
                instructions = f.read().strip()
            
            # Load example output
            example_file = Path("example-output.tsv")
            if not example_file.exists():
                raise FileNotFoundError("example-output.tsv not found in current directory")
            
            with open(example_file, 'r', encoding='utf-8') as f:
                example_output = f.read().strip()
            
            # Combine them with a clear separator
            combined_instructions = f"{instructions}\n\n### EXEMPLE DE SORTIE ATTENDUE\n{example_output}"
            
            return combined_instructions
        except Exception as e:
            logger.error(f"Failed to load instruction templates: {e}")
            raise
    
    def _initialize_client(self):
        """Initialize the appropriate AI client based on model"""
        try:
            if self.model in self.GPT_MODELS:
                self.openai_client = OpenAI()
                logger.info(f"Initialized OpenAI client for model: {self.model}")
            elif self.model in self.GEMINI_MODELS:
                if not GEMINI_AVAILABLE:
                    raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")
                # Configure Gemini (requires GOOGLE_API_KEY environment variable)
                genai.configure()
                self.genai_model = genai.GenerativeModel(self.model)
                logger.info(f"Initialized Gemini client for model: {self.model}")
            else:
                available_models = self.GPT_MODELS + self.GEMINI_MODELS
                raise ValueError(f"Unsupported model: {self.model}. Available models: {available_models}")
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            raise
    
    def process_single_page(self, ocr_text: str, page_identifier: str, max_retries: int = 3) -> ProcessingResult:
        """
        Process a single page of OCR text through AI correction
        
        Args:
            ocr_text: Raw OCR text to process
            page_identifier: Identifier for the page (for logging)
            max_retries: Maximum number of retry attempts
            
        Returns:
            ProcessingResult with success status and output
        """
        start_time = time.time()
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Processing {page_identifier} (attempt {attempt + 1}/{max_retries + 1})")
                
                # Call the appropriate AI model with clean separation of instructions and input
                if self.model in self.GPT_MODELS:
                    result = self._call_openai(ocr_text)
                elif self.model in self.GEMINI_MODELS:
                    result = self._call_gemini(ocr_text)
                else:
                    raise ValueError(f"Unsupported model: {self.model}")
                
                processing_time = time.time() - start_time
                
                # Validate the result
                if self._validate_output(result):
                    logger.info(f"Successfully processed {page_identifier} in {processing_time:.2f}s")
                    return ProcessingResult(
                        page_file=page_identifier,
                        success=True,
                        output_data=result,
                        model_used=self.model,
                        processing_time=processing_time,
                        retry_count=attempt
                    )
                else:
                    logger.warning(f"Invalid output format for {page_identifier}, retrying...")
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing {page_identifier} (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    processing_time = time.time() - start_time
                    return ProcessingResult(
                        page_file=page_identifier,
                        success=False,
                        error_message=str(e),
                        model_used=self.model,
                        processing_time=processing_time,
                        retry_count=attempt
                    )
                
                # Exponential backoff for retries
                time.sleep(2 ** attempt)
        
        # Should never reach here, but just in case
        return ProcessingResult(
            page_file=page_identifier,
            success=False,
            error_message="Maximum retries exceeded",
            model_used=self.model,
            retry_count=max_retries
        )
    
    def _call_openai(self, ocr_text: str) -> str:
        """Call OpenAI API with clean separation of instructions and input"""
        try:
            response = self.openai_client.responses.create(
                model=self.model,
                instructions=self.instructions,
                input=ocr_text
            )
            return response.output_text.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _call_gemini(self, ocr_text: str) -> str:
        """Call Gemini API with combined instructions and input"""
        if not GEMINI_AVAILABLE:
            raise ImportError("Gemini support not available. Install google-generativeai package.")
        
        try:
            # For Gemini, combine instructions and input since it doesn't have separate parameters
            full_prompt = f"{self.instructions}\n\n### TEXTE OCR À TRAITER:\n{ocr_text}"
            
            response = self.genai_model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0,  # Deterministic output for structured data extraction
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _validate_output(self, output: str) -> bool:
        """
        Validate that the output is in the expected TSV format
        
        Args:
            output: The AI model output to validate
            
        Returns:
            True if output appears to be valid TSV format
        """
        if not output or len(output.strip()) == 0:
            return False
        
        lines = output.strip().split('\n')
        
        # Should have at least a header line
        if len(lines) < 1:
            return False
        
        # Check if first line looks like a header
        header_line = lines[0].strip()
        expected_columns = ['nom', 'année', 'notes', 'adresse', 'horaires']
        
        # Allow for TSV header (with tabs) or empty result (just header)
        if '\t' in header_line:
            columns = [col.strip() for col in header_line.split('\t')]
            return columns == expected_columns
        
        # If no tabs in header, it might be an empty result page
        # which is valid according to the prompt
        return len(lines) == 1 and any(col in header_line for col in expected_columns)
    
    def get_ocr_files(self, year: str, pages: Optional[List[int]] = None, 
                     ocr_source: str = 'tesseract') -> List[Tuple[Path, str]]:
        """
        Get list of OCR files to process
        
        Args:
            year: Year to process (e.g., '1887')
            pages: List of specific page numbers, or None for all pages
            ocr_source: 'tesseract' or 'original' OCR source
            
        Returns:
            List of (file_path, page_identifier) tuples
        """
        if ocr_source == 'tesseract':
            ocr_dir = Path(f"rosenwald-tesseract-ocr/{year}")
        elif ocr_source == 'original':
            ocr_dir = Path(f"rosenwald-original-ocr/{year}")
        else:
            raise ValueError(f"Invalid ocr_source: {ocr_source}. Must be 'tesseract' or 'original'")
        
        if not ocr_dir.exists():
            raise FileNotFoundError(f"OCR directory not found: {ocr_dir}")
        
        # Get all text files in the directory
        all_files = sorted(ocr_dir.glob(f"{year}-page-*.txt"))
        
        if not all_files:
            raise FileNotFoundError(f"No OCR files found in {ocr_dir}")
        
        # Filter by specific pages if requested
        if pages:
            filtered_files = []
            for page_num in pages:
                page_file = ocr_dir / f"{year}-page-{page_num:03d}.txt"
                if page_file.exists():
                    filtered_files.append((page_file, f"{year}-page-{page_num:03d}"))
                else:
                    logger.warning(f"Page file not found: {page_file}")
            return filtered_files
        else:
            return [(f, f.stem) for f in all_files]
    
    def process_batch(self, year: str, pages: Optional[List[int]] = None, 
                     ocr_source: str = 'tesseract', output_dir: Optional[str] = None) -> Dict[str, any]:
        """
        Process a batch of OCR files
        
        Args:
            year: Year to process
            pages: Specific pages to process, or None for all
            ocr_source: 'tesseract' or 'original'
            output_dir: Custom output directory, or None for default structure
            
        Returns:
            Dictionary with processing statistics and results
        """
        # Setup output directory with organized structure
        if output_dir is None:
            output_dir = f"llm-corrected-results/{ocr_source}/{self.model}/{year}"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get files to process
        try:
            files_to_process = self.get_ocr_files(year, pages, ocr_source)
        except Exception as e:
            logger.error(f"Failed to get OCR files: {e}")
            return {"success": False, "error": str(e)}
        
        if not files_to_process:
            logger.error("No files to process")
            return {"success": False, "error": "No files found to process"}
        
        logger.info(f"Processing {len(files_to_process)} files with model {self.model}")
        logger.info(f"OCR source: {ocr_source}")
        logger.info(f"Output directory: {output_path}")
        
        # Process files with progress bar
        results = []
        successful_count = 0
        failed_count = 0
        
        with tqdm(files_to_process, desc=f"LLM Correction ({self.model})", unit="page") as pbar:
            for i, (file_path, page_id) in enumerate(pbar):
                try:
                    # Read OCR text
                    with open(file_path, 'r', encoding='utf-8') as f:
                        ocr_text = f.read()
                    
                    # Process through AI
                    result = self.process_single_page(ocr_text, page_id)
                    results.append(result)
                    
                    if result.success:
                        # Save corrected output
                        output_file = output_path / f"{page_id}.tsv"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(result.output_data)
                        
                        successful_count += 1
                        pbar.set_postfix({
                            "Success": f"{successful_count}/{len(files_to_process)}", 
                            "Model": self.model
                        })
                    else:
                        failed_count += 1
                        pbar.set_postfix({
                            "Success": f"{successful_count}/{len(files_to_process)}", 
                            "Failed": failed_count,
                            "Model": self.model
                        })
                        
                        # Log error
                        logger.error(f"Failed to process {page_id}: {result.error_message}")
                    
                    # Add delay between pages (except for last page)
                    if i < len(files_to_process) - 1 and self.delay_between_pages > 0:
                        time.sleep(self.delay_between_pages)
                
                except Exception as e:
                    logger.error(f"Unexpected error processing {page_id}: {e}")
                    failed_count += 1
                    results.append(ProcessingResult(
                        page_file=page_id,
                        success=False,
                        error_message=str(e),
                        model_used=self.model
                    ))
        
        # Generate summary report
        total_time = sum(r.processing_time for r in results if r.processing_time)
        avg_time = total_time / len(results) if results else 0
        
        summary = {
            "success": True,
            "model_used": self.model,
            "ocr_source": ocr_source,
            "total_files": len(files_to_process),
            "successful": successful_count,
            "failed": failed_count,
            "success_rate": successful_count / len(files_to_process) * 100 if files_to_process else 0,
            "total_processing_time": total_time,
            "average_time_per_page": avg_time,
            "output_directory": str(output_path),
            "results": results
        }
        
        # Save summary report
        summary_file = output_path / "processing_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            # Convert ProcessingResult objects to dicts for JSON serialization
            json_summary = summary.copy()
            json_summary["results"] = [
                {
                    "page_file": r.page_file,
                    "success": r.success,
                    "error_message": r.error_message,
                    "model_used": r.model_used,
                    "processing_time": r.processing_time,
                    "retry_count": r.retry_count
                }
                for r in results
            ]
            json.dump(json_summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processing complete: {successful_count}/{len(files_to_process)} successful")
        logger.info(f"Summary saved to: {summary_file}")
        
        return summary

def parse_page_range(page_str: str) -> List[int]:
    """
    Parse page specification string into list of page numbers
    
    Examples:
        "5" -> [5]
        "1-10" -> [1, 2, 3, ..., 10]
        "1,5,10-12" -> [1, 5, 10, 11, 12]
    """
    pages = []
    
    for part in page_str.split(','):
        part = part.strip()
        if '-' in part:
            # Range specification
            start, end = map(int, part.split('-'))
            pages.extend(range(start, end + 1))
        else:
            # Single page
            pages.append(int(part))
    
    return sorted(list(set(pages)))  # Remove duplicates and sort

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='LLM-Powered OCR Post-Correction for Rosenwald Medical Directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  # Process single page with GPT-5-nano
  %(prog)s --year 1887 --pages 32 --model gpt-5-nano
  
  # Process multiple pages with GPT-5-mini
  %(prog)s --year 1887 --pages 1-10,50,100-105 --model gpt-5-mini
  
  # Use original OCR instead of Tesseract
  %(prog)s --year 1887 --pages 32 --ocr-source original
  
  # Process all pages with delay (for rate limiting)
  %(prog)s --year 1887 --delay 2.0
        '''
    )
    
    parser.add_argument(
        '--year', '-y',
        required=True,
        help='Year to process (e.g., 1887)'
    )
    
    parser.add_argument(
        '--pages', '-p',
        help='Page numbers to process. Examples: 32, 1-10, 1,5,10-12. If not specified, processes all pages.'
    )
    
    parser.add_argument(
        '--model', '-m',
        choices=LLMCorrector.GPT_MODELS + LLMCorrector.GEMINI_MODELS,
        default='gpt-5',
        help='AI model to use (default: gpt-5)'
    )
    
    parser.add_argument(
        '--ocr-source', '-s',
        choices=['tesseract', 'original'],
        default='tesseract',
        help='OCR source to use (default: tesseract)'
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=0.5,
        help='Delay in seconds between processing pages (default: 0.5, set to 0 for no delay)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        help='Custom output directory (default: llm-corrected-results/{ocr_source}/{model}/{year}/)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse pages if specified
    pages = None
    if args.pages:
        try:
            pages = parse_page_range(args.pages)
            logger.info(f"Processing pages: {pages}")
        except ValueError as e:
            logger.error(f"Invalid page specification: {e}")
            sys.exit(1)
    
    try:
        # Initialize corrector
        corrector = LLMCorrector(model=args.model, delay_between_pages=args.delay)
        
        # Process batch
        results = corrector.process_batch(
            year=args.year,
            pages=pages,
            ocr_source=args.ocr_source,
            output_dir=args.output_dir
        )
        
        if results["success"]:
            print(f"\n✓ Processing completed successfully!")
            print(f"  Model: {results['model_used']}")
            print(f"  Success rate: {results['success_rate']:.1f}%")
            print(f"  Files processed: {results['successful']}/{results['total_files']}")
            print(f"  Average time per page: {results['average_time_per_page']:.2f}s")
            print(f"  Output directory: {results['output_directory']}")
        else:
            print(f"\n✗ Processing failed: {results['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()