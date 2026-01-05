#!/usr/bin/env python3
"""Build Gemini multimodal batch JSONL requests (image + OCR text).

For each TSV row (year, page, text), look up the uploaded image file (uri/name),
combine the vision instructions/example with the OCR text, and emit a Gemini batch
request line. The resulting prompt gives the model both the OCR text and the image.

Defaults reuse the existing Gemini vision uploads/benchmarks in batch-gemini-image/.

Outputs: batch-gemini-image-text/image-text-requests-<model>.jsonl by default.
"""

import argparse
import base64
import csv
import json
import mimetypes
import time
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
INSTR_RAW = ROOT / "instructions-image-input.txt"
INSTR_EXAMPLE = ROOT / "instructions-example-output.tsv"
TSV_PATHS = {
    "original": ROOT / "batch-gemini-image-text-production" / "rosenwald-benchmark-original.tsv",
}
DEFAULT_IMAGES_ROOT = ROOT / "rosenwald-images"
DEFAULT_MODEL = "gemini-3-pro-preview"


def load_instructions() -> str:
    if not INSTR_RAW.exists():
        raise SystemExit(f"Missing instructions file: {INSTR_RAW}")
    if not INSTR_EXAMPLE.exists():
        raise SystemExit(f"Missing example file: {INSTR_EXAMPLE}")

    raw_text = INSTR_RAW.read_text(encoding="utf-8").strip()
    example_text = INSTR_EXAMPLE.read_text(encoding="utf-8").strip()
    return (
        f"{raw_text}\n\n"
        f"### EXEMPLE DE FORMAT ATTENDU:\n{example_text}\n\n"
        f"### IMAGE À TRAITER:\nAnalysez l'image ci-jointe et combinez-la avec le texte OCR fourni."
        f"\n\nIMPORTANT: En cas de conflit entre l'image et le texte OCR, l'image fait autorité."
    )


def find_image(images_root: Path, year: str, page: str) -> Optional[Path]:
    stem = f"{year}-page-{page}"
    for ext in (".png", ".jpg", ".jpeg"):
        cand = images_root / year / f"{stem}{ext}"
        if cand.exists():
            return cand
    return None


def infer_mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def count_rows(tsv_path: Path) -> int:
    total = 0
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = (row.get("year") or "").strip()
            page = (row.get("page") or "").strip()
            if year and page:
                total += 1
    return total


def format_duration(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def print_progress(done: int, total: int, start_time: float) -> None:
    if total <= 0:
        return
    pct = (done / total) * 100
    elapsed = time.perf_counter() - start_time
    rate = (done / elapsed) if elapsed > 0 else 0
    remaining = ((total - done) / rate) if rate > 0 else 0
    print(
        f"\rprogress: {done}/{total} ({pct:5.1f}%) elapsed {format_duration(elapsed)} eta {format_duration(remaining) if rate > 0 else '--:--'}",
        end="",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Gemini multimodal (image + OCR text) batch JSONL requests"
    )
    parser.add_argument(
        "--source",
        choices=sorted(TSV_PATHS.keys()),
        default="original",
        help="Which benchmark TSV to read (default: original)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model name for filename tagging (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--images-root",
        type=Path,
        default=DEFAULT_IMAGES_ROOT,
        help="Root folder containing rendered images (default: rosenwald-images)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=25,
        help="Print progress every N processed rows (default: 25)",
    )
    parser.add_argument(
        "--chunk-max-bytes",
        type=int,
        default=1_800_000_000,
        help="Approximate max bytes per chunk file before rotating (default: 1.8GB)",
    )
    parser.add_argument(
        "--chunk-dir",
        type=Path,
        help="Optional subfolder for chunked outputs (default: <output-stem>-chunks next to output)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output JSONL path (default: batch-gemini-image-text/image-text-requests-<model>.jsonl)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tsv_path = TSV_PATHS[args.source]
    if not tsv_path.exists():
        raise SystemExit(f"Missing TSV: {tsv_path}")

    if not args.images_root.exists():
        raise SystemExit(f"Images root not found: {args.images_root}")
    instructions = load_instructions()

    total_rows = count_rows(tsv_path)
    progress_every = max(1, args.progress_every)
    start_time = time.perf_counter()

    out_path = args.output or (
        Path(__file__).resolve().parent / f"image-text-requests-{args.model}.jsonl"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunk_dir = args.chunk_dir or (out_path.parent / f"{out_path.stem}-chunks")
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunk_max_bytes = max(1, args.chunk_max_bytes)
    buffer = []
    chunk_index = 1
    written_total = 0
    chunks_written = 0
    current_bytes = 0

    missing_images = []
    missing_text = 0
    processed = 0

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = (row.get("year") or "").strip()
            page = (row.get("page") or "").strip()
            text = row.get("text")

            if not year or not page:
                continue

            processed += 1

            normalized_text = (text or "").replace(r"\n", "\n").replace(r"\t", "\t")
            if not normalized_text.strip():
                missing_text += 1

            custom_id = f"{year}-{page}"
            image_path = find_image(args.images_root, year, page)
            if not image_path:
                missing_images.append(custom_id)
                continue

            mime_type = infer_mime_type(image_path)
            image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
            prompt = (
                f"{instructions}\n\n"
                f"### TEXTE OCR SUPPLÉMENTAIRE\n"
                f"{normalized_text if normalized_text.strip() else '(aucun texte OCR fourni)'}"
            )

            request = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_b64,
                                }
                            },
                        ]
                    }
                ]
            }

            line = json.dumps({"key": custom_id, "request": request}, ensure_ascii=False)
            line_bytes = len(line.encode("utf-8")) + 1  # newline

            buffer.append(line)
            current_bytes += line_bytes

            if current_bytes >= chunk_max_bytes:
                chunk_path = chunk_dir / f"{out_path.stem}-part-{chunk_index:04d}.jsonl"
                with chunk_path.open("w", encoding="utf-8") as f_out:
                    for ln in buffer:
                        f_out.write(ln)
                        f_out.write("\n")
                written_total += len(buffer)
                chunks_written += 1
                chunk_index += 1
                buffer.clear()
                current_bytes = 0

            if total_rows and (processed % progress_every == 0 or processed == total_rows):
                print_progress(processed, total_rows, start_time)

    if total_rows:
        print()

    if buffer:
        chunk_path = chunk_dir / f"{out_path.stem}-part-{chunk_index:04d}.jsonl"
        with chunk_path.open("w", encoding="utf-8") as f_out:
            for ln in buffer:
                f_out.write(ln)
                f_out.write("\n")
        written_total += len(buffer)
        chunks_written += 1
        buffer.clear()

    print(f"Wrote {written_total} requests across {chunks_written} file(s) in {chunk_dir}")
    if missing_images:
        print(f"Missing images for {len(missing_images)} entries (not written):")
        for cid in missing_images[:20]:
            print(f"  {cid}")
        if len(missing_images) > 20:
            print("  ... (truncated)")
    if missing_text:
        print(f"Entries missing OCR text: {missing_text}")


if __name__ == "__main__":
    main()
