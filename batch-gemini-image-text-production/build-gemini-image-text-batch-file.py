#!/usr/bin/env python3
"""Build Gemini multimodal batch JSONL requests (image + OCR text).

For each TSV row (year, page, text), look up the uploaded image file (uri/name),
combine the vision instructions/example with the OCR text, and emit a Gemini batch
request line. The resulting prompt gives the model both the OCR text and the image.

Defaults reuse the existing Gemini vision uploads/benchmarks in batch-gemini-image/.

Outputs: batch-gemini-image-text/image-text-requests-<model>.jsonl by default.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
INSTR_RAW = ROOT / "instructions-image-input.txt"
INSTR_EXAMPLE = ROOT / "instructions-example-output.tsv"
TSV_PATHS = {
    "original": ROOT / "batch-gemini-image-text-production" / "rosenwald-benchmark-original.tsv",
}
DEFAULT_MAPPING = ROOT / "batch-gemini-image-text-production" / "uploaded-image-ids.jsonl"
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


def load_mapping(path: Path) -> Dict[str, Dict[str, str]]:
    mapping: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        raise SystemExit(
            f"Missing mapping file: {path}. Run batch-gemini-image/upload_gemini_images.py first."
        )

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
            if not isinstance(cid, str):
                continue
            mapping[cid] = {
                "file_name": obj.get("file_name"),
                "uri": obj.get("uri"),
                "mime_type": obj.get("mime_type"),
            }
    return mapping


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
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="JSONL produced by upload_gemini_images.py with custom_id/file info",
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

    mapping = load_mapping(args.mapping)
    instructions = load_instructions()

    out_path = args.output or (
        Path(__file__).resolve().parent / f"image-text-requests-{args.model}.jsonl"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    requests = []
    missing_ids = []
    missing_text = 0

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            year = (row.get("year") or "").strip()
            page = (row.get("page") or "").strip()
            text = row.get("text")

            if not year or not page:
                continue

            normalized_text = (text or "").replace(r"\n", "\n").replace(r"\t", "\t")
            if not normalized_text.strip():
                missing_text += 1

            custom_id = f"{year}-{page}"
            info = mapping.get(custom_id)
            if not info:
                missing_ids.append(custom_id)
                continue

            file_uri = info.get("uri") or info.get("file_name")
            if not file_uri:
                missing_ids.append(custom_id)
                continue

            mime_type = info.get("mime_type")
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
                                "file_data": {
                                    "file_uri": file_uri,
                                    **({"mime_type": mime_type} if mime_type else {}),
                                }
                            },
                        ]
                    }
                ]
            }

            requests.append({"key": custom_id, "request": request})

    with out_path.open("w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False))
            f.write("\n")

    print(f"Wrote {len(requests)} requests to {out_path}")
    if missing_ids:
        print(f"Missing file references for {len(missing_ids)} entries (not written):")
        for cid in missing_ids[:20]:
            print(f"  {cid}")
        if len(missing_ids) > 20:
            print("  ... (truncated)")
    if missing_text:
        print(f"Entries missing OCR text: {missing_text}")


if __name__ == "__main__":
    main()
