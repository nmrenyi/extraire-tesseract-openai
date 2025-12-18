#!/usr/bin/env python3
"""Check OpenAI batch status and print a readable summary."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI


def save_error_file(client: OpenAI, file_id: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    content = client.files.content(file_id)
    target.write_bytes(content.read())
    return target


def save_output_file(client: OpenAI, file_id: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    content = client.files.content(file_id)
    target.write_bytes(content.read())
    return target


def summarize_errors(error_path: Path) -> None:
    print("\nFailed Requests")
    print("---------------")
    count = 0
    with error_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"(skip malformed line) {line[:80]}...")
                continue
            custom_id = obj.get("custom_id") or obj.get("id") or "(no custom_id)"
            resp = obj.get("response") if isinstance(obj.get("response"), dict) else None
            err = obj.get("error") or (resp.get("body", {}).get("error") if resp else None)

            message = None
            if isinstance(err, dict):
                message = err.get("message") or err.get("error") or str(err)
            if not message and resp and isinstance(resp.get("body"), dict):
                body_err = resp["body"].get("error")
                if isinstance(body_err, dict):
                    message = body_err.get("message") or str(body_err)
            if not message:
                message = "(no error message found)"
            print(f"- {custom_id}: {message}")
            count += 1
    if count == 0:
        print("(no failed entries found in error file)")


def fmt_ts(ts: int | None) -> str:
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve and display OpenAI batch status")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--batch-id", help="Batch ID (e.g., batch_abc123)")
    grp.add_argument(
        "--model",
        default="gpt-5-mini-2025-08-07",
        help="Model name to infer batch JSON at batch/<ocr-source>-requests-<model>.jsonl.batch.json",
    )
    parser.add_argument(
        "--ocr-source",
        choices=["original", "tesseract"],
        default="original",
        help="Which OCR source was used to build the requests (default: original)",
    )
    parser.add_argument(
        "--errors-out",
        help="Optional path to save the error JSONL (default: batch/raw-batch-output/<basename>.errors.jsonl or batch/raw-batch-output/errors-<batch_id>.jsonl)",
    )
    parser.add_argument(
        "--output-out",
        help="Optional path to save the completed output JSONL (default: batch/raw-batch-output/<basename>.output.jsonl or batch/raw-batch-output/output-<batch_id>.jsonl)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = OpenAI()

    batch_id = args.batch_id
    base_name = None

    # If model is provided, infer batch JSON path and read batch id from it (unless overridden).
    if args.model:
        batch_json_path = Path(__file__).resolve().parent / f"{args.ocr_source}-requests-{args.model}.jsonl.batch.json"
        if not batch_json_path.exists():
            raise SystemExit(f"Batch JSON not found for model {args.model}: {batch_json_path}")

        data = json.loads(batch_json_path.read_text())
        batch_id = data.get("id") or data.get("batch_id") or data.get("batchId")
        if not batch_id:
            raise SystemExit(f"Could not find batch id in {batch_json_path}")

        base_name = f"{args.ocr_source}-requests-{args.model}"

    batch = client.batches.retrieve(batch_id)

    # Header
    print("Batch Status")
    print("============")
    print(f"id:                {batch.id}")
    print(f"status:            {batch.status}")
    print(f"endpoint:          {batch.endpoint}")
    print(f"input_file_id:     {batch.input_file_id}")
    print(f"output_file_id:    {getattr(batch, 'output_file_id', None) or '-'}")
    print(f"error_file_id:     {getattr(batch, 'error_file_id', None) or '-'}")
    print(f"completion_window: {batch.completion_window}")

    # Timestamps
    print("\nTimestamps (UTC)")
    print("----------------")
    print(f"created_at:     {fmt_ts(batch.created_at)}")
    print(f"in_progress_at: {fmt_ts(getattr(batch, 'in_progress_at', None))}")
    print(f"finalizing_at:  {fmt_ts(getattr(batch, 'finalizing_at', None))}")
    print(f"completed_at:   {fmt_ts(getattr(batch, 'completed_at', None))}")
    print(f"failed_at:      {fmt_ts(getattr(batch, 'failed_at', None))}")
    print(f"expired_at:     {fmt_ts(getattr(batch, 'expired_at', None))}")
    print(f"cancelling_at:  {fmt_ts(getattr(batch, 'cancelling_at', None))}")
    print(f"cancelled_at:   {fmt_ts(getattr(batch, 'cancelled_at', None))}")
    print(f"expires_at:     {fmt_ts(getattr(batch, 'expires_at', None))}")

    # Request counts
    counts = getattr(batch, "request_counts", None)
    if counts:
        print("\nRequest Counts")
        print("--------------")
        # request_counts is a pydantic model; access attributes safely
        total = getattr(counts, "total", "-")
        completed = getattr(counts, "completed", "-")
        failed = getattr(counts, "failed", "-")
        print(f"total:     {total}")
        print(f"completed: {completed}")
        print(f"failed:    {failed}")

    # Metadata
    md = getattr(batch, "metadata", None)
    if md:
        print("\nMetadata")
        print("--------")
        for k, v in md.items():
            print(f"{k}: {v}")

    # Always download and summarize errors if available
    error_file_id = getattr(batch, "error_file_id", None)
    output_file_id = getattr(batch, "output_file_id", None)

    if output_file_id:
        default_output = None
        if base_name:
            default_output = Path(__file__).resolve().parent / "raw-batch-output" / f"{base_name}.output.jsonl"
        else:
            default_output = Path(__file__).resolve().parent / "raw-batch-output" / f"output-{batch_id}.jsonl"

        output_path = save_output_file(
            client,
            output_file_id,
            Path(args.output_out) if args.output_out else default_output,
        )
        print(f"\nDownloaded output file to: {output_path}")

    if not error_file_id:
        print("\nNo error file available yet (batch may still be running or no failures).")
        return

    default_errors = None
    if base_name:
        default_errors = Path(__file__).resolve().parent / "raw-batch-output" / f"{base_name}.errors.jsonl"
    else:
        default_errors = Path(__file__).resolve().parent / "raw-batch-output" / f"errors-{batch_id}.jsonl"

    error_path = save_error_file(
        client,
        error_file_id,
        Path(args.errors_out) if args.errors_out else default_errors,
    )
    print(f"\nDownloaded error file to: {error_path}")
    summarize_errors(error_path)


if __name__ == "__main__":
    main()
