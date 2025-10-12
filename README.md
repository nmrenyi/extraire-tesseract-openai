# Rosenwald Medical Directory OCR Project

A comprehensive OCR processing and evaluation pipeline for historical French medical directories from the Rosenwald collection (1887-1949). This project converts PDF documents to structured data using multiple OCR engines and advanced language models for error correction, with professional evaluation tools for performance analysis.

## Overview

This project processes historical French medical directories through a complete pipeline:

1. **PDF to Image Conversion**: Convert PDF pages to high-quality PNG images
2. **Dual OCR Extraction**: 
   - Extract original embedded OCR text directly from PDFs using PyMuPDF
   - Use Tesseract to extract raw text from images for comparison and improved accuracy
3. **AI-Powered Data Structuring**: Use multiple LLM models (GPT-5 series, Gemini 2.5) to correct OCR errors and extract structured medical directory data
4. **Performance Evaluation**: Comprehensive comparison tools to evaluate and optimize OCR correction performance

## Project Structure

```
├── pdfs/                           # Source PDF files (1887-1949)
├── rosenwald-images/               # Converted PNG images by year
├── rosenwald-tesseract-ocr/        # Tesseract OCR text output by year
├── rosenwald-original-ocr/         # Original embedded PDF OCR text by year
├── ocr-no-ad/                      # Raw OCR results without ads/headers
├── llm-corrected-results/          # LLM-corrected structured data
│   ├── tesseract/                  # Results from Tesseract OCR input
│   │   ├── gpt-5/                  # GPT-5 model results
│   │   ├── gpt-5-mini/             # GPT-5-mini model results
│   │   ├── gpt-5-nano/             # GPT-5-nano model results
│   │   ├── gemini-2.5-pro/         # Gemini 2.5 Pro model results
│   │   └── gemini-2.5-flash/       # Gemini 2.5 Flash model results
│   └── original/                   # Results from original PDF OCR input
├── golden-truth/                   # Manually verified reference data
├── compare-results/                # OCR evaluation reports and metrics
├── env/                           # Python virtual environment
├── pdf2png.py                     # PDF to PNG conversion script
├── extract-existing-ocr.py        # Extract original embedded PDF OCR text
├── ocr-batch.py                   # Batch OCR processing script
├── ocr.py                         # Single image OCR script
├── llm-correction.py              # LLM-powered OCR correction pipeline
├── compare.py                     # Comprehensive OCR evaluation tool
├── demo.py                        # Dual API availability testing
├── instructions-raw.txt           # LLM correction instructions
├── instructions-example-output.tsv # Example structured output format
├── prompt.txt                     # Legacy AI prompt (deprecated)
└── prompt-example.tsv             # Legacy example format (deprecated)
```

## Features

- **Multi-Engine OCR Processing**: Tesseract and original PDF OCR extraction
- **Advanced LLM Correction**: GPT-5 series and Gemini 2.5 series model support
- **Comprehensive Evaluation**: Industry-standard WER/CER metrics with detailed alignment analysis
- **Professional Pipeline**: Clean separation following AI model best practices
- **Dual API Support**: OpenAI and Google AI integration with availability testing
- **Progress Tracking**: Visual progress bars and comprehensive logging
- **Flexible Configuration**: Customizable parameters for all processing stages
- **Performance Optimization**: Automatic model selection based on evaluation results

## Requirements

- Python 3.11+
- Tesseract OCR with French language pack
- PyMuPDF (fitz) for PDF text extraction  
- OpenAI API access (for GPT models)
- Google AI API access (optional, for Gemini models)
- jiwer library for OCR evaluation metrics
- Dependencies listed in the virtual environment

## PDF Limitations

⚠️ **Important**: PDFs must contain **fewer than 10,000 pages** due to the 4-digit page numbering system used throughout the pipeline (0001-9999). 

- **Supported**: PDFs with 1-9,999 pages ✅
- **Not supported**: PDFs with 10,000+ pages ❌

The Rosenwald collection (1887-1949) contains 47 PDFs with a maximum of 1,622 pages, well within this limit. If you need to process larger documents, consider splitting them into smaller PDFs first.

## Quick Start

### 1. API Availability Testing
Test your API configurations before processing:

```bash
# Test both OpenAI and Gemini APIs
python demo.py

# Expected output:
# ✅ Both APIs are working! Full pipeline functionality available.
```

### 2. OCR Performance Evaluation
Compare OCR correction performance across all models:

```bash
# Comprehensive comparison (default: all models, all OCR sources, LLM + raw)
python compare.py

# Compare specific model performance
python compare.py --model gemini-2.5-pro

# Compare only raw OCR accuracy
python compare.py --type raw

# Results show performance metrics:
# Type       Source                    WER        CER       
# -------------------------------------------------------
# LLM        original/gpt-5            0.0936     0.0340    ⭐ Best
# LLM        original/gemini-2.5-pro   0.0936     0.0372    
# Raw OCR    original                  0.3528     0.1126    Baseline
```

### 3. LLM-Powered OCR Correction
Process documents using the best-performing models:

```bash
# Process with top-performing model (Original OCR + GPT-5)
python llm-correction.py --year 1887 --pages 32 --model gpt-5 --ocr-source original

# Batch processing with progress tracking
python llm-correction.py --year 1887 --pages 1-50 --model gemini-2.5-pro
```

## OCR Performance Evaluation

The `compare.py` tool provides comprehensive OCR performance analysis using industry-standard metrics.

### Evaluation Metrics

- **WER (Word Error Rate)**: Percentage of word-level errors compared to reference
- **CER (Character Error Rate)**: Percentage of character-level errors compared to reference
- **Alignment Analysis**: Detailed comparison showing insertions, deletions, and substitutions

### Usage Examples

```bash
# Complete performance analysis (default)
python compare.py
# Compares: All LLM models + Raw OCR vs Golden Truth

# Focus on specific aspects
python compare.py --type llm --model gpt-5           # LLM-only comparison
python compare.py --type raw --ocr-source all        # Raw OCR baseline
python compare.py --ocr-source original --model all  # Original OCR performance

# Different pages/years
python compare.py --year 1888 --page 045
```

### Performance Results

Current evaluation shows clear performance rankings:

| **Approach** | **WER** | **CER** | **Performance** |
|--------------|---------|---------|-----------------|
| Original/GPT-5 | 0.0936 | 0.0340 | 🏆 **Best Overall** |
| Original/Gemini-2.5-Pro | 0.0936 | 0.0372 | 🥈 **Excellent** |
| Tesseract/Gemini-2.5-Pro | 0.1154 | 0.0438 | 🥉 **Very Good** |
| Raw Original OCR | 0.3528 | 0.1126 | 📊 **Baseline** |
| Raw Tesseract OCR | 0.5067 | 0.2978 | 📊 **Baseline** |

**Key Insights:**
- LLM correction provides **60-80% improvement** over raw OCR
- Original PDF OCR provides better input than Tesseract for LLM processing
- GPT-5 and Gemini-2.5-Pro achieve similar top-tier performance
- All LLM models significantly outperform raw OCR baselines

### Output Files

Detailed results are saved to `compare-results/` with:
- Summary tables with WER/CER metrics
- Word-level alignment visualization
- Character-level alignment analysis
- Individual model performance reports

## LLM-Powered OCR Correction

The `llm-correction.py` script provides advanced OCR error correction using state-of-the-art language models. Based on performance evaluation, it supports multiple high-performing models for optimal results.

### Supported Models

#### OpenAI GPT-5 Series (Recommended)
- **gpt-5**: 🏆 Top performer with original OCR (0.0936 WER)
- **gpt-5-mini**: Balanced performance and cost
- **gpt-5-nano**: Fastest processing for high-volume tasks

#### Google Gemini 2.5 Series (High Performance)
- **gemini-2.5-pro**: 🥈 Excellent accuracy (0.0936 WER with original OCR)
- **gemini-2.5-flash**: Fast processing with good results

*Performance metrics based on evaluation against golden truth data*

### API Setup and Testing

```bash
# Set API keys
export OPENAI_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-google-api-key"  # Optional for Gemini models

# Test API availability
python demo.py
# ✅ OpenAI GPT-5 series is working
# ✅ Gemini 2.5 series is working
# ✅ Both APIs are working! Full pipeline functionality available.
```

### Usage Examples

#### Optimal Performance (Based on Evaluation):
```bash
# Best overall performance: Original OCR + GPT-5
python llm-correction.py --year 1887 --pages 32 --model gpt-5 --ocr-source original

# Alternative high performer: Original OCR + Gemini 2.5 Pro  
python llm-correction.py --year 1887 --pages 32 --model gemini-2.5-pro --ocr-source original
```

#### Standard Processing:
```bash
# Process specific pages for a year
python llm-correction.py --year 1887 --pages 32

# Process multiple pages with specific model
python llm-correction.py --year 1887 --pages 32,33,34 --model gpt-5-mini

# Process a page range using Tesseract OCR source
python llm-correction.py --year 1887 --pages 30-35 --ocr-source tesseract

# Batch processing with delay for rate limiting
python llm-correction.py --year 1887 --pages 1-50 --delay 2.0
```

### Command Line Options

- `--year`: Target year directory (required)
- `--pages`: Pages to process - single (32), multiple (32,33,34), or range (30-35)
- `--model`: LLM model selection (default: gpt-5-nano)
  - Recommended: `gpt-5` or `gemini-2.5-pro` for best accuracy
  - Fast: `gpt-5-nano` or `gemini-2.5-flash` for speed
- `--ocr-source`: OCR source - 'tesseract' or 'original' (default: tesseract)
  - Recommended: `original` for better accuracy (see evaluation results)
- `--delay`: Delay between pages in seconds (default: 2)

### Output Structure

Results are organized by OCR source and model:
```
llm-corrected-results/
├── original/
│   ├── gpt-5/1887/1887-page-032.tsv          # 🏆 Best performance
│   └── gemini-2.5-pro/1887/1887-page-032.tsv # 🥈 Excellent alternative
└── tesseract/
    ├── gpt-5/1887/1887-page-032.tsv
    └── gemini-2.5-flash/1887/1887-page-032.tsv
```

### Output Format

Results are saved as TSV files with the following structure:
```
nom|année|notes|adresse|horaires
Vallois|1848||St-André-des-Arts 50|2 à 4
Ravaux (Mme)|1883||Assomption 75|
```

### Error Handling

- **Exponential Backoff**: Automatic retry with increasing delays
- **Comprehensive Logging**: All operations logged to `llm_correction.log`
- **Progress Tracking**: Visual progress bars for multi-page processing
- **Graceful Failures**: Individual page failures don't stop batch processing

### System Dependencies

```bash
# macOS (via Homebrew)
brew install tesseract tesseract-lang
brew install poppler  # for pdftoppm

# Verify Tesseract installation
tesseract --list-langs  # Should include 'fra'
```

## Advanced Usage

### 1. PDF to Image Conversion

Convert PDF files to PNG images:

```bash
python pdf2png.py --year 1887 --dpi 300
```

This creates images in `rosenwald-images/1887/` with naming pattern `1887-page-X.png`.

### 2. Original OCR Text Extraction

Extract embedded OCR text directly from PDF files:

```bash
# Extract OCR text from all PDFs in a year directory
python extract-existing-ocr.py --year 1887
# Process a single PDF file  
python extract-existing-ocr.py --pdf path/to/file.pdf --output output_directory/
# Get PDF information only
python extract-existing-ocr.py --info path/to/file.pdf
```

This extracts the original embedded OCR text to `rosenwald-original-ocr/1887/` with files named `1887-page-001.txt`, etc.

### 3. Tesseract OCR Text Extraction

#### Single Image OCR
```bash
python ocr.py path/to/image.png [output.txt] --language fra --psm 3
```

#### Batch OCR Processing
```bash
python ocr-batch.py 1887 --language fra --psm 3
```

This processes all PNG files in `rosenwald-images/1887/` and outputs text files to `rosenwald-tesseract-ocr/1887/`.

**Setup:**
```bash
# Set OpenAI API key (required for GPT models)
export OPENAI_API_KEY="your-openai-api-key"

# Optional: For Gemini models  
export GEMINI_API_KEY="your-google-api-key"

# Test API availability
python demo.py
```

## Complete Workflow Example

Here's a complete workflow using the best-performing configuration:

```bash
# 1. Test API availability
python demo.py

# 2. Evaluate current performance (optional but recommended)
python compare.py --year 1887 --page 032

# 3. Process documents with optimal settings
python llm-correction.py --year 1887 --pages 1-50 --model gpt-5 --ocr-source original

# 4. Verify results quality
python compare.py --year 1887 --page 001  # Check first processed page
```

### 5. Legacy AI Data Extraction

The project also includes a legacy prompt system for reference:

- **Input**: Raw OCR text with potential errors
- **Processing**: AI corrects OCR errors and identifies medical entries
- **Output**: Structured TSV data with columns: `nom`, `année`, `notes`, `adresse`, `horaires`

See `instructions-raw.txt` and `instructions-example-output.tsv` for the current prompt system.

## Data Structure

The extracted medical directory entries follow this structure:

| Column | Description | Example |
|--------|-------------|---------|
| nom | Doctor's surname | "Vallois" |
| année | Graduation/reference year | "1848" |
| notes | Professional titles/affiliations | "Ex-Int. des Hôp." |
| adresse | Street address | "St-André-des-Arts 50" |
| horaires | Office hours | "Lun. Mer. Ven. 3 à 5" |

## OCR Quality Assessment

The project provides comprehensive tools for comparing OCR methods:

### OCR Sources Comparison

| **Method** | **Speed** | **Accuracy** | **Use Case** |
|------------|-----------|--------------|--------------|
| **Original PDF OCR** | ⚡ Fast | 🎯 Higher (0.35 WER) | Production processing |
| **Tesseract OCR** | 🐌 Slower | 📊 Baseline (0.51 WER) | Fresh processing, comparison |

### LLM Correction Impact

All LLM models provide substantial improvements over raw OCR:

- **Best Case**: 73% WER reduction (Original OCR + GPT-5: 0.35 → 0.09)
- **Typical**: 60-70% WER reduction across all model combinations
- **Worst Case**: Still 40%+ improvement with any LLM model

### Data Directories

- `ocr-no-ad/`: Raw OCR text files for baseline comparison
- `golden-truth/`: Manually verified reference data for evaluation
- `compare-results/`: Detailed performance analysis reports

## OCR Configuration

The project supports various Tesseract configurations:

- **Language**: Default French (`fra`), configurable
- **Page Segmentation Mode (PSM)**: Default `3` (fully automatic), configurable
- **DPI**: Default `300` for high-quality conversion

## Collection Coverage

The project processes Rosenwald medical directories spanning:
- **Years**: 1887-1949 (with some gaps)
- **Total PDFs**: 47 directory volumes
- **Content**: French medical practitioners with addresses and office hours

## Development

The project uses a Python virtual environment located in `env/`. All required dependencies are pre-installed in this environment.

### Key Scripts

- `pdf2png.py`: High-level PDF processing with progress tracking
- `extract-existing-ocr.py`: Extract original embedded OCR text from PDFs
- `ocr-batch.py`: Efficient batch OCR with error handling
- `ocr.py`: Core OCR functionality for individual images
- `llm-correction.py`: LLM-powered OCR correction pipeline with 5 model support
- `compare.py`: Comprehensive OCR evaluation tool with WER/CER metrics
- `demo.py`: Dual API availability testing (OpenAI + Google AI)

## Research Applications

This pipeline enables comprehensive historical analysis:

### Quantitative Research
- **Performance Metrics**: 60-80% OCR error reduction through LLM correction
- **Model Comparison**: Objective evaluation of 5 different LLM models
- **OCR Baseline Analysis**: Comparison of traditional vs. modern OCR methods

### Historical Research Applications

### Historical Research Applications

Final structured data enables historical analysis of:
- Medical practitioner distribution in France
- Evolution of medical specializations over 60+ years (1887-1949)
- Geographic patterns of medical practice
- Historical medical education trends
- Socioeconomic patterns in medical practice locations

### Technical Contributions
- **OCR Evaluation Framework**: Standardized comparison methodology for historical documents
- **Multi-Model Pipeline**: Production-ready system supporting multiple AI providers
- **Performance Benchmarking**: Quantitative assessment of modern LLM capabilities on historical text
