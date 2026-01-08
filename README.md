# Rosenwald Medical Directory OCR & AI Extraction Pipeline

A comprehensive research pipeline for extracting structured data from historical French medical directories (Rosenwald collection, 1887-1949). This project combines traditional OCR with modern large language models to convert historical PDF documents into structured, analyzable data with professional evaluation metrics.

## Overview

This pipeline processes 60+ years of French medical directories through multiple approaches:

1. **PDF Processing**: Convert PDFs to images or extract embedded OCR text
2. **OCR Extraction**: Traditional Tesseract OCR and embedded PDF text extraction  
3. **AI-Powered Structuring**: Multiple LLM models correct errors and extract structured data
4. **Batch Processing**: Industrial-scale processing via OpenAI and Gemini batch APIs
5. **Vision-Based Processing**: Direct image analysis without OCR preprocessing
6. **Quality Evaluation**: Industry-standard WER/CER metrics against golden truth data

## Project Architecture

```
├── pdfs/                              # Source PDF files (1887-1949)
├── rosenwald-images/                  # PDF pages as PNG images
├── rosenwald-original-ocr/            # Embedded PDF OCR text by year
├── rosenwald-tesseract-ocr/           # Tesseract OCR text by year
├── rosenwald-images-150/              # Higher DPI images for production
│
├── llm-corrected-results/             # LLM-corrected structured outputs
│   ├── original/                      # Results from embedded PDF OCR
│   │   ├── gpt-5/                     
│   │   ├── gpt-5-mini/                
│   │   ├── gpt-5-nano/                
│   │   ├── gemini-2.5-pro/            
│   │   └── gemini-2.5-flash/          
│   ├── tesseract/                     # Results from Tesseract OCR
│   └── only-llm/                      # Results from direct image analysis
│
├── golden-truth/                      # Manually verified reference data
├── ocr-no-ad/                         # Raw OCR for baseline comparison
├── compare-results/                   # Evaluation reports (WER/CER metrics)
│
├── batch-gemini/                      # Gemini batch processing (text input)
├── batch-openai/                      # OpenAI batch processing (text input)
├── batch-gemini-image/                # Gemini vision batch (image input)
├── batch-openai-image/                # OpenAI vision batch (image input)
├── batch-gemini-image-text/           # Gemini multimodal (image + OCR)
├── batch-openai-image-text/           # OpenAI multimodal (image + OCR)
├── batch-gemini-image-text-production/ # Production-scale multimodal processing
│
├── pdf2png.py                         # PDF to PNG conversion
├── extract-existing-ocr.py            # Extract embedded PDF OCR text
├── ocr.py                             # Single image OCR
├── ocr-batch.py                       # Batch OCR processing
├── llm-correction.py                  # LLM correction pipeline (interactive)
├── image-input.py                     # Direct image analysis (vision APIs)
├── compare.py                         # Comprehensive OCR evaluation
├── compare_two_tsvs.py                # Compare two TSV files
├── run_all_corrections.py             # Run all model corrections for one page
├── demo.py                            # API availability testing
│
├── instructions-raw.txt               # LLM instructions for OCR text input
├── instructions-image-input.txt       # LLM instructions for image input
├── instructions-example-output.tsv    # Example structured output format
└── requirements.txt                   # Python dependencies
```

## Key Features

### Multiple Processing Approaches

1. **Text-Based OCR Correction**: Extract OCR text first, then use LLMs to correct errors
2. **Vision-Based Processing**: LLMs analyze images directly without OCR preprocessing
3. **Multimodal Processing**: Combine OCR text + images for best accuracy
4. **Interactive Processing**: Single-page or batch processing via command-line
5. **Industrial Batch Processing**: Process thousands of pages via cloud batch APIs

### Supported AI Models

- **OpenAI**: GPT-5, GPT-5-mini, GPT-5-nano (text & vision)
- **Google**: Gemini 2.5 Pro, Gemini 2.5 Flash (text & vision)

### Professional Evaluation

- **WER (Word Error Rate)**: Industry-standard word-level accuracy
- **CER (Character Error Rate)**: Character-level precision metrics
- **Alignment Visualization**: Detailed error analysis with insertions/deletions/substitutions
- **Comparative Analysis**: Compare multiple models and approaches

## Installation

### Prerequisites

```bash
# Python 3.8+ required
python --version

# System dependencies (macOS)
brew install tesseract tesseract-lang
brew install poppler  # for pdftoppm

# Verify Tesseract with French language pack
tesseract --list-langs  # should include 'fra'
```

### Python Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Or use conda/venv
conda create -n rosenwald python=3.11
conda activate rosenwald
pip install -r requirements.txt
```

### API Configuration

```bash
# Required for GPT models
export OPENAI_API_KEY="your-openai-api-key"

# Optional for Gemini models  
export GEMINI_API_KEY="your-google-api-key"

# Test API availability
python demo.py
```

## Quick Start

### 1. Test API Configuration

```bash
python demo.py
# ✅ Both APIs are working! Full pipeline functionality available.
```

### 2. Extract OCR Text from PDF

```bash
# Extract embedded OCR text from PDF
python extract-existing-ocr.py --year 1887

# Or use Tesseract on images
python pdf2png.py --year 1887 --dpi 300
python ocr-batch.py 1887 --language fra
```

### 3. LLM-Powered Correction (Interactive)

```bash
# Best performance: Original OCR + GPT-5
python llm-correction.py --year 1887 --pages 32 --model gpt-5 --ocr-source original

# Alternative: Gemini 2.5 Pro
python llm-correction.py --year 1887 --pages 32 --model gemini-2.5-pro --ocr-source original

# Process multiple pages
python llm-correction.py --year 1887 --pages 1-50 --model gpt-5 --ocr-source original
```

### 4. Direct Image Analysis (Vision)

```bash
# Process image directly with vision models
python image-input.py --year 1887 --page 32 --model gpt-5
python image-input.py --year 1887 --page 32 --model gemini-2.5-flash
```

### 5. Evaluate Results

```bash
# Compare against golden truth
python compare.py --year 1887 --page 0032

# Compare specific model
python compare.py --year 1887 --page 0032 --model gpt-5 --ocr-source original
```

## Processing Workflows

### Workflow 1: Interactive Processing (Small Scale)

For processing individual pages or small batches:

```bash
# 1. Extract OCR text
python extract-existing-ocr.py --year 1887

# 2. Process with LLM
python llm-correction.py --year 1887 --pages 32 --model gpt-5 --ocr-source original

# 3. Evaluate quality
python compare.py --year 1887 --page 0032 --model gpt-5
```

### Workflow 2: Batch API Processing (Large Scale)

For processing hundreds or thousands of pages:

```bash
# Navigate to batch processing directory
cd batch-openai  # or batch-gemini, batch-gemini-image, etc.

# 1. Build batch request file
python build-batch-file.py --source original --model gpt-5.2-2025-12-11

# 2. Submit batch job
python run_openai_batch.py original-requests-gpt-5.2-2025-12-11.jsonl

# 3. Check status
python check_batch_status.py original-requests-gpt-5.2-2025-12-11.jsonl

# 4. Extract results when complete
python extract_batch_output.py original-requests-gpt-5.2-2025-12-11.jsonl
```

### Workflow 3: Vision-Based Processing

For direct image analysis without OCR:

```bash
cd batch-gemini-image

# 1. Upload images to Gemini
python upload_gemini_images.py

# 2. Build batch requests
python build-gemini-image-batch-file.py --model gemini-3-flash-preview

# 3. Submit and monitor
python run_gemini_image_batch.py image-requests-gemini-3-flash-preview.jsonl
python check_gemini_image_batch_status.py image-requests-gemini-3-flash-preview.jsonl

# 4. Extract results
python extract_gemini_image_batch_output.py image-requests-gemini-3-flash-preview.jsonl
```

### Workflow 4: Multimodal Processing (Best Accuracy)

For combining OCR text with image analysis:

```bash
cd batch-gemini-image-text-production

# 1. Build multimodal batch requests
python build-gemini-image-text-batch-file.py --source original

# 2. Process via batch API
# (Follow similar steps as vision-based workflow)
```

## Core Scripts Reference

### PDF & OCR Processing

#### pdf2png.py
Convert PDF pages to PNG images.

```bash
# Convert entire PDF
python pdf2png.py --year 1887 --dpi 300

# Convert specific pages
python pdf2png.py --year 1887 --pages 1-50 --dpi 150
```

#### extract-existing-ocr.py
Extract embedded OCR text from PDFs using PyMuPDF.

```bash
# Extract from year directory
python extract-existing-ocr.py --year 1887

# Extract from specific PDF
python extract-existing-ocr.py --pdf pdfs/1887.pdf --output rosenwald-original-ocr/

# Get PDF information only
python extract-existing-ocr.py --info pdfs/1887.pdf
```

#### ocr-batch.py
Batch Tesseract OCR processing.

```bash
# Process all images in year directory
python ocr-batch.py 1887 --language fra --psm 3

# Options:
#   --language: Tesseract language code (default: fra)
#   --psm: Page segmentation mode (default: 3)
```

#### ocr.py
Single image OCR processing.

```bash
# Process single image
python ocr.py 1887 32 --language fra --psm 3
```

### LLM Processing

#### llm-correction.py
Interactive LLM-powered OCR correction.

```bash
# Process with specific model and OCR source
python llm-correction.py --year 1887 --pages 32 --model gpt-5 --ocr-source original

# Options:
#   --year: Year directory (required)
#   --pages: Single (32), multiple (32,33,34), or range (30-35)
#   --model: gpt-5, gpt-5-mini, gpt-5-nano, gemini-2.5-pro, gemini-2.5-flash
#   --ocr-source: original or tesseract (default: tesseract)
#   --delay: Delay between pages in seconds (default: 2)
```

#### image-input.py
Direct image analysis using vision APIs.

```bash
# Process with OpenAI Vision
python image-input.py --year 1887 --page 32 --model gpt-5

# Process with Gemini Vision
python image-input.py --year 1887 --page 32 --model gemini-2.5-flash

# Process with both models
python image-input.py --year 1887 --page 32 --dual
```

#### run_all_corrections.py
Run all model/source combinations for comprehensive comparison.

```bash
# Process one page with all models
python run_all_corrections.py --year 1887 --page 32

# Options:
#   --dry-run: Show commands without executing
```

### Evaluation & Comparison

#### compare.py
Comprehensive OCR evaluation using WER/CER metrics.

```bash
# Compare all approaches
python compare.py --year 1887 --page 0032

# Compare specific model
python compare.py --year 1887 --page 0032 --model gpt-5 --ocr-source original

# Compare only raw OCR
python compare.py --year 1887 --page 0032 --type raw

# Options:
#   --type: llm, raw, or both (default: both)
#   --ocr-source: original, tesseract, only-llm, or all (default: all)
#   --model: gpt-5, gpt-5-mini, gpt-5-nano, gemini-2.5-pro, gemini-2.5-flash, or all
#   --output-dir: Directory for results (default: compare-results)
```

#### compare_two_tsvs.py
Direct comparison between two TSV files.

```bash
# Compare hypothesis against reference
python compare_two_tsvs.py --hyp golden-truth/my-result.tsv
```

### Utilities

#### demo.py
Test API availability and configuration.

```bash
python demo.py
# Tests both OpenAI and Gemini APIs with actual API calls
```

## Batch Processing Systems

The project includes six specialized batch processing directories for industrial-scale operations:

### Text-Based Batch Processing

- **batch-openai/**: OpenAI batch API for OCR text correction
- **batch-gemini/**: Gemini batch API for OCR text correction

### Vision-Based Batch Processing

- **batch-openai-image/**: OpenAI vision batch for direct image analysis
- **batch-gemini-image/**: Gemini vision batch for direct image analysis

### Multimodal Batch Processing

- **batch-openai-image-text/**: OpenAI multimodal (image + OCR text)
- **batch-gemini-image-text/**: Gemini multimodal (image + OCR text)
- **batch-gemini-image-text-production/**: Production-scale Gemini multimodal processing

Each batch directory contains:
- `build-*-batch-file.py`: Generate batch request JSONL
- `run_*_batch.py`: Submit batch job to API
- `check_*_batch_status.py`: Monitor job progress
- `extract_*_batch_output.py`: Extract and save results
- `rosenwald-benchmark-*.tsv`: Benchmark datasets with year/page/text columns

### Benchmark TSV Format

Batch processing uses TSV files with the following structure:

```tsv
year	page	text
1887	0032	[OCR text content with \n and \t escaped]
1888	0045	[OCR text content...]
```

These benchmark files are created from OCR outputs and used to build batch API requests.

## Output Format

All processing produces structured TSV files with this schema:

```tsv
nom	année	notes	adresse	horaires
Vallois	1848		St-André-des-Arts 50	2 à 4
Ravaux (Mme)	1883		Assomption 75	
Berline Hering (Mme)	1881		Halles 13	
Darcus Richardson	1861		Poisson 3	3 à 4, Exc. Dim
```

### Column Descriptions

| Column | Description | Example |
|--------|-------------|---------|
| **nom** | Doctor's surname (with titles if present) | "Ravaux (Mme)" |
| **année** | Graduation or reference year | "1883" |
| **notes** | Professional titles/affiliations | "Ex-Int. des Hôp." |
| **adresse** | Street address | "St-André-des-Arts 50" |
| **horaires** | Office hours | "Lun. Mer. Ven. 3 à 5" |

## Instruction Templates

The pipeline uses two instruction templates depending on input type:

### instructions-raw.txt
For OCR text input (used by llm-correction.py and text-based batch processing).

Key requirements:
- Correct OCR errors in French historical text
- Extract only medical directory entries (ignore ads/headers)
- Preserve exact spelling, accents, abbreviations
- Handle missing fields gracefully
- Output TSV format without markdown formatting

### instructions-image-input.txt
For image input (used by image-input.py and vision-based batch processing).

Additional requirements:
- Read text directly from historical medical directory images
- Critical column reading order: LEFT column top-to-bottom, THEN RIGHT column
- Handle partially effaced or difficult-to-read text
- Extract from multi-column layouts systematically

Both templates include instructions-example-output.tsv as a format reference.

## Performance Evaluation

The compare.py tool provides comprehensive performance metrics:

### Evaluation Metrics

- **WER (Word Error Rate)**: $\frac{\text{Insertions + Deletions + Substitutions}}{\text{Total Words in Reference}}$
- **CER (Character Error Rate)**: Same formula at character level
- **Alignment Visualization**: Visual comparison showing errors

### Current Performance Results

Based on evaluation against golden truth data:

| Approach | WER | CER | Performance |
|----------|-----|-----|-------------|
| Original/GPT-5 | 0.0936 | 0.0340 | 🏆 **Best Overall** |
| Original/Gemini-2.5-Pro | 0.0936 | 0.0372 | 🥈 **Excellent** |
| Tesseract/Gemini-2.5-Pro | 0.1154 | 0.0438 | 🥉 **Very Good** |
| Raw Original OCR | 0.3528 | 0.1126 | 📊 **Baseline** |
| Raw Tesseract OCR | 0.5067 | 0.2978 | 📊 **Baseline** |

**Key Findings:**
- LLM correction provides **60-80% improvement** over raw OCR
- Original embedded PDF OCR is superior to Tesseract for LLM input
- GPT-5 and Gemini 2.5 Pro achieve nearly identical top-tier performance
- All tested LLM models significantly outperform raw OCR baselines

## Data Collection Information

### Rosenwald Collection Coverage

- **Time Period**: 1887-1949 (with gaps in publication years)
- **Total PDFs**: 47 historical medical directory volumes
- **Content**: French medical practitioners with contact information
- **Maximum Pages**: 1,622 pages (well within 9,999 page limit)

### Golden Truth Dataset

The golden-truth directory contains manually verified reference data used for evaluation:
- Format: TSV files matching output schema
- Naming: {year}-page-{NNNN}.tsv
- Purpose: Ground truth for WER/CER calculations

### OCR Baseline Dataset

The ocr-no-ad directory contains raw OCR text without ads/headers:
- Purpose: Baseline comparison for raw OCR accuracy
- Formats: {year}-page-{NNNN}-original.txt and {year}-page-{NNNN}-tesseract.txt

## Research Applications

### Quantitative Analysis
- **OCR Correction Performance**: Objective evaluation of LLM-based OCR correction
- **Model Comparison**: Systematic comparison of multiple AI models
- **Accuracy Benchmarking**: Industry-standard WER/CER metrics

### Historical Research
Structured data enables analysis of:
- Geographic distribution of medical practitioners in France (1887-1949)
- Evolution of medical specializations over 60+ years
- Historical medical education trends through graduation years
- Socioeconomic patterns via practice locations
- Professional affiliations and hospital networks

### Technical Contributions
- **Evaluation Framework**: Standardized methodology for historical OCR assessment
- **Multi-Modal Pipeline**: Production-ready system supporting multiple AI providers
- **Batch Processing Architecture**: Scalable processing of large document collections
- **Vision vs. OCR Comparison**: Comparative analysis of different extraction approaches

## Advanced Configuration

### Page Numbering System

The pipeline uses 4-digit zero-padded page numbers (0001-9999):

```
1887-page-0001.png
1887-page-0032.txt
1887-page-0149.tsv
```

**Important**: PDFs must contain fewer than 10,000 pages. The Rosenwald collection (max 1,622 pages) is well within this limit.

### DPI Settings

- **Standard**: 300 DPI for general processing
- **Production**: 150 DPI for large-scale operations (rosenwald-images-150)
- **High Quality**: 600 DPI for difficult documents

### Tesseract Configuration

- **Language**: Default `fra` (French)
- **PSM (Page Segmentation Mode)**: Default `3` (fully automatic)
- Configurable via --language and --psm options

## Troubleshooting

### Common Issues

**API Rate Limits**
```bash
# Add delay between pages
python llm-correction.py --year 1887 --pages 1-50 --delay 3
```

**Missing API Keys**
```bash
# Verify environment variables
echo $OPENAI_API_KEY
echo $GEMINI_API_KEY

# Test configuration
python demo.py
```

**Tesseract Language Pack Missing**
```bash
# macOS
brew install tesseract-lang

# Verify installation
tesseract --list-langs  # should include 'fra'
```

**Large PDF Processing**
```bash
# Process in chunks
python llm-correction.py --year 1925 --pages 1-100 --model gpt-5
python llm-correction.py --year 1925 --pages 101-200 --model gpt-5
```

### Resuming Processing

All scripts handle existing files gracefully:
- OCR extraction skips already-processed pages
- LLM correction can resume interrupted batches
- Batch processing can be re-run safely

### Verification

```bash
# Count processed files
find llm-corrected-results/original/gpt-5/ -name "*.tsv" | wc -l

# Check specific year completion
ls llm-corrected-results/original/gpt-5/1887/*.tsv | wc -l

# Verify output format
head llm-corrected-results/original/gpt-5/1887/1887-page-0032.tsv
```

## Development

### Project Structure Principles

- **Separation of Concerns**: Interactive vs. batch processing
- **Multiple Approaches**: Text-based, vision-based, and multimodal
- **Comprehensive Logging**: All operations logged for debugging
- **Professional Evaluation**: Industry-standard metrics throughout

### Key Dependencies

```
openai>=1.3.0              # OpenAI GPT models
google-genai>=0.3.0        # Google Gemini models
PyMuPDF>=1.22.0            # PDF text extraction
pytesseract>=0.3.10        # Tesseract OCR wrapper
jiwer>=3.0.0               # WER/CER calculation
tqdm>=4.65.0               # Progress bars
```

See requirements.txt for complete dependency list.


## Contact

For questions, feedback, or collaboration:

**Ren Yi**  
Email: [renyi1006@gmail.com](mailto:renyi1006@gmail.com)

