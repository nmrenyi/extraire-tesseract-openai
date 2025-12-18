#!/usr/bin/env python3
"""Extract TSV outputs from a Gemini batch output JSONL file.

- Infers bucket dir from filename (<source>-requests-<model>.output.jsonl -> <source>-<model>).
- Writes one .tsv per line, named after the "key" field (or line number fallback).
- Default output root: batch-gemini/raw-output-tsv/
"""

import argparse
import json
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parent


def infer_bucket_name(input_path: Path) -> Tuple[str, str, str]:
    """Infer (source, model, bucket) from the filename."""
    base = input_path.name
    for suffix in (".output.jsonl", ".errors.jsonl", ".jsonl"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    if "-requests-" in base:
        source, model = base.split("-requests-", 1)
    else:
        source, model = "unknown", base
    bucket = f"{source}-{model}"
    return source, model, bucket


def safe_stem(key: str, fallback: str) -> str:
    raw = key or fallback
    return "".join(ch if ch.isalnum() or ch in ("-", ".", "_") else "_" for ch in raw)


def extract_text(obj: dict, line_no: int, errors: list[str]) -> Optional[str]:
    response = obj.get("response")
    if not isinstance(response, dict):
        errors.append(f"line {line_no}: missing response")
        return None

    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append(f"line {line_no}: missing candidates")
        return None

    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    if not isinstance(content, dict):
        errors.append(f"line {line_no}: missing content")
        return None

    parts = content.get("parts") if isinstance(content.get("parts"), list) else None
    if not parts:
        errors.append(f"line {line_no}: missing content.parts")
        return None

    texts = [p.get("text") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
    if not texts:
        errors.append(f"line {line_no}: no text parts")
        return None

    # Join multiple text parts with newlines.
    return "\n".join(t.rstrip("\n") for t in texts if t is not None)


def process_file(input_path: Path, output_root: Path) -> tuple[int, list[str], Path]:
    source, model, bucket = infer_bucket_name(input_path)
    dest_dir = output_root / bucket
    dest_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    written = 0

    for line_no, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: json decode error: {exc}")
            continue
        text = extract_text(obj, line_no, errors)
        if text is None:
            continue
        stem = safe_stem(obj.get("key", ""), f"line-{line_no:04d}")
        out_path = dest_dir / f"{stem}.tsv"
        out_path.write_text(text + "\n", encoding="utf-8")
        written += 1

    return written, errors, dest_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract TSV outputs from Gemini batch JSONL results.")
    parser.add_argument("input", type=Path, help="Path to the .output.jsonl file")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "raw-output-tsv",
        help="Base directory to write TSV files (default: batch-gemini/raw-output-tsv)",
    )
    args = parser.parse_args()

    written, errors, dest_dir = process_file(args.input, args.output_root)

    print(f"validated lines: {written}")
    print(f"errors: {len(errors)}")
    if errors:
        for msg in errors:
            print(msg)
    print(f"tsv outputs saved under {dest_dir}")


if __name__ == "__main__":
    main()
