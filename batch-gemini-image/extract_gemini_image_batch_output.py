#!/usr/bin/env python3
"""Extract TSV results from a Gemini vision batch output JSONL.

Reads the Gemini batch output JSONL (one line per request) and writes one TSV per key
under raw-output-tsv/<model>/.

Assumptions about each JSONL line:
- top-level keys: key, response
- response.candidates[0].content.parts contains a part with a text field

Example:
  python batch-gemini-image/extract_gemini_image_batch_output.py \
    --model gemini-3-flash-preview

Input default: batch-gemini-image/raw-batch-output/image-requests-<model>.output.jsonl
Output default: batch-gemini-image/raw-output-tsv/<model>/<key>.tsv
"""

import argparse
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "gemini-3-flash-preview"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract TSVs from Gemini vision batch output JSONL")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name used in filename inference (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        help="Path to output JSONL (default: batch-gemini-image/raw-batch-output/image-requests-<model>.output.jsonl)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Where to write TSVs (default: batch-gemini-image/raw-output-tsv/<model>/)",
    )
    return parser.parse_args()


def extract_text(response: dict) -> Optional[str]:
    """Return the first text part from the first candidate, if present."""
    if not isinstance(response, dict):
        return None

    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None

    first = candidates[0]
    content = first.get("content") if isinstance(first, dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return None

    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            return text
    return None


def main() -> None:
    args = parse_args()

    in_path = args.output_jsonl or (
        ROOT / "batch-gemini-image" / "raw-batch-output" / f"image-requests-{args.model}.output.jsonl"
    )
    out_dir = args.out_dir or (ROOT / "batch-gemini-image" / "raw-output-tsv" / args.model)

    if not in_path.exists():
        raise SystemExit(f"Output JSONL not found: {in_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    missing = 0
    errors = 0

    with in_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"skip line {line_no}: invalid JSON ({exc})")
                errors += 1
                continue

            key = obj.get("key") or f"row-{line_no}"
            response = obj.get("response") if isinstance(obj.get("response"), dict) else None

            text = extract_text(response)
            if not text:
                print(f"missing text for {key} (line {line_no})")
                missing += 1
                continue

            out_path = out_dir / f"{key}.tsv"
            out_path.write_text(text.strip() + "\n", encoding="utf-8")
            written += 1

    print(f"written: {written}")
    print(f"missing text: {missing}")
    print(f"parse errors: {errors}")


if __name__ == "__main__":
    main()
