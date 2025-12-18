#!/usr/bin/env python3
"""Build OpenAI vision batch JSONL requests from the Rosenwald benchmark TSV.

For each TSV row (year, page), look up the uploaded image file_id, attach the
combined image instructions/example, and emit a /v1/responses batch request.

Outputs: batch-openai-image/image-requests-<model>.jsonl by default.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
INSTR_RAW = ROOT / "instructions-image-input.txt"
INSTR_EXAMPLE = ROOT / "instructions-example-output.tsv"
DEFAULT_TSV = Path(__file__).resolve().parent / "rosenwald-benchmark-original.tsv"
DEFAULT_MAPPING = Path(__file__).resolve().parent / "uploaded-image-ids.jsonl"


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
        f"### IMAGE À TRAITER:\nAnalysez l'image ci-jointe et extrayez les données médicales selon les instructions ci-dessus."
    )


def load_mapping(path: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not path.exists():
        raise SystemExit(f"Missing mapping file: {path}. Run upload_openai_images.py first.")

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
    parser = argparse.ArgumentParser(description="Build OpenAI vision batch JSONL requests")
    parser.add_argument(
        "--tsv",
        type=Path,
        default=DEFAULT_TSV,
        help="Benchmark TSV with year/page columns (default: batch-openai-image/rosenwald-benchmark-original.tsv)",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="JSONL produced by upload_openai_images.py with custom_id/file_id (default: uploaded-image-ids.jsonl)",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini-2025-08-07",
        help="OpenAI vision-capable model name (default: gpt-5-mini-2025-08-07)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSONL path (default: batch-openai-image/image-requests-<model>.jsonl)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.tsv.exists():
        raise SystemExit(f"Missing TSV: {args.tsv}")

    mapping = load_mapping(args.mapping)
    instructions = load_instructions()

    out_path = args.output or (Path(__file__).resolve().parent / f"image-requests-{args.model}.jsonl")

    requests = []
    missing_ids = []

    with args.tsv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = (row.get("year") or "").strip()
            page = (row.get("page") or "").strip()
            if not year or not page:
                continue
            custom_id = f"{year}-{page}"
            file_id = mapping.get(custom_id)
            if not file_id:
                missing_ids.append(custom_id)
                continue

            body = {
                "model": args.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": instructions},
                            {"type": "input_image", "file_id": file_id},
                        ],
                    }
                ],
            }

            requests.append(
                {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": body,
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False))
            f.write("\n")

    print(f"Wrote {len(requests)} requests to {out_path}")
    if missing_ids:
        print(f"Missing file_ids for {len(missing_ids)} entries (not written):")
        for cid in missing_ids[:20]:
            print(f"  {cid}")
        if len(missing_ids) > 20:
            print("  ... (truncated)")


if __name__ == "__main__":
    main()
