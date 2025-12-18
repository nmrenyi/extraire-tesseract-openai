#!/usr/bin/env python3
"""Check Gemini batch status and optionally download the output file.

Default paths are relative to the batch-gemini folder.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from google import genai

ROOT = Path(__file__).resolve().parent


def fmt_dt(dt) -> str:
    if dt is None:
        return "-"
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve and display Gemini batch status")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--batch-name", help="Full batch name, e.g., batches/abc123")
    grp.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="Model name to infer batch JSON at batch-gemini/<ocr>-requests-<model>.jsonl.batch.json (default: gemini-3-flash-preview)",
    )
    parser.add_argument(
        "--ocr-source",
        choices=["original", "tesseract"],
        default="original",
        help="Which OCR source was used to build the requests (default: original)",
    )
    parser.add_argument(
        "--output-out",
        help="Optional path to save the output JSONL (default: batch-gemini/raw-batch-output/<basename>.output.jsonl)",
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Poll until job reaches a terminal state before printing and downloading",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds to sleep between polls when --poll is set (default: 30)",
    )
    return parser.parse_args()


def infer_batch_name(model: str, ocr_source: str) -> tuple[str, str]:
    base = f"{ocr_source}-requests-{model}"
    batch_json_path = ROOT / f"{base}.jsonl.batch.json"
    if not batch_json_path.exists():
        raise SystemExit(f"Batch JSON not found for model {model}: {batch_json_path}")
    data = json.loads(batch_json_path.read_text())
    batch_name = data.get("name") or data.get("id") or data.get("batch_id")
    if not batch_name:
        raise SystemExit(f"Could not find batch name in {batch_json_path}")
    return batch_name, base


def download_output(client: genai.Client, file_name: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    content = client.files.download(file=file_name)
    target.write_bytes(content)
    return target


def main() -> None:
    args = parse_args()
    client = genai.Client()

    if args.batch_name:
        batch_name = args.batch_name
        base_name = None
    else:
        batch_name, base_name = infer_batch_name(args.model, args.ocr_source)

    completed_states = {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED",
        "JOB_STATE_EXPIRED",
    }

    batch = client.batches.get(name=batch_name)

    if args.poll:
        print(f"Polling status for job: {batch_name}")
        while batch.state.name not in completed_states:
            print(f"Current state: {batch.state.name}")
            time.sleep(args.poll_interval)
            batch = client.batches.get(name=batch_name)
        print(f"Job finished with state: {batch.state.name}")

    print("Batch Status")
    print("============")
    print(f"name:        {batch.name}")
    print(f"state:       {batch.state.name if getattr(batch, 'state', None) else '-'}")
    print(f"model:       {getattr(batch, 'model', '-')}")

    if getattr(batch, "error", None):
        print(f"error:       {batch.error}")

    print("\nTimestamps")
    print("-----------")
    print(f"create_time: {fmt_dt(getattr(batch, 'create_time', None))}")
    print(f"end_time:    {fmt_dt(getattr(batch, 'end_time', None))}")

    dest = getattr(batch, "dest", None)

    if batch.state.name != "JOB_STATE_SUCCEEDED":
        print(f"\nJob not succeeded. Final state: {batch.state.name}")
        if getattr(batch, "error", None):
            print(f"Error: {batch.error}")
        return

    if dest and getattr(dest, "file_name", None):
        default_output = None
        if base_name:
            default_output = ROOT / "raw-batch-output" / f"{base_name}.output.jsonl"
        else:
            safe_name = batch.name.replace("/", "_")
            default_output = ROOT / "raw-batch-output" / f"output-{safe_name}.jsonl"

        output_path = download_output(
            client,
            dest.file_name,
            Path(args.output_out) if args.output_out else default_output,
        )
        print(f"\nDownloaded output file to: {output_path}")
    elif dest and getattr(dest, "inlined_responses", None):
        print(f"\nInline responses available: {len(dest.inlined_responses)}")
        for idx, inline_response in enumerate(dest.inlined_responses, 1):
            print(f"\n--- Response {idx} ---")
            if getattr(inline_response, "response", None):
                try:
                    print(inline_response.response.text)
                except AttributeError:
                    print(inline_response.response)
            elif getattr(inline_response, "error", None):
                print(f"Error: {inline_response.error}")
    else:
        print("\nNo destination file or inline responses available yet.")


if __name__ == "__main__":
    main()
