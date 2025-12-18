import argparse
import json
from pathlib import Path
from typing import Optional, Tuple


def infer_bucket_name(input_path: Path) -> Tuple[str, str, str]:
    """Infer (source, model, bucket) from the filename."""
    base = input_path.name
    for suffix in (".output.jsonl", ".errors.jsonl", ".jsonl"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    if "-requests-" in base:
        source, model = base.split("-requests-", 1)
    else:
        source, model = "unknown", base
    bucket = f"{source}-{model}"
    return source, model, bucket


def safe_stem(custom_id: str, fallback: str) -> str:
    raw = custom_id or fallback
    return "".join(ch if ch.isalnum() or ch in ("-", ".", "_") else "_" for ch in raw)


def extract_text(obj: dict, line_no: int, errors: list[str]) -> Optional[str]:
    response = obj.get("response")
    if not isinstance(response, dict):
        errors.append(f"line {line_no}: missing response")
        return None
    if response.get("status_code") != 200:
        errors.append(f"line {line_no}: status_code {response.get('status_code')}")
        return None
    body = response.get("body")
    if not isinstance(body, dict):
        errors.append(f"line {line_no}: missing body")
        return None
    output = body.get("output")
    if not isinstance(output, list):
        errors.append(f"line {line_no}: missing output list")
        return None
    message = next((item for item in output if item.get("type") == "message"), None)
    if not message:
        errors.append(f"line {line_no}: no message output")
        return None
    content_list = message.get("content") or []
    text_item = next(
        (c for c in content_list if c.get("type") == "output_text" and isinstance(c.get("text"), str)),
        None,
    )
    if not text_item:
        errors.append(f"line {line_no}: no output_text content")
        return None
    return text_item["text"].rstrip("\n")


def process_file(input_path: Path, output_root: Path) -> tuple[int, list[str], Path]:
    source, model, bucket = infer_bucket_name(input_path)
    dest_dir = output_root / bucket
    dest_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    written = 0

    for line_no, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: json decode error: {exc}")
            continue
        text = extract_text(obj, line_no, errors)
        if text is None:
            continue
        stem = safe_stem(obj.get("custom_id", ""), f"line-{line_no:04d}")
        out_path = dest_dir / f"{stem}.tsv"
        out_path.write_text(text + "\n", encoding="utf-8")
        written += 1

    return written, errors, dest_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and extract TSV outputs from batch JSONL results.")
    parser.add_argument("input", type=Path, help="Path to the .output.jsonl file")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("batch/raw-output-tsv"),
        help="Base directory to write TSV files (default: batch/raw-output-tsv)",
    )
    args = parser.parse_args()

    written, errors, dest_dir = process_file(args.input, args.output_root)

    print(f"validated lines: {written}")
    print(f"errors: {len(errors)}")
    if errors:
        for msg in errors:
            print(msg)
    print(f"tsv outputs saved under {dest_dir}")


if __name__ == "__main__":
    main()
