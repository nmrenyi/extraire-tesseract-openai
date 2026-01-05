#!/usr/bin/env python3
"""Upload a multimodal (image + OCR text) JSONL and launch Gemini batch job(s).

Quick usage
-----------
- Single file:
        python run_gemini_image_text_batch.py --file path/to/requests.jsonl --model gemini-3-flash-preview

- Chunked directory:
        python run_gemini_image_text_batch.py --chunks-dir path/to/chunks --model gemini-3-flash-preview

Notes
- Expects GOOGLE_API_KEY in the environment.
- Each file is uploaded, then a batch is created; per-file sidecars: *.uploaded_name.txt, *.batch.json.
- In chunk mode, display names get -chunk-XXXX suffix unless you provide --display-name.
"""

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional
from google import genai
from google.genai import types


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload JSONL and launch Gemini multimodal batch job")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--file", help="Path to a single JSONL batch request file")
    grp.add_argument(
        "--chunks-dir",
        type=Path,
        help="Directory containing multiple JSONL chunk files (e.g., chunked outputs)",
    )
    parser.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="Gemini model name (default: gemini-3-flash-preview)",
    )
    parser.add_argument(
        "--display-name",
        help="Optional display name for the batch job (defaults to base filename; in chunk mode, "
             "each chunk gets a suffix)",
    )
    parser.add_argument(
        "--file-name-out",
        help="Where to store the uploaded file name (default: <file>.uploaded_name.txt). Only used in single-file mode.",
    )
    parser.add_argument(
        "--batch-out",
        help="Where to store the created batch info JSON (default: <file>.batch.json). Only used in single-file mode.",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip local JSONL validation before upload",
    )
    parser.add_argument(
        "--glob",
        default="*.jsonl",
        help="Glob to select chunk files inside --chunks-dir (default: *.jsonl)",
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


def upload_and_create(
    client: genai.Client,
    jsonl_path: Path,
    model: str,
    display_name: str,
    file_name_out: Optional[Path],
    batch_out: Optional[Path],
    skip_validate: bool,
) -> None:
    if not jsonl_path.exists():
        raise SystemExit(f"Input file not found: {jsonl_path}")

    if not skip_validate:
        print(f"Validating {jsonl_path} ...")
        validate_jsonl(jsonl_path)
        print("Validation passed.")

    file_name_out = file_name_out or jsonl_path.with_suffix(jsonl_path.suffix + ".uploaded_name.txt")
    batch_out = batch_out or jsonl_path.with_suffix(jsonl_path.suffix + ".batch.json")

    print(f"Uploading {jsonl_path} ...")
    uploaded = client.files.upload(
        file=str(jsonl_path),
        config=types.UploadFileConfig(display_name=display_name, mime_type="application/jsonl"),
    )
    file_name_out.write_text(uploaded.name)
    print(f"Uploaded. file name: {uploaded.name}\nSaved to: {file_name_out}")

    print("Creating batch job ...")
    batch = client.batches.create(
        model=model,
        src=uploaded.name,
        config={"display_name": display_name},
    )
    batch_out.write_text(batch.model_dump_json(indent=2))
    print(
        f"Batch created. name: {batch.name}\nState: {batch.state.name}\nSaved batch info to: {batch_out}"
    )


def iter_chunk_files(chunks_dir: Path, glob_pattern: str) -> Iterable[Path]:
    return sorted(chunks_dir.glob(glob_pattern))


def main() -> None:
    args = parse_args()
    client = genai.Client()

    if args.chunks_dir:
        if not args.chunks_dir.exists():
            raise SystemExit(f"Chunks directory not found: {args.chunks_dir}")

        chunk_files = list(iter_chunk_files(args.chunks_dir, args.glob))
        if not chunk_files:
            raise SystemExit(f"No chunk files matching {args.glob} in {args.chunks_dir}")

        print(f"Found {len(chunk_files)} chunk(s) in {args.chunks_dir}")
        for idx, jsonl_path in enumerate(chunk_files, start=1):
            base_display = args.display_name or jsonl_path.stem
            display_name = f"{base_display}-chunk-{idx:04d}" if len(chunk_files) > 1 else base_display
            print("\n---")
            upload_and_create(
                client=client,
                jsonl_path=jsonl_path,
                model=args.model,
                display_name=display_name,
                file_name_out=None,
                batch_out=None,
                skip_validate=args.skip_validate,
            )
    else:
        jsonl_path = Path(args.file)
        display_name = args.display_name or jsonl_path.stem
        upload_and_create(
            client=client,
            jsonl_path=jsonl_path,
            model=args.model,
            display_name=display_name,
            file_name_out=Path(args.file_name_out) if args.file_name_out else None,
            batch_out=Path(args.batch_out) if args.batch_out else None,
            skip_validate=args.skip_validate,
        )


if __name__ == "__main__":
    main()
