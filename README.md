# Rosenwald Medical Directory OCR Project

A comprehensive OCR and data extraction pipeline for processing historical French medical directories from the Rosenwald collection (1887-1949). This project converts PDF documents to structured data using Tesseract OCR and OpenAI's language models for error correction and data formatting.

## Overview

This project processes historical French medical directories through a three-stage pipeline:

1. **PDF to Image Conversion**: Convert PDF pages to high-quality PNG images
2. **OCR Text Extraction**: 
   - Extract original embedded OCR text directly from PDFs using PyMuPDF
   - Use Tesseract to extract raw text from images for comparison and improved accuracy
3. **AI-Powered Data Structuring**: Use OpenAI GPT models to correct OCR errors and extract structured medical directory data

## Project Structure

```
├── pdfs/                           # Source PDF files (1887-1949)
├── rosenwald-images/               # Converted PNG images by year
├── rosenwald-tesseract-ocr/        # Tesseract OCR text output by year
├── rosenwald-original-ocr/         # Original embedded PDF OCR text by year
├── llm-corrected-results/          # LLM-corrected structured data
│   ├── tesseract/                  # Results from Tesseract OCR input
│   │   ├── gpt-5/                  # GPT-5 model results
│   │   ├── gpt-5-mini/             # GPT-5-mini model results
│   │   └── gpt-5-nano/             # GPT-5-nano model results
│   └── original/                   # Results from original PDF OCR input
├── env/                           # Python virtual environment
├── pdf2png.py                     # PDF to PNG conversion script
├── extract_existing_ocr.py        # Extract original embedded PDF OCR text
├── ocr_batch.py                   # Batch OCR processing script
├── ocr.py                         # Single image OCR script
├── llm_correction.py              # LLM-powered OCR correction pipeline
├── demo.py                        # OpenAI API demonstration
├── instructions-raw.txt           # LLM correction instructions
├── example-output.tsv             # Example structured output format
├── prompt.txt                     # Legacy AI prompt (deprecated)
└── prompt-example.tsv             # Legacy example format (deprecated)
```

## Features

- **Batch PDF Processing**: Convert entire yearly directories from PDF to PNG format
- **Dual OCR Processing**: Extract text using both Tesseract and original embedded PDF OCR
- **LLM-Powered Correction**: Advanced language models (GPT-5 series, Gemini 2.5) for error correction
- **Progress Tracking**: Visual progress bars for long-running operations
- **Structured Output**: Extract medical directory entries into TSV format with organized folder structure
- **Professional Pipeline**: Clean separation of instructions and input following OpenAI best practices
- **Flexible Configuration**: Customizable OCR parameters and LLM model selection
- **Comprehensive Error Handling**: Automatic retries, exponential backoff, and detailed logging

## Requirements

- Python 3.11+
- Tesseract OCR with French language pack
- PyMuPDF (fitz) for PDF text extraction
- OpenAI API access
- Dependencies listed in the virtual environment

## LLM-Powered OCR Correction

The `llm_correction.py` script provides advanced OCR error correction using state-of-the-art language models. It processes raw OCR text and extracts structured medical directory data.

### Supported Models

#### OpenAI GPT-5 Series (Primary)
- **gpt-5**: Latest flagship model with highest accuracy
- **gpt-5-mini**: Balanced performance and cost
- **gpt-5-nano**: Fastest processing for high-volume tasks

#### Google Gemini 2.5 Series (Optional)
- **gemini-2.5-pro**: High-capability model for complex corrections
- **gemini-2.5-flash**: Fast processing alternative

### Usage Examples

#### Process specific pages for a year:
```bash
python llm_correction.py --year 1887 --pages 32
```

#### Process multiple pages with specific model:
```bash
python llm_correction.py --year 1887 --pages 32,33,34 --model gpt-5-mini
```

#### Process a page range using Tesseract OCR source:
```bash
python llm_correction.py --year 1887 --pages 30-35 --ocr-source tesseract
```

#### Use original PDF OCR with Gemini model:
```bash
python llm_correction.py --year 1887 --pages 32 --model gemini-2.5-pro --ocr-source original
```

### Command Line Options

- `--year`: Target year directory (required)
- `--pages`: Pages to process - single (32), multiple (32,33,34), or range (30-35)
- `--model`: LLM model selection (default: gpt-5-nano)
- `--ocr-source`: OCR source - 'tesseract' or 'original' (default: tesseract)
- `--delay`: Delay between pages in seconds (default: 2)

### Output Format

Results are saved as TSV files with the following structure:
```
nom|année|notes|adresse|horaires
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

## Usage

### 1. PDF to Image Conversion

Convert PDF files to PNG images:

```bash
python pdf2png.py --year 1887 --dpi 300
```

This creates images in `rosenwald-images/1887/` with naming pattern `1887-page-X.png`.

### 2. Original OCR Text Extraction

Extract embedded OCR text directly from PDF files:

```bash
# Extract original OCR from a specific year
python extract_existing_ocr.py --year 1887

# Extract from specific PDF file
python extract_existing_ocr.py --pdf path/to/file.pdf --output output_directory/

# Show PDF information
python extract_existing_ocr.py --info path/to/file.pdf
```

This extracts the original embedded OCR text to `rosenwald-original-ocr/1887/` with files named `1887-page-001.txt`, etc.

### 3. Tesseract OCR Text Extraction

#### Single Image OCR
```bash
python ocr.py path/to/image.png [output.txt] --language fra --psm 3
```

#### Batch OCR Processing
```bash
python ocr_batch.py 1887 --language fra --psm 3
```

This processes all PNG files in `rosenwald-images/1887/` and outputs text files to `rosenwald-tesseract-ocr/1887/`.

### 4. LLM-Powered OCR Correction

Process OCR text through advanced language models to correct errors and extract structured medical directory data:

```bash
# Process single page with GPT-5-nano (fastest)
python llm_correction.py --year 1887 --pages 32 --model gpt-5-nano

# Process multiple pages with GPT-5-mini (balanced)
python llm_correction.py --year 1887 --pages 1-10,50,100-105 --model gpt-5-mini

# Use original OCR instead of Tesseract
python llm_correction.py --year 1887 --pages 32 --ocr-source original

# Process with delay to avoid rate limits
python llm_correction.py --year 1887 --pages 1-50 --delay 2.0
```

**Available Models:**
- **GPT-5 series**: `gpt-5`, `gpt-5-mini`, `gpt-5-nano`
- **Gemini 2.5 series**: `gemini-2.5-pro`, `gemini-2.5-flash` (optional)

**Features:**
- **Clean API separation**: Uses `instructions` + `input` parameters following OpenAI docs
- **Organized output**: Results saved to `llm-corrected-results/{ocr_source}/{model}/{year}/`
- **Error handling**: Automatic retries with exponential backoff
- **Progress tracking**: Real-time progress bars and comprehensive logging
- **Dual OCR support**: Works with both Tesseract and original PDF OCR

**Setup:**
```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-openai-api-key"

# Optional: For Gemini models
export GOOGLE_API_KEY="your-google-api-key"
```

### 5. Legacy AI Data Extraction

The project also includes a legacy prompt system for reference:

- **Input**: Raw OCR text with potential errors
- **Processing**: AI corrects OCR errors and identifies medical entries
- **Output**: Structured TSV data with columns: `nom`, `année`, `notes`, `adresse`, `horaires`

See `instructions-raw.txt` and `example-output.tsv` for the current prompt system.

## Data Structure

The extracted medical directory entries follow this structure:

| Column | Description | Example |
|--------|-------------|---------|
| nom | Doctor's surname | "Vallois" |
| année | Graduation/reference year | "1848" |
| notes | Professional titles/affiliations | "Ex-Int. des Hôp." |
| adresse | Street address | "St-André-des-Arts 50" |
| horaires | Office hours | "Lun. Mer. Ven. 3 à 5" |

## OCR Comparison

The project provides two different OCR extraction methods:

### Original PDF OCR (`rosenwald-original-ocr/`)
- **Source**: Embedded OCR text already present in PDF files
- **Pros**: Fast extraction, preserves original digitization quality
- **Cons**: May contain embedded errors from original scanning process
- **Tool**: `extract_existing_ocr.py`

### Tesseract OCR (`rosenwald-tesseract-ocr/`)
- **Source**: Fresh OCR processing of PNG images using Tesseract
- **Pros**: Modern OCR engine, customizable parameters, potential accuracy improvements
- **Cons**: Slower processing, requires image conversion step
- **Tool**: `ocr_batch.py` / `ocr.py`

Both outputs can be compared and used as input for the AI data extraction pipeline to achieve optimal results.

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
- `extract_existing_ocr.py`: Extract original embedded OCR text from PDFs
- `ocr_batch.py`: Efficient batch OCR with error handling
- `ocr.py`: Core OCR functionality for individual images
- `demo.py`: OpenAI API integration example

## Output

Final structured data enables historical analysis of:
- Medical practitioner distribution in France
- Evolution of medical specializations
- Geographic patterns of medical practice
- Historical medical education trends
