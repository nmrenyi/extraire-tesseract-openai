#!/usr/bin/env python3
"""Check OpenAI batch status and print a readable summary."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI


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
        help="Model name to infer batch JSON at batch/original-ocr-requests-<model>.jsonl.batch.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = OpenAI()

    batch_id = args.batch_id

    # If model is provided, infer batch JSON path and read batch id from it (unless overridden).
    if args.model:
        batch_json_path = Path(__file__).resolve().parent / f"original-ocr-requests-{args.model}.jsonl.batch.json"
        if not batch_json_path.exists():
            raise SystemExit(f"Batch JSON not found for model {args.model}: {batch_json_path}")

        data = json.loads(batch_json_path.read_text())
        batch_id = data.get("id") or data.get("batch_id") or data.get("batchId")
        if not batch_id:
            raise SystemExit(f"Could not find batch id in {batch_json_path}")

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


if __name__ == "__main__":
    main()
