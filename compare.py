import jiwer
import argparse
import os
from pathlib import Path


def get_hypothesis(ocr_source: str, model: str, year: str, page: str) -> str:
    """Load hypothesis text from LLM corrected results."""
    # Construct path to LLM corrected results
    result_path = f"llm-corrected-results/{ocr_source}/{model}/{year}/{year}-page-{page.zfill(4)}.tsv"
    
    with open(result_path, "r", encoding="utf-8") as f:
        content = f.read().strip().replace("\t", " ")
        # For TSV files, skip the first line (header)
        return ' '.join(content.split('\n')[1:])


def get_raw_ocr_hypothesis(ocr_type: str, year: str, page: str) -> str:
    """Load hypothesis text from raw OCR results in ocr-no-ad directory."""
    result_path = f"ocr-no-ad/{year}-page-{page.zfill(4)}-{ocr_type}.txt"
    
    with open(result_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        # For raw OCR text files, use all content
        return ' '.join(content.split('\n'))


def get_reference(year: str, page: str) -> str:
    """Load reference (golden truth) text from golden-truth directory."""
    with open(f'golden-truth/{year}-page-{page.zfill(4)}.tsv', 'r', encoding='utf-8') as f:
        return ' '.join(f.read().strip().replace("\t", " ").split('\n')[1:])


def calculate_metrics(reference: str, hypothesis: str, tr_word, tr_char):
    """Calculate WER, MER, and CER metrics."""
    # Word Error Rate (WER) and Match Error Rate (MER)
    word_compare = jiwer.process_words(
        reference=reference,
        hypothesis=hypothesis,
        reference_transform=tr_word,
        hypothesis_transform=tr_word,
    )
    
    # Character Error Rate (CER)
    char_compare = jiwer.process_characters(
        reference=reference,
        hypothesis=hypothesis,
        reference_transform=tr_char,
        hypothesis_transform=tr_char,
    )
    
    return {
        'wer': word_compare.wer,
        'cer': char_compare.cer,
        'word_alignment': jiwer.visualize_alignment(word_compare),
        'char_alignment': jiwer.visualize_alignment(char_compare)
    }


def save_comparison_results(comparison_type: str, source_name: str, year: str, page: str, metrics: dict, output_dir: str):
    """Save comparison results to file."""
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{year}-page-{page.zfill(4)}-{comparison_type}-{source_name}-comparison.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Comparison Results for {source_name} ({comparison_type}) - {year}-page-{page.zfill(4)}\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Word Error Rate (WER): {metrics['wer']:.4f}\n")
        f.write(f"Character Error Rate (CER): {metrics['cer']:.4f}\n\n")
        f.write("Word Alignment:\n")
        f.write("-" * 20 + "\n")
        f.write(metrics['word_alignment'] + "\n\n")
        f.write("Character Alignment:\n")
        f.write("-" * 20 + "\n")
        f.write(metrics['char_alignment'] + "\n")
    
    print(f"Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Compare OCR results (raw or LLM-corrected) with golden truth')
    parser.add_argument('--type',
                       choices=['llm', 'raw', 'both'],
                       default='both',
                       help='Comparison type: llm-corrected results, raw OCR, or both (default: both)')
    parser.add_argument('--ocr-source', 
                       choices=['original', 'tesseract', 'all'],
                       default='all',
                       help='OCR source to compare (default: all)')
    parser.add_argument('--model', 
                       choices=['gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gemini-2.5-pro', 'gemini-2.5-flash', 'all'],
                       default='all',
                       help='LLM model to compare (only used with --type llm, default: all)')
    parser.add_argument('--year', 
                       default='1887',
                       help='Year to analyze (default: 1887)')
    parser.add_argument('--page', 
                       default='0032',
                       help='Page number to analyze (default: 0032)')
    parser.add_argument('--output-dir',
                       default='compare-results',
                       help='Output directory for results (default: compare-results)')
    
    args = parser.parse_args()
    
    # Define transformations
    tr_word = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.Strip(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.ReduceToListOfListOfWords(),
    ])

    tr_char = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.Strip(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.ReduceToListOfListOfChars(),
    ])
    
    # Load reference (golden truth)
    try:
        reference = get_reference(args.year, args.page)
    except FileNotFoundError:
        print(f"Error: Golden truth file not found for {args.year}-page-{args.page.zfill(4)}")
        print(f"Expected file: golden-truth/{args.year}-page-{args.page.zfill(4)}.tsv")
        return
    
    # Collect all results
    results = []
    
    if args.type in ['llm', 'both']:
        # LLM-corrected results comparison
        models = ['gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gemini-2.5-pro', 'gemini-2.5-flash'] if args.model == 'all' else [args.model]
        ocr_sources_for_llm = ['original', 'tesseract'] if args.ocr_source == 'all' else [args.ocr_source]
        
        for ocr_source in ocr_sources_for_llm:
            for model in models:
                try:
                    # Load hypothesis
                    hypothesis = get_hypothesis(ocr_source, model, args.year, args.page)
                    
                    # Calculate metrics
                    metrics = calculate_metrics(reference, hypothesis, tr_word, tr_char)
                    
                    # Store results
                    results.append({
                        'type': 'LLM',
                        'source': f"{ocr_source}/{model}",
                        'wer': metrics['wer'],
                        'cer': metrics['cer']
                    })
                    
                    # Save detailed results to file
                    save_comparison_results('llm', f"{ocr_source}-{model}", args.year, args.page, metrics, args.output_dir)
                    
                except FileNotFoundError:
                    print(f"Warning: Results file not found for {model} on {ocr_source} OCR - {args.year}-page-{args.page.zfill(4)}")
                    print(f"Expected file: llm-corrected-results/{ocr_source}/{model}/{args.year}/{args.year}-page-{args.page.zfill(4)}.tsv")
                    continue
    
    if args.type in ['raw', 'both']:
        # Raw OCR results comparison
        ocr_types = ['original', 'tesseract'] if args.ocr_source == 'all' else [args.ocr_source]
        
        for ocr_type in ocr_types:
            try:
                # Load hypothesis
                hypothesis = get_raw_ocr_hypothesis(ocr_type, args.year, args.page)
                
                # Calculate metrics
                metrics = calculate_metrics(reference, hypothesis, tr_word, tr_char)
                
                # Store results
                results.append({
                    'type': 'Raw OCR',
                    'source': ocr_type,
                    'wer': metrics['wer'],
                    'cer': metrics['cer']
                })
                
                # Save detailed results to file
                save_comparison_results('raw', ocr_type, args.year, args.page, metrics, args.output_dir)
                
            except FileNotFoundError:
                print(f"Warning: Raw OCR file not found for {ocr_type} - {args.year}-page-{args.page.zfill(4)}")
                print(f"Expected file: ocr-no-ad/{args.year}-page-{args.page.zfill(4)}-{ocr_type}.txt")
                continue
    
    # Display results in table format
    if results:
        print(f"\nOCR Comparison Results")
        print(f"Type: {args.type.upper()} | Year: {args.year} | Page: {args.page.zfill(4)}")
        print("=" * 80)
        print(f"{'Type':<10} {'Source':<25} {'WER':<10} {'CER':<10}")
        print("-" * 55)
        
        for result in results:
            print(f"{result['type']:<10} {result['source']:<25} {result['wer']:<10.4f} {result['cer']:<10.4f}")
        
        print(f"\nDetailed comparison results saved in: {args.output_dir}/")
    else:
        print("No results to display.")
        
        if args.type in ['llm', 'both']:
            print(f"\nMake sure you have LLM correction results in:")
            print(f"llm-corrected-results/{args.ocr_source}/{{model}}/{args.year}/{args.year}-page-{args.page.zfill(4)}.tsv")
        if args.type in ['raw', 'both']:
            print(f"\nMake sure you have raw OCR results in:")
            print(f"ocr-no-ad/{args.year}-page-{args.page.zfill(4)}-{{ocr_type}}.txt")
            
        print(f"\nAnd golden truth in:")
        print(f"golden-truth/{args.year}-page-{args.page.zfill(4)}.tsv")


if __name__ == "__main__":
    main()