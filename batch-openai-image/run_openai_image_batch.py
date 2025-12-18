#!/usr/bin/env python3
"""Upload an OpenAI vision batch JSONL and start a batch job.

Steps:
1) Upload the JSONL (purpose="batch").
2) Persist the returned file_id to a sidecar file for reuse.
3) Start a batch with endpoint /v1/responses and the chosen completion window.

Example:
  python batch-openai-image/run_openai_image_batch.py \
    --file batch-openai-image/image-requests-gpt-5-mini-2025-08-07.jsonl \
    --window 24h

Requires OPENAI_API_KEY in the environment.
"""

import argparse
import json
from pathlib import Path
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload JSONL and launch OpenAI vision batch")
    parser.add_argument("--file", required=True, help="Path to the JSONL batch request file")
    parser.add_argument("--window", default="24h", help="Batch completion window (default: 24h)")
    parser.add_argument("--file-id-out", help="Where to store the uploaded file_id (default: <file>.file_id.txt)")
    parser.add_argument("--batch-out", help="Where to store the created batch info JSON (default: <file>.batch.json)")
    parser.add_argument("--skip-validate", action="store_true", help="Skip local JSONL validation before upload")
    return parser.parse_args()


def validate_jsonl(path: Path) -> None:
    """Validate that each line is JSON and has the expected request shape."""
    required_top = {"custom_id", "method", "url", "body"}
    required_body = {"model", "input"}

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
                raise SystemExit(f"Line {idx} missing top-level keys: {sorted(missing)}")

            body = obj.get("body", {})
            if not isinstance(body, dict):
                raise SystemExit(f"Line {idx} has non-object body")

            if not required_body.issubset(body.keys()):
                missing = required_body.difference(body.keys())
                raise SystemExit(f"Line {idx} missing body keys: {sorted(missing)}")

            if obj.get("method") != "POST":
                raise SystemExit(f"Line {idx} expected method POST, found: {obj.get('method')}")

            if obj.get("url") != "/v1/responses":
                raise SystemExit(f"Line {idx} expected url /v1/responses, found: {obj.get('url')}")


def main() -> None:
    args = parse_args()
    jsonl_path = Path(args.file)
    if not jsonl_path.exists():
        raise SystemExit(f"Input file not found: {jsonl_path}")

    if not args.skip_validate:
        print(f"Validating {jsonl_path} ...")
        validate_jsonl(jsonl_path)
        print("Validation passed.")

    file_id_out = Path(args.file_id_out) if args.file_id_out else jsonl_path.with_suffix(jsonl_path.suffix + ".file_id.txt")
    batch_out = Path(args.batch_out) if args.batch_out else jsonl_path.with_suffix(jsonl_path.suffix + ".batch.json")

    client = OpenAI()

    # 1) Upload file
    print(f"Uploading {jsonl_path} ...")
    with jsonl_path.open("rb") as f:
        upload = client.files.create(file=f, purpose="batch")
    file_id_out.write_text(upload.id)
    print(f"Uploaded. file_id: {upload.id}\nSaved to: {file_id_out}")

    # 2) Create batch
    print("Creating batch ...")
    batch = client.batches.create(
        input_file_id=upload.id,
        endpoint="/v1/responses",
        completion_window=args.window,
    )
    batch_out.write_text(batch.model_dump_json(indent=2))
    print(f"Batch created. id: {batch.id}\nStatus: {batch.status}\nSaved batch info to: {batch_out}")


if __name__ == "__main__":
    main()
