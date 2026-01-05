#!/usr/bin/env python3
"""Extract TSV results from Gemini multimodal batch output JSONL(s).

Run tips (from this directory):
- Single output file (model-based default):
        python extract_gemini_image_text_batch_output.py --model gemini-3-flash-preview
- Explicit output file:
        python extract_gemini_image_text_batch_output.py --output-jsonl path/to/file.output.jsonl
- All chunk outputs in a directory:
    python extract_gemini_image_text_batch_output.py --outputs-dir path/to/chunks --glob "*.output.jsonl"
        (writes everything into one combined folder)
"""

import argparse
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "gemini-3-flash-preview"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract TSVs from Gemini multimodal batch output JSONL")
    grp = parser.add_mutually_exclusive_group(required=False)
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name used in filename inference (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        help=(
            "Path to output JSONL (default: batch-gemini-image-text/raw-batch-output/"
            "image-text-requests-<model>.output.jsonl)"
        ),
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        help="Directory containing multiple output JSONLs (e.g., chunk outputs)",
    )
    parser.add_argument(
        "--glob",
        default="*.output.jsonl",
        help="Glob for output files inside --outputs-dir (default: *.output.jsonl)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Where to write TSVs (default: batch-gemini-image-text/raw-output-tsv/<model>/)",
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
    inputs = []

    if args.outputs_dir:
        if not args.outputs_dir.exists():
            raise SystemExit(f"Outputs dir not found: {args.outputs_dir}")
        inputs = sorted(args.outputs_dir.glob(args.glob))
        if not inputs:
            raise SystemExit(f"No files matching {args.glob} in {args.outputs_dir}")
    else:
        in_path = args.output_jsonl or (
            ROOT
            / "batch-gemini-image-text"
            / "raw-batch-output"
            / f"image-text-requests-{args.model}.output.jsonl"
        )
        inputs = [in_path]

    total_written = 0
    total_missing = 0
    total_errors = 0

    for in_path in inputs:
        if not in_path.exists():
            print(f"skip missing file: {in_path}")
            continue

        out_dir = args.out_dir
        if args.outputs_dir:
            # Combine all chunk outputs into a single folder
            default_dir = ROOT / "batch-gemini-image-text-production" / "raw-output-tsv" / args.outputs_dir.name
            out_dir = out_dir or default_dir
        else:
            out_dir = out_dir or (ROOT / "batch-gemini-image-text-production" / "raw-output-tsv" / args.model)

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
                    print(f"{in_path.name}: skip line {line_no}: invalid JSON ({exc})")
                    errors += 1
                    continue

                key = obj.get("key") or f"row-{line_no}"
                response = obj.get("response") if isinstance(obj.get("response"), dict) else None

                text = extract_text(response)
                if not text:
                    print(f"{in_path.name}: missing text for {key} (line {line_no})")
                    missing += 1
                    continue

                out_path = out_dir / f"{key}.tsv"
                out_path.write_text(text.strip() + "\n", encoding="utf-8")
                written += 1

        total_written += written
        total_missing += missing
        total_errors += errors

        print(f"{in_path}: written={written} missing={missing} parse_errors={errors} -> {out_dir}")

    print(f"TOTAL written={total_written} missing={total_missing} parse_errors={total_errors}")


if __name__ == "__main__":
    main()
