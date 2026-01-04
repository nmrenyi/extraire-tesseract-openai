#!/usr/bin/env python3
"""Upload vision input images to Gemini Files API and record file names/URIs.

Reads the Rosenwald benchmark TSV, locates each image under rosenwald-images/<year>/<year>-page-<page>.{png,jpg,jpeg},
uploads to Gemini Files API, and writes one JSONL line per upload with custom_id and Gemini file name/URI.

Output default: batch-gemini-image/uploaded-image-ids.jsonl
"""

import argparse
import csv
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional
from google import genai

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = Path(__file__).resolve().parent / "rosenwald-benchmark-original.tsv"
DEFAULT_IMAGES_ROOT = ROOT / "rosenwald-images"
DEFAULT_OUT = Path(__file__).resolve().parent / "uploaded-image-ids.jsonl"

PROGRESS_EVERY = 1  # update progress output every N rows


def find_image(images_root: Path, year: str, page: str) -> Optional[Path]:
    stem = f"{year}-page-{page}"
    candidates = [
        images_root / year / f"{stem}.png",
        images_root / year / f"{stem}.jpg",
        images_root / year / f"{stem}.jpeg",
    ]
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
            fname = obj.get("file_name")
            if isinstance(cid, str) and isinstance(fname, str):
                mapping[cid] = fname
    return mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload Rosenwald images for Gemini vision batch use")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV, help="Path to benchmark TSV (default: batch-gemini-image/rosenwald-benchmark-original.tsv)")
    parser.add_argument("--images-root", type=Path, default=DEFAULT_IMAGES_ROOT, help="Root folder containing year subfolders (default: rosenwald-images)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Where to write JSONL mapping (default: batch-gemini-image/uploaded-image-ids.jsonl)")
    parser.add_argument("--resume", action="store_true", help="Skip uploads already present in --out")
    parser.add_argument("--limit", type=int, help="Optional max number of uploads")
    parser.add_argument("--workers", type=int, default=16, help="Parallel uploads (default: 16)")
    return parser.parse_args()


def count_rows(tsv_path: Path) -> int:
    total = 0
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if (row.get("year") or "").strip() and (row.get("page") or "").strip():
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
    elapsed_str = format_duration(elapsed)
    eta_str = format_duration(remaining) if rate > 0 else "--:--"
    print(
        f"\rprogress: {done}/{total} ({pct:5.1f}%) elapsed {elapsed_str} eta {eta_str}",
        end="",
        flush=True,
    )


def main() -> None:
    args = parse_args()

    if not args.tsv.exists():
        raise SystemExit(f"Missing TSV: {args.tsv}")
    if not args.images_root.exists():
        raise SystemExit(f"Missing images root: {args.images_root}")

    total_rows = count_rows(args.tsv)

    existing = load_existing(args.out) if args.resume else {}
    client = genai.Client()
    lock = threading.Lock()

    uploaded = 0
    skipped = 0
    missing_images = []
    failed = 0
    processed = 0

    def upload_one(image_path: Path, custom_id: str) -> Dict[str, str]:
        uploaded_file = client.files.upload(file=str(image_path))
        return {
            "custom_id": custom_id,
            "file_name": getattr(uploaded_file, "name", None),
            "uri": getattr(uploaded_file, "uri", None),
            "mime_type": getattr(uploaded_file, "mime_type", None),
            "source_path": str(image_path),
        }

    with args.tsv.open("r", encoding="utf-8", newline="") as f_in, args.out.open("a", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in, delimiter="\t")
        futures = []

        for row in reader:
            year = row.get("year").strip()
            page = row.get("page").strip()

            processed += 1
            custom_id = f"{year}-{page}"

            if args.resume and custom_id in existing:
                skipped += 1
                continue

            image_path = find_image(args.images_root, year, page)
            if not image_path:
                missing_images.append(custom_id)
                continue

            if args.limit and uploaded + len(futures) >= args.limit:
                print("Reached upload limit.")
                break

            futures.append((custom_id, image_path))

        print(f"len(futures): {len(futures)}, uploaded: {uploaded}, skipped: {skipped}, processed: {processed}, tsv: {args.tsv}")

        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            future_map = {pool.submit(upload_one, path, cid): (cid, path) for cid, path in futures}
            completed = 0
            for future in as_completed(future_map):
                cid, path = future_map[future]
                try:
                    record = future.result()
                    with lock:
                        f_out.write(json.dumps(record, ensure_ascii=False))
                        f_out.write("\n")
                        uploaded += 1
                except Exception as exc:  # pragma: no cover
                    failed += 1
                    print(f"upload failed for {cid} ({path}): {exc}")
                finally:
                    with lock:
                        completed += 1
                        if PROGRESS_EVERY and (
                            completed % PROGRESS_EVERY == 0 or completed == len(futures)
                        ):
                            print_progress(completed, len(futures), start_time)
        print()  # ensure the progress line ends with a newline

    print(f"uploaded: {uploaded}")
    print(f"skipped (resume): {skipped}")
    print(f"failed uploads: {failed}")
    print(f"missing images: {len(missing_images)}")
    if missing_images:
        for cid in missing_images[:20]:
            print(f"missing: {cid}")
        if len(missing_images) > 20:
            print("... (truncated)")


if __name__ == "__main__":
    main()
