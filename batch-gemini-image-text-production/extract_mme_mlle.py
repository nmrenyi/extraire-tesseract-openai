#!/usr/bin/env python3
"""Extract female honorifics from TSV files and add sexe column.

This script recognizes the following patterns:
Madame, Mme, Mad., Mademoiselle, Mlle, Dame, née

The script:
1. Reads all TSV files from an input directory
2. Identifies rows containing female honorifics in the 'nom' field
3. Adds a 'sexe' column with the exact pattern found
4. Cleans up the 'année' column (converts float to int where possible)
5. Saves the processed TSVs to an output directory
6. Creates a combined file with all entries containing these patterns (all_mme_mlle.tsv)
7. Creates a statistics file with counts per file (mme_mlle_counts.tsv)
"""

import argparse
import os
from pathlib import Path
import pandas as pd
from typing import Optional


def determine_sexe(nom: str) -> str:
    """Determine sexe based on presence of female honorifics in nom field.
    
    Returns the actual pattern found: Madame, Mme, Mad., Mademoiselle, Mlle, née, Dame
    
    Args:
        nom: Name string to check
        
    Returns:
        The matched pattern or empty string
    """
    if pd.isna(nom):
        return ''
    
    # Check patterns in priority order (longer patterns first to avoid partial matches)
    # patterns = ['Mademoiselle', 'Madame', 'Mlle', 'Mme', 'Mad.', 'Dame', 'née']
    patterns = ['Mlle', 'Mme', 'Mademoiselle', '(Madame', 'Mad.', '(Dame']
    
    for pattern in patterns:
        if pattern in nom:
            return pattern
    
    return ''


def convert_annee(annee) -> str:
    """Convert année field to string, converting float to int if possible.
    
    Args:
        annee: Year value (may be float, int, or NaN)
        
    Returns:
        String representation of the year
    """
    if pd.isna(annee):
        return ''
    try:
        annee_int = int(annee)
        return str(annee_int)
    except:
        return str(annee)


def process_tsv_files(
    input_folder: str,
    output_folder: str,
    create_combined: bool = True,
    combined_output: Optional[str] = None,
    stats_output: Optional[str] = None
) -> tuple[int, int]:
    """Process all TSV files to extract Mme and Mlle entries.
    
    Args:
        input_folder: Directory containing input TSV files
        output_folder: Directory to save processed TSV files
        create_combined: Whether to create a combined file with all Mme/Mlle entries
        combined_output: Path for the combined output file
        stats_output: Path for the statistics file
        
    Returns:
        Tuple of (total_mme, total_mlle) counts
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all TSV files
    filenames = sorted([f for f in os.listdir(input_path) if f.endswith('.tsv')])
    
    if not filenames:
        print(f"No TSV files found in {input_folder}")
        return 0, 0
    
    print(f"Found {len(filenames)} TSV files to process")
    
    total_mme = 0
    total_mlle = 0
    all_mme_mlle_rows = []
    stats_results = []
    
    # Process each file
    for idx, filename in enumerate(filenames, 1):
        try:
            df = pd.read_csv(input_path / filename, sep='\t')
            
            # Add sexe column
            df['sexe'] = df['nom'].apply(determine_sexe)
            
            # Clean up année column
            if 'année' in df.columns:
                df['année'] = df['année'].apply(convert_annee)
            
            # Count Mme and Mlle
            mme_count = (df['sexe'] == 'Mme').sum()
            mlle_count = (df['sexe'] == 'Mlle').sum()
            total_mme += mme_count
            total_mlle += mlle_count
            
            # Collect stats
            stats_results.append({
                'filename': filename.replace('.tsv', ''),
                'count_mme': mme_count,
                'count_mlle': mlle_count
            })
            
            # Save processed file
            df.to_csv(output_path / filename, sep='\t', index=False)
            
            # Collect Mme/Mlle rows for combined output
            if create_combined and df['sexe'].ne('').any():
                # Extract year and page from filename (e.g., "1903-0129.tsv")
                year, page = filename.replace('.tsv', '').split('-')
                female_rows = df[df['sexe'] != ''].copy()
                female_rows['year'] = year
                female_rows['page'] = page
                all_mme_mlle_rows.append(female_rows)
            
            if (idx % 100 == 0) or (mme_count > 0 or mlle_count > 0):
                print(f"[{idx}/{len(filenames)}] {filename}: Mme={mme_count}, Mlle={mlle_count}")
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Save statistics file
    if stats_output and stats_results:
        stats_df = pd.DataFrame(stats_results)
        stats_df['total'] = stats_df['count_mme'] + stats_df['count_mlle']
        stats_df.to_csv(stats_output, sep='\t', index=False)
        print(f"\nStatistics saved to: {stats_output}")
    
    # Create combined file if requested
    if create_combined and all_mme_mlle_rows:
        combined_df = pd.concat(all_mme_mlle_rows, ignore_index=True)
        
        # Clean up année column in combined file
        if 'année' in combined_df.columns:
            combined_df['année'] = combined_df['année'].apply(convert_annee)
        
        combined_path = combined_output or (output_path / 'all_mme_mlle.tsv')
        combined_df.to_csv(combined_path, sep='\t', index=False)
        print(f"\nCombined file saved to: {combined_path}")
        print(f"Total entries in combined file: {len(combined_df)}")
    
    return total_mme, total_mlle


def count_mme_mlle(input_folder: str) -> pd.DataFrame:
    """Count female honorific occurrences in all TSV files.
    
    Counts based on patterns: Madame, Mme, Mad., Mademoiselle, Mlle, Dame, née
    
    Args:
        input_folder: Directory containing TSV files
        
    Returns:
        DataFrame with counts per file
    """
    input_path = Path(input_folder)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    filenames = sorted([f for f in os.listdir(input_path) if f.endswith('.tsv')])
    
    patterns = ['Mademoiselle', 'Madame', 'Mlle', 'Mme', 'Mad.', 'Dame', 'née']
    
    results = []
    for filename in filenames:
        try:
            df = pd.read_csv(input_path / filename, sep='\t')
            # Count based on all patterns
            def has_pattern(nom):
                if pd.isna(nom):
                    return False
                return any(pattern in nom for pattern in patterns)
            
            # For backward compatibility, still count Mme-related and Mlle-related separately
            def has_mme_related(nom):
                if pd.isna(nom):
                    return False
                return any(pattern in nom for pattern in ['Madame', 'Mme', 'Mad.', 'Dame', 'née'])
            
            def has_mlle_related(nom):
                if pd.isna(nom):
                    return False
                return any(pattern in nom for pattern in ['Mademoiselle', 'Mlle'])
            
            count_mme = df['nom'].apply(has_mme_related).sum()
            count_mlle = df['nom'].apply(has_mlle_related).sum()
            results.append({
                'filename': filename.replace('.tsv', ''),
                'count_mme': count_mme,
                'count_mlle': count_mlle
            })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    results_df = pd.DataFrame(results)
    results_df['total'] = results_df['count_mme'] + results_df['count_mlle']
    
    return results_df


def main():
    parser = argparse.ArgumentParser(
        description='Extract and analyze Mme/Mlle entries from TSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  # Default: process TSVs, add sexe column, create combined and stats files:
  %(prog)s --input repaired-tsv --output analysed-tsv
  
  # Skip creating combined file:
  %(prog)s --input repaired-tsv --output analysed-tsv --no-combined
  
  # Custom paths for output files:
  %(prog)s --input repaired-tsv --output analysed-tsv --combined custom.tsv --stats custom_stats.tsv
  
  # Just count occurrences without processing:
  %(prog)s --input repaired-tsv --count-only --stats counts.tsv
        '''
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input directory containing TSV files'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory for processed TSV files (required unless --count-only)'
    )
    
    parser.add_argument(
        '--combined',
        help='Path for combined file with all Mme/Mlle entries (default: <output>/all_mme_mlle.tsv)'
    )
    
    parser.add_argument(
        '--stats',
        help='Path for count statistics file (default: <output>/mme_mlle_counts.tsv)'
    )
    
    parser.add_argument(
        '--no-combined',
        action='store_true',
        help='Skip creating the combined all_mme_mlle.tsv file'
    )
    
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Skip creating the mme_mlle_counts.tsv statistics file'
    )
    
    parser.add_argument(
        '--count-only',
        action='store_true',
        help='Only count Mme/Mlle without processing files'
    )
    
    args = parser.parse_args()
    
    if args.count_only:
        # Just count and optionally save statistics
        print("Counting Mme and Mlle occurrences...")
        results_df = count_mme_mlle(args.input)
        
        print(f"\nProcessed {len(results_df)} files")
        print(f"Total Mme: {results_df['count_mme'].sum()}")
        print(f"Total Mlle: {results_df['count_mlle'].sum()}")
        print(f"Total: {results_df['total'].sum()}")
        
        if args.stats:
            results_df.to_csv(args.stats, sep='\t', index=False)
            print(f"\nStatistics saved to: {args.stats}")
    
    else:
        # Process files
        if not args.output:
            parser.error("--output is required unless --count-only is specified")
        
        output_path = Path(args.output)
        
        # Set default paths for combined and stats files
        combined_path = args.combined
        if not args.no_combined and not combined_path:
            combined_path = str(output_path / 'all_mme_mlle.tsv')
        
        stats_path = args.stats
        if not args.no_stats and not stats_path:
            stats_path = str(output_path / 'mme_mlle_counts.tsv')
        
        print(f"Processing TSV files from {args.input}...")
        print(f"Output directory: {args.output}")
        if not args.no_combined:
            print(f"Combined file: {combined_path}")
        if not args.no_stats:
            print(f"Statistics file: {stats_path}")
        
        total_mme, total_mlle = process_tsv_files(
            args.input,
            args.output,
            create_combined=not args.no_combined,
            combined_output=combined_path,
            stats_output=stats_path
        )
        
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total Mme: {total_mme}")
        print(f"Total Mlle: {total_mlle}")
        print(f"Total: {total_mme + total_mlle}")
        print(f"Processed files saved to: {args.output}")


if __name__ == '__main__':
    main()
