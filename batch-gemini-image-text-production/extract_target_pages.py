#!/usr/bin/env python3
"""Extract specific page ranges listed in target-pages.tsv into PNGs.

Reads target-pages.tsv (year, page_begin, page_end, note, localisation) and
uses pdf2png.py to render only those pages into rosenwald-images/<year>/.

Example:
  python batch-gemini-image-text-production/extract_target_pages.py
  python batch-gemini-image-text-production/extract_target_pages.py --years 1887 1888 --dpi 400
  python extract_target_pages.py --dry-run
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = Path(__file__).resolve().parent / "target-pages.tsv"
DEFAULT_PDFS_DIR = ROOT / "pdfs"
DEFAULT_OUTPUT_DIR = ROOT / "rosenwald-images"
PDF2PNG_PATH = ROOT / "pdf2png.py"

# Import the single-page converter from the existing script to avoid shelling out repeatedly.
sys.path.append(str(ROOT))  # Allows `import pdf2png`
try:
    from pdf2png import convert_single_page_to_png, get_pdf_page_count
except Exception as exc:  # pragma: no cover - defensive import guard
    raise SystemExit(f"Could not import helpers from pdf2png.py: {exc}")


def read_targets(tsv_path: Path, years_filter: Iterable[str]) -> List[Dict[str, str]]:
    """Load target rows, optionally filtering by year."""
    if not tsv_path.exists():
        raise SystemExit(f"Target TSV not found: {tsv_path}")

    years = {y.strip() for y in years_filter} if years_filter else None
    rows: List[Dict[str, str]] = []

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = (row.get("year") or "").strip()
            if years and year not in years:
                continue
            try:
                start = int(row.get("page_begin") or 0)
                end = int(row.get("page_end") or 0)
            except ValueError:
                print(f"skip row with non-numeric pages: {row}")
                continue
            if not year or start <= 0 or end < start:
                print(f"skip malformed row: {row}")
                continue
            rows.append({"year": year, "start": start, "end": end})
    return rows


def render_year(pdf_path: Path, pages: Iterable[int], output_dir: Path, dpi: int, dry_run: bool) -> Dict[str, int]:
    """Render selected pages for one PDF, returning counts."""
    if not pdf_path.exists():
        print(f"skip missing PDF: {pdf_path}")
        return {"rendered": 0, "failed": 0}

    page_list = sorted(set(pages))

    page_count = get_pdf_page_count(str(pdf_path))
    if page_count is None:
        print(f"warning: could not verify page count for {pdf_path}")
    else:
        too_high = [p for p in page_list if p > page_count]
        if too_high:
            print(f"skip {pdf_path.name}: pages beyond PDF length {page_count}: {too_high}")
            page_list = [p for p in page_list if p <= page_count]

    rendered = 0
    failed = 0
    for page in page_list:
        if dry_run:
            print(f"DRY-RUN would render {pdf_path.name} page {page} -> {output_dir}")
            rendered += 1
            continue
        ok = convert_single_page_to_png(str(pdf_path), page, str(output_dir), dpi)
        if ok:
            rendered += 1
        else:
            failed += 1
    return {"rendered": rendered, "failed": failed}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract page ranges from target-pages.tsv into PNGs")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV, help="Path to target-pages.tsv")
    parser.add_argument("--pdfs-dir", type=Path, default=DEFAULT_PDFS_DIR, help="Directory containing <year>.pdf files")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Where to write PNGs")
    parser.add_argument("--years", nargs="*", help="Optional subset of years to process (e.g., 1887 1888)")
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI (default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="List work without rendering")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    targets = read_targets(args.tsv, args.years)
    if not targets:
        print("No targets to process; check filters/TSV.")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)

    total_rendered = 0
    total_failed = 0

    for entry in targets:
        year = entry["year"]
        pages = range(entry["start"], entry["end"] + 1)
        pdf_path = args.pdfs_dir / f"{year}.pdf"
        summary = render_year(pdf_path, pages, args.output_dir, args.dpi, args.dry_run)
        total_rendered += summary["rendered"]
        total_failed += summary["failed"]

    status = "DRY-RUN complete" if args.dry_run else "Rendering complete"
    print(f"{status}: rendered={total_rendered}, failed={total_failed}")


if __name__ == "__main__":
    main()
