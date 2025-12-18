#!/usr/bin/env python3
"""Build Gemini batch JSONL requests from a benchmark TSV.

For each row in the selected benchmark TSV (original or tesseract), this script:
- Reads the OCR `text` column directly from the TSV.
- Combines instructions-raw.txt and instructions-example-output.tsv into one prompt.
- Emits one Gemini Batch API JSON line per file with key "{year}-{page}".

Output: batch/<source>-requests-<model>.jsonl (e.g., original-requests-gemini-3-pro-preview.jsonl)
"""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTR_RAW = ROOT / "instructions-raw.txt"
INSTR_EXAMPLE = ROOT / "instructions-example-output.tsv"
TSV_PATHS = {
    "original": ROOT / "batch-gemini" / "rosenwald-benchmark-original.tsv",
    "tesseract": ROOT / "batch-gemini" / "rosenwald-benchmark-tesseract.tsv",
}


def load_instructions() -> str:
    """Combine raw instructions and example output into one prompt string."""
    if not INSTR_RAW.exists():
        raise SystemExit(f"Missing instructions file: {INSTR_RAW}")
    if not INSTR_EXAMPLE.exists():
        raise SystemExit(f"Missing example file: {INSTR_EXAMPLE}")

    raw_text = INSTR_RAW.read_text(encoding="utf-8").strip()
    example_text = INSTR_EXAMPLE.read_text(encoding="utf-8").strip()
    return f"{raw_text}\n\n### EXEMPLE DE SORTIE ATTENDUE\n{example_text}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gemini batch JSONL requests from a benchmark TSV")
    parser.add_argument(
        "--source",
        choices=sorted(TSV_PATHS.keys()),
        default="original",
        help="Which benchmark TSV to read (default: original)",
    )
    parser.add_argument(
        "--model",
        default="gemini-3-pro-preview",
        help="Gemini model name for the request payload and filename (default: gemini-3-pro-preview)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tsv_path = TSV_PATHS[args.source]
    if not tsv_path.exists():
        raise SystemExit(f"Missing benchmark TSV: {tsv_path}")

    instructions = load_instructions()
    output_path = ROOT / "batch-gemini" / f"{args.source}-requests-{args.model}.jsonl"

    requests = []

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = row.get("year", "").strip()
            page = row.get("page", "").strip()
            text = row.get("text", "")

            if not year or not page or text is None:
                continue

            # Convert literal escape sequences to real control characters.
            normalized_text = text.replace(r"\n", "\n").replace(r"\t", "\t")

            prompt = f"{instructions}\n\n### TEXTE OCR\n{normalized_text}"

            requests.append({
                "key": f"{year}-{page}",
                "request": {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                            ]
                        }
                    ],
                },
            })

    with output_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False))
            f.write("\n")

    print(f"Wrote {len(requests)} requests to {output_path}")


if __name__ == "__main__":
    main()
