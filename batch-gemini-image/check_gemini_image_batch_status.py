#!/usr/bin/env python3
"""Check Gemini vision batch status, optionally download output/error, and summarize failures."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from google import genai

TERMINAL_STATES = {
    "PROCESSING_COMPLETE",
    "FAILED",
    "CANCELLED",
}


def fmt_ts(ts) -> str:
    """Format timestamps that may be seconds or already datetime objects."""
    if ts is None:
        return "-"
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")


def save_bytes(client: genai.Client, file_name: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with client.files.download(file_name) as fsrc:
        target.write_bytes(fsrc.read())
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
            key = obj.get("key") or obj.get("custom_id") or "(no key)"
            resp = obj.get("response") if isinstance(obj.get("response"), dict) else None
            err = obj.get("error") or (resp.get("error") if resp else None)
            message = None
            if isinstance(err, dict):
                message = err.get("message") or err.get("error") or str(err)
            if not message:
                message = "(no error message found)"
            print(f"- {key}: {message}")
            count += 1
    if count == 0:
        print("(no failed entries found in error file)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve and display Gemini vision batch status")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--batch-name", help="Batch name (e.g., batches/abc123)")
    grp.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Model name to infer batch JSON at batch-gemini-image/image-requests-<model>.jsonl.batch.json",
    )
    parser.add_argument(
        "--errors-out",
        help="Optional path to save the error JSONL (default: batch-gemini-image/raw-batch-output/<basename>.errors.jsonl or errors-<batch_name>.jsonl)",
    )
    parser.add_argument(
        "--output-out",
        help="Optional path to save the output JSONL (default: batch-gemini-image/raw-batch-output/<basename>.output.jsonl or output-<batch_name>.jsonl)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = genai.Client()

    batch_name = args.batch_name
    base_name = None

    if args.model and not batch_name:
        batch_json_path = Path(__file__).resolve().parent / f"image-requests-{args.model}.jsonl.batch.json"
        if not batch_json_path.exists():
            raise SystemExit(f"Batch JSON not found for model {args.model}: {batch_json_path}")

        data = json.loads(batch_json_path.read_text())
        batch_name = data.get("name") or data.get("batch") or data.get("batch_name")
        if not batch_name:
            raise SystemExit(f"Could not find batch name in {batch_json_path}")

        base_name = f"image-requests-{args.model}"

    batch = client.batches.get(name=batch_name)

    print("Batch Status")
    print("============")
    print(f"name:              {batch.name}")
    print(f"state:             {batch.state.name if batch.state else '-'}")
    print(f"output_file:       {getattr(batch, 'output_file', None) or '-'}")
    print(f"error_file:        {getattr(batch, 'error_file', None) or '-'}")
    print(f"display_name:      {getattr(batch, 'display_name', None) or '-'}")

    print("\nTimestamps (UTC)")
    print("----------------")
    print(f"create_time:   {fmt_ts(getattr(batch, 'create_time', None))}")
    print(f"start_time:    {fmt_ts(getattr(batch, 'start_time', None))}")
    print(f"end_time:      {fmt_ts(getattr(batch, 'end_time', None))}")

    if getattr(batch, "stats", None):
        stats = batch.stats
        print("\nRequest Counts")
        print("--------------")
        print(f"total:     {getattr(stats, 'total_count', '-')}")
        print(f"success:   {getattr(stats, 'success_count', '-')}")
        print(f"error:     {getattr(stats, 'error_count', '-')}")

    error_file = getattr(batch, "error_file", None)
    output_file = getattr(batch, "output_file", None)

    if output_file:
        default_output = None
        if base_name:
            default_output = Path(__file__).resolve().parent / "raw-batch-output" / f"{base_name}.output.jsonl"
        else:
            safe_name = batch_name.split("/")[-1]
            default_output = Path(__file__).resolve().parent / "raw-batch-output" / f"output-{safe_name}.jsonl"

        output_path = save_bytes(
            client,
            output_file,
            Path(args.output_out) if args.output_out else default_output,
        )
        print(f"\nDownloaded output file to: {output_path}")

    if not error_file:
        print("\nNo error file available yet (batch may still be running or no failures).")
        return

    default_errors = None
    if base_name:
        default_errors = Path(__file__).resolve().parent / "raw-batch-output" / f"{base_name}.errors.jsonl"
    else:
        safe_name = batch_name.split("/")[-1]
        default_errors = Path(__file__).resolve().parent / "raw-batch-output" / f"errors-{safe_name}.jsonl"

    error_path = save_bytes(
        client,
        error_file,
        Path(args.errors_out) if args.errors_out else default_errors,
    )
    print(f"\nDownloaded error file to: {error_path}")
    summarize_errors(error_path)


if __name__ == "__main__":
    main()
