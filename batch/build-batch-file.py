#!/usr/bin/env python3
"""Build batch requests for original OCR pages listed in target-files.log.

For each year-page found in batch/target-files.log, this script:
- Locates the matching original OCR txt file under rosenwald-original-ocr/{year}/
- Combines instructions-raw.txt and instructions-example-output.tsv into a single
    instruction string (same as llm-correction.py)
- Emits one batch-style request JSON line per file with custom_id "{year}-{page}-{side}"

Output: batch/original-ocr-requests-<model>.jsonl
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "batch" / "target-files.log"
OCR_ROOT = ROOT / "rosenwald-original-ocr"
INSTR_RAW = ROOT / "instructions-raw.txt"
INSTR_EXAMPLE = ROOT / "instructions-example-output.tsv"

# Capture year, page, and final side indicator (-1 or -2) before .json
# Example: claude-sonnet-4-5__vs__qwen3-vl-235b-a22b-thinking-1887-0029-...-1.json
pattern = re.compile(r"(?P<year>\d{4})-(?P<page>\d{4}).*-(?P<side>[12])\.json")

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
    parser = argparse.ArgumentParser(description="Build batch JSONL requests from target-files.log")
    parser.add_argument(
        "--model",
        default="gpt-5-mini-2025-08-07",
        help="Model name to include in each request and output filename (default: gpt-5-mini-2025-08-07)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not LOG_PATH.exists():
        raise SystemExit(f"Missing log file: {LOG_PATH}")

    instructions = load_instructions()

    output_path = ROOT / "batch" / f"original-ocr-requests-{args.model}.jsonl"

    pairs = set()
    for line in LOG_PATH.read_text().splitlines():
        match = pattern.search(line)
        if match:
            pairs.add((match.group("year"), match.group("page"), match.group("side")))

    sorted_pairs = sorted(pairs, key=lambda t: (int(t[0]), int(t[1]), int(t[2])))

    requests = []
    missing = []

    for year, page, side in sorted_pairs:
        ocr_path = OCR_ROOT / year / f"{year}-page-{page}.txt"
        if not ocr_path.exists():
            missing.append(ocr_path)
            continue

        ocr_text = ocr_path.read_text(encoding="utf-8").strip()

        requests.append({
            "custom_id": f"{year}-{page}-{side}",
            "method": "POST",
            "url": "/v1/responses",
            "body": {
                "model": args.model,
                "instructions": instructions,
                "input": ocr_text,
            },
        })

    with output_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False))
            f.write("\n")

    print(f"Wrote {len(requests)} requests to {output_path}")
    if missing:
        print(f"Missing {len(missing)} OCR files:")
        for path in missing:
            print(f"  {path}")


if __name__ == "__main__":
    main()
