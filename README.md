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
├── pdfs/                    # Source PDF files (1887-1949)
├── rosenwald-images/        # Converted PNG images by year
├── rosenwald-tesseract-ocr/ # Tesseract OCR text output by year
├── rosenwald-original-ocr/  # Original embedded PDF OCR text by year
├── env/                    # Python virtual environment
├── convert_pdfs.py         # PDF to PNG conversion script
├── extract_existing_ocr.py # Extract original embedded PDF OCR text
├── batch_ocr.py           # Batch OCR processing script
├── ocr.py                 # Single image OCR script
├── demo.py                # OpenAI API demonstration
├── prompt.txt             # AI prompt for data extraction
└── prompt-example.tsv     # Example output format
```

## Features

- **Batch PDF Processing**: Convert entire yearly directories from PDF to PNG format
- **OCR Processing**: Extract text from images using Tesseract with French language support
- **Progress Tracking**: Visual progress bars for long-running operations
- **Structured Output**: Extract medical directory entries into TSV format
- **Error Correction**: AI-powered correction of OCR errors and data formatting
- **Flexible Configuration**: Customizable OCR parameters (language, page segmentation mode, DPI)

## Requirements

- Python 3.11+
- Tesseract OCR with French language pack
- PyMuPDF (fitz) for PDF text extraction
- OpenAI API access
- Dependencies listed in the virtual environment

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
python convert_pdfs.py --year 1887 --dpi 300
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
python batch_ocr.py 1887 --language fra --psm 3
```

This processes all PNG files in `rosenwald-images/1887/` and outputs text files to `rosenwald-tesseract-ocr/1887/`.

### 4. AI Data Extraction

The project includes a sophisticated prompt system for extracting structured medical directory data:

- **Input**: Raw OCR text with potential errors
- **Processing**: AI corrects OCR errors and identifies medical entries
- **Output**: Structured TSV data with columns: `nom`, `année`, `notes`, `adresse`, `horaires`

See `prompt.txt` for the complete AI prompt and `prompt-example.tsv` for expected output format.

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
- **Tool**: `batch_ocr.py` / `ocr.py`

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

- `convert_pdfs.py`: High-level PDF processing with progress tracking
- `extract_existing_ocr.py`: Extract original embedded OCR text from PDFs
- `batch_ocr.py`: Efficient batch OCR with error handling
- `ocr.py`: Core OCR functionality for individual images
- `demo.py`: OpenAI API integration example

## Output

Final structured data enables historical analysis of:
- Medical practitioner distribution in France
- Evolution of medical specializations
- Geographic patterns of medical practice
- Historical medical education trends
