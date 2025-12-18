#!/usr/bin/env python3
"""Upload a Gemini vision JSONL and launch a batch job.

Steps:
1) Upload the JSONL file to Gemini Files API.
2) Persist the returned file name to a sidecar file for reuse.
3) Create a batch job pointing to that file.

Example:
  python batch-gemini-image/run_gemini_image_batch.py \
    --file batch-gemini-image/image-requests-gemini-3-flash-preview.jsonl \
    --model gemini-3-flash-preview \
    --display-name rosenwald-image-flash

Requires GOOGLE_API_KEY in the environment.
"""

import argparse
import json
from pathlib import Path
from google import genai
from google.genai import types


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload JSONL and launch Gemini vision batch job")
    parser.add_argument("--file", required=True, help="Path to the JSONL batch request file")
    parser.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="Gemini model name (default: gemini-3-flash-preview)",
    )
    parser.add_argument(
        "--display-name",
        help="Optional display name for the batch job (defaults to base filename)",
    )
    parser.add_argument(
        "--file-name-out",
        help="Where to store the uploaded file name (default: <file>.uploaded_name.txt)",
    )
    parser.add_argument(
        "--batch-out",
        help="Where to store the created batch info JSON (default: <file>.batch.json)",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip local JSONL validation before upload",
    )
    return parser.parse_args()


def validate_jsonl(path: Path) -> None:
    """Validate that each line is JSON and has the expected request shape."""
    required_top = {"key", "request"}

    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {idx}: {exc}")

            if not required_top.issubset(obj.keys()):
                missing = required_top.difference(obj.keys())
                raise SystemExit(f"Line {idx} missing keys: {sorted(missing)}")

            if not isinstance(obj.get("request"), dict):
                raise SystemExit(f"Line {idx} has non-object request")


def main() -> None:
    args = parse_args()
    jsonl_path = Path(args.file)
    if not jsonl_path.exists():
        raise SystemExit(f"Input file not found: {jsonl_path}")

    if not args.skip_validate:
        print(f"Validating {jsonl_path} ...")
        validate_jsonl(jsonl_path)
        print("Validation passed.")

    file_name_out = Path(args.file_name_out) if args.file_name_out else jsonl_path.with_suffix(jsonl_path.suffix + ".uploaded_name.txt")
    batch_out = Path(args.batch_out) if args.batch_out else jsonl_path.with_suffix(jsonl_path.suffix + ".batch.json")
    display_name = args.display_name or jsonl_path.stem

    client = genai.Client()

    # 1) Upload file
    print(f"Uploading {jsonl_path} ...")
    uploaded = client.files.upload(
        file=str(jsonl_path),
        config=types.UploadFileConfig(display_name=display_name, mime_type="application/jsonl"),
    )
    file_name_out.write_text(uploaded.name)
    print(f"Uploaded. file name: {uploaded.name}\nSaved to: {file_name_out}")

    # 2) Create batch job
    print("Creating batch job ...")
    batch = client.batches.create(
        model=args.model,
        src=uploaded.name,
        config={"display_name": display_name},
    )
    batch_out.write_text(batch.model_dump_json(indent=2))
    print(f"Batch created. name: {batch.name}\nState: {batch.state.name}\nSaved batch info to: {batch_out}")


if __name__ == "__main__":
    main()
