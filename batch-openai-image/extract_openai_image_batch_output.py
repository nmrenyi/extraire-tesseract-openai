#!/usr/bin/env python3
"""Extract TSV results from an OpenAI vision batch output JSONL.

Reads the batch output JSONL (each line = one batch request response) and writes one
TSV file per custom_id under raw-output-tsv/<model>/.

Assumptions about each JSONL line:
- top-level keys: id, custom_id, response
- response.body.output[*].content contains an item with type "output_text" and "text"

Example:
  python batch-openai-image/extract_openai_image_batch_output.py \
    --model gpt-5-mini-2025-08-07

Input default: batch-openai-image/raw-batch-output/image-requests-<model>.output.jsonl
Output default: batch-openai-image/raw-output-tsv/<model>/<custom_id>.tsv
"""

import argparse
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "gpt-5-mini-2025-08-07"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract TSVs from OpenAI vision batch output JSONL")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name used in filename inference (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        help="Path to output JSONL (default: batch-openai-image/raw-batch-output/image-requests-<model>.output.jsonl)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Where to write TSVs (default: batch-openai-image/raw-output-tsv/<model>/)",
    )
    return parser.parse_args()


def extract_text(body: dict) -> Optional[str]:
    """Grab output_text from the response body."""
    # New Responses API: body may have .output_text convenience
    text_direct = body.get("output_text") if isinstance(body, dict) else None
    if isinstance(text_direct, str) and text_direct.strip():
        return text_direct

    outputs = body.get("output") if isinstance(body, dict) else None
    if not isinstance(outputs, list):
        return None

    for entry in outputs:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "message":
            continue
        content = entry.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text_val = part.get("text")
                if isinstance(text_val, str):
                    return text_val
    return None


def main() -> None:
    args = parse_args()

    in_path = args.output_jsonl or (ROOT / "batch-openai-image" / "raw-batch-output" / f"image-requests-{args.model}.output.jsonl")
    out_dir = args.out_dir or (ROOT / "batch-openai-image" / "raw-output-tsv" / args.model)

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

            custom_id = obj.get("custom_id") or obj.get("id") or f"row-{line_no}"
            resp = obj.get("response") if isinstance(obj.get("response"), dict) else None
            body = resp.get("body") if resp else None

            text = extract_text(body) if isinstance(body, dict) else None
            if not text:
                print(f"missing text for {custom_id} (line {line_no})")
                missing += 1
                continue

            out_path = out_dir / f"{custom_id}.tsv"
            out_path.write_text(text.strip() + "\n", encoding="utf-8")
            written += 1

    print(f"written: {written}")
    print(f"missing text: {missing}")
    print(f"parse errors: {errors}")


if __name__ == "__main__":
    main()
