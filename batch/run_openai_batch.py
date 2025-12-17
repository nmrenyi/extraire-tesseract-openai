#!/usr/bin/env python3
"""Upload a JSONL batch file to OpenAI and start a batch job.

Steps:
1) Upload the JSONL (purpose="batch").
2) Persist the returned file_id to a sidecar file for reuse.
3) Start a batch with endpoint /v1/responses and the chosen completion window.

Example:
  python batch/run_openai_batch.py \
    --file batch/original-ocr-requests-gpt-5-mini-2025-08-07.jsonl \
    --window 24h

Requires OPENAI_API_KEY in the environment.
"""

import argparse
from pathlib import Path
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload JSONL and launch OpenAI batch")
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the JSONL batch request file",
    )
    parser.add_argument(
        "--window",
        default="24h",
        help="Batch completion window (default: 24h)",
    )
    parser.add_argument(
        "--file-id-out",
        help="Where to store the uploaded file_id (default: <file>.file_id.txt)",
    )
    parser.add_argument(
        "--batch-out",
        help="Where to store the created batch info JSON (default: <file>.batch.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jsonl_path = Path(args.file)
    if not jsonl_path.exists():
        raise SystemExit(f"Input file not found: {jsonl_path}")

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
