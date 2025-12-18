#!/usr/bin/env python3
"""Upload vision input images to OpenAI and record file_ids.

Reads the Rosenwald benchmark TSV, locates each image under rosenwald-images/<year>/<year>-page-<page>.{png,jpg,jpeg},
uploads it with purpose="vision", and writes one JSONL line per upload with custom_id and file_id.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Optional
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = Path(__file__).resolve().parent / "rosenwald-benchmark-original.tsv"
DEFAULT_IMAGES_ROOT = ROOT / "rosenwald-images"
DEFAULT_OUT = Path(__file__).resolve().parent / "uploaded-image-ids.jsonl"

PROGRESS_EVERY = 1  # update progress output every N rows


def find_image(images_root: Path, year: str, page: str) -> Optional[Path]:
    stem = f"{year}-page-{page}"
    candidates = [images_root / year / f"{stem}.png", images_root / year / f"{stem}.jpg", images_root / year / f"{stem}.jpeg"]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def load_existing(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    mapping: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = obj.get("custom_id")
            fid = obj.get("file_id")
            if isinstance(cid, str) and isinstance(fid, str):
                mapping[cid] = fid
    return mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload Rosenwald images for OpenAI vision batch use")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV, help="Path to benchmark TSV (default: batch-openai-image/rosenwald-benchmark-original.tsv)")
    parser.add_argument("--images-root", type=Path, default=DEFAULT_IMAGES_ROOT, help="Root folder containing year subfolders (default: rosenwald-images)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Where to write JSONL mapping (default: batch-openai-image/uploaded-image-ids.jsonl)")
    parser.add_argument("--resume", action="store_true", help="Skip uploads already present in --out")
    parser.add_argument("--limit", type=int, help="Optional max number of uploads")
    return parser.parse_args()


def count_rows(tsv_path: Path) -> int:
    """Count data rows with year/page present for progress estimation."""
    total = 0
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if (row.get("year") or "").strip() and (row.get("page") or "").strip():
                total += 1
    return total


def print_progress(done: int, total: int) -> None:
    if total <= 0:
        return
    pct = (done / total) * 100
    print(f"\rprogress: {done}/{total} ({pct:5.1f}%)", end="", flush=True)


def main() -> None:
    args = parse_args()

    if not args.tsv.exists():
        raise SystemExit(f"Missing TSV: {args.tsv}")
    if not args.images_root.exists():
        raise SystemExit(f"Missing images root: {args.images_root}")

    total_rows = count_rows(args.tsv)

    existing = load_existing(args.out) if args.resume else {}
    client = OpenAI()

    uploaded = 0
    skipped = 0
    missing_images = []
    processed = 0

    with args.tsv.open("r", encoding="utf-8", newline="") as f_in, args.out.open("a", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in, delimiter="\t")
        for row in reader:
            year = (row.get("year") or "").strip()
            page = (row.get("page") or "").strip()
            if not year or not page:
                continue
            processed += 1

            if processed % PROGRESS_EVERY == 0:
                print_progress(processed, total_rows)

            custom_id = f"{year}-{page}"

            if args.resume and custom_id in existing:
                skipped += 1
                continue

            image_path = find_image(args.images_root, year, page)
            if not image_path:
                missing_images.append(custom_id)
                continue

            with image_path.open("rb") as img_file:
                upload = client.files.create(file=img_file, purpose="vision")

            record = {
                "custom_id": custom_id,
                "file_id": upload.id,
                "filename": upload.filename if hasattr(upload, "filename") else None,
                "source_path": str(image_path),
            }
            f_out.write(json.dumps(record, ensure_ascii=False))
            f_out.write("\n")
            uploaded += 1

            if args.limit and uploaded >= args.limit:
                break

    # Final progress update
    if total_rows:
        print_progress(processed, total_rows)
        print()

    print(f"uploaded: {uploaded}")
    print(f"skipped (resume): {skipped}")
    print(f"missing images: {len(missing_images)}")
    if missing_images:
        for cid in missing_images[:20]:
            print(f"missing: {cid}")
        if len(missing_images) > 20:
            print("... (truncated)")


if __name__ == "__main__":
    main()
