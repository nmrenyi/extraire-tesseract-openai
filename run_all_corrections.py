#!/usr/bin/env python3
"""
Script to run all post-corrections for a specific page
Usage: python run_all_corrections.py --year 1887 --page 32
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run all post-corrections for a specific page")
    parser.add_argument("--year", type=str, required=True, help="Year (e.g., 1887)")
    parser.add_argument("--page", type=int, required=True, help="Page number (e.g., 32)")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    
    args = parser.parse_args()
    
    year = args.year
    page = args.page
    page_str = f"{page:04d}"  # 4-digit format
    
    print(f"🚀 Running all post-corrections for {year} page {page}")
    print(f"📄 Page format: {year}-page-{page_str}")
    
    # List of all correction tasks (alternating GPT and Gemini to avoid consecutive API calls)
    tasks = [
        # Original OCR - alternating GPT and Gemini
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "original",
                   "--model", "gpt-5"],
            "description": f"LLM correction: Original OCR + GPT-5 for {year} page {page}"
        },
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "original", 
                   "--model", "gemini-2.5-pro"],
            "description": f"LLM correction: Original OCR + Gemini 2.5 Pro for {year} page {page}"
        },
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "original",
                   "--model", "gpt-5-mini"],
            "description": f"LLM correction: Original OCR + GPT-5-mini for {year} page {page}"
        },
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "original",
                   "--model", "gemini-2.5-flash"],
            "description": f"LLM correction: Original OCR + Gemini 2.5 Flash for {year} page {page}"
        },
        
        # Tesseract OCR - alternating GPT and Gemini
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "tesseract",
                   "--model", "gpt-5"],
            "description": f"LLM correction: Tesseract OCR + GPT-5 for {year} page {page}"
        },
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "tesseract",
                   "--model", "gemini-2.5-pro"],
            "description": f"LLM correction: Tesseract OCR + Gemini 2.5 Pro for {year} page {page}"
        },
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "tesseract",
                   "--model", "gpt-5-mini"],
            "description": f"LLM correction: Tesseract OCR + GPT-5-mini for {year} page {page}"
        },
        {
            "cmd": ["python", "llm-correction.py", 
                   "--year", year, 
                   "--page", page_str,
                   "--source", "tesseract",
                   "--model", "gemini-2.5-flash"],
            "description": f"LLM correction: Tesseract OCR + Gemini 2.5 Flash for {year} page {page}"
        }
    ]
    
    if args.dry_run:
        print("\n🔍 DRY RUN - Commands that would be executed:")
        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. {task['description']}")
            print(f"   Command: {' '.join(task['cmd'])}")
        return
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    # Check if files exist
    original_ocr_file = Path(f"rosenwald-original-ocr/{year}/{year}-page-{page_str}.txt")
    tesseract_ocr_file = Path(f"rosenwald-tesseract-ocr/{year}/{year}-page-{page_str}.txt")
    
    if not original_ocr_file.exists():
        print(f"❌ Original OCR file not found: {original_ocr_file}")
        print("   Run extract-existing-ocr.py first to extract original OCR")
        sys.exit(1)
    
    if not tesseract_ocr_file.exists():
        print(f"❌ Tesseract OCR file not found: {tesseract_ocr_file}")
        print("   Run ocr.py first to generate Tesseract OCR")
        sys.exit(1)
    
    print(f"✅ Original OCR file found: {original_ocr_file}")
    print(f"✅ Tesseract OCR file found: {tesseract_ocr_file}")
    
    # Execute tasks
    successful_tasks = 0
    failed_tasks = []
    
    for i, task in enumerate(tasks, 1):
        print(f"\n📊 Progress: {i}/{len(tasks)}")
        success = run_command(task["cmd"], task["description"])
        
        if success:
            successful_tasks += 1
        else:
            failed_tasks.append(task["description"])
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful tasks: {successful_tasks}/{len(tasks)}")
    
    if failed_tasks:
        print(f"❌ Failed tasks: {len(failed_tasks)}")
        for task in failed_tasks:
            print(f"   • {task}")
    
    print(f"\n📁 Output files should be in:")
    print(f"   llm-corrected-results/original/{year}/")
    print(f"   llm-corrected-results/tesseract/{year}/")
    
    print(f"\n🔍 To check results, run:")
    print(f"   python compare.py --year {year} --page {page:04d}")

if __name__ == "__main__":
    main()