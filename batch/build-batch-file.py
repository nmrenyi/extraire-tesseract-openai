#!/usr/bin/env python3
"""Build batch requests directly from a benchmark TSV file.

For each row in the selected benchmark TSV (original or tesseract), this script:
- Reads the OCR `text` column directly from the TSV
- Combines instructions-raw.txt and instructions-example-output.tsv into a single
  instruction string (same as llm-correction.py)
- Emits one batch-style request JSON line per file with custom_id "{year}-{page}"

Output: batch/<source>-requests-<model>.jsonl
"""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTR_RAW = ROOT / "instructions-raw.txt"
INSTR_EXAMPLE = ROOT / "instructions-example-output.tsv"
TSV_PATHS = {
    "original": ROOT / "batch" / "rosenwald-benchmark-original.tsv",
    "tesseract": ROOT / "batch" / "rosenwald-benchmark-tesseract.tsv",
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


def parse_args():
    parser = argparse.ArgumentParser(description="Build batch JSONL requests from a benchmark TSV")
    parser.add_argument(
        "--source",
        choices=sorted(TSV_PATHS.keys()),
        default="original",
        help="Which benchmark TSV to read (default: original)",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini-2025-08-07",
        help="Model name to include in each request and output filename (default: gpt-5-mini-2025-08-07)",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["medium", "high"],
        default="high",
        help="Reasoning effort hint passed to the model (default: high)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tsv_path = TSV_PATHS[args.source]
    if not tsv_path.exists():
        raise SystemExit(f"Missing benchmark TSV: {tsv_path}")

    instructions = load_instructions()

    output_path = ROOT / "batch" / f"{args.source}-requests-{args.model}.jsonl"

    requests = []

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = row.get("year", "").strip()
            page = row.get("page", "").strip()
            text = row.get("text", "")

            if not year or not page or text is None:
                continue

            # Convert literal "\n" sequences to real newlines to avoid double escaping in JSONL
            # Restore escaped control sequences for the model to see structure.
            normalized_text = (
                text
                .replace(r"\n", "\n")
                .replace(r"\t", "\t")     # only needed if you escaped tabs when writing
            )

            requests.append({
                "custom_id": f"{year}-{page}",
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": args.model,
                    "reasoning": {"effort": args.reasoning_effort},
                    "instructions": instructions,
                    "input": normalized_text,
                },
            })

    with output_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False))
            f.write("\n")

    print(f"Wrote {len(requests)} requests to {output_path}")


if __name__ == "__main__":
    main()
