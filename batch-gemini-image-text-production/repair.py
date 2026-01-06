"""Utility for repairing malformed TSVs produced by machine annotators."""

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Repair TSV outputs for reviewer comparison")
	parser.add_argument(
		"--input-dir",
		type=Path,
		default=Path(__file__).resolve().parent / "raw-output-tsv" / "gemini-3-pro-image-text",
		help="Directory containing TSV files to repair",
	)
	parser.add_argument(
		"--pattern",
		default="*.tsv",
		help="Glob pattern (relative to input-dir) for TSV files to repair",
	)
	parser.add_argument(
		"--recursive",
		action="store_true",
		help="Recurse into subdirectories when searching for TSV files",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="Optional limit of files to process (useful for quick checks)",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		default=Path(__file__).resolve().parent / "repaired-tsv",
		help="Directory to store repaired TSVs (default: repaired-tsv beside this script)",
	)
	return parser.parse_args()


DEFAULT_HEADERS = ["nom", "année", "notes", "adresse", "horaires"]


def _looks_like_header(headers: List[str]) -> bool:
	normalized = [h.strip().lower() for h in headers]
	return any(h in {"nom", "année", "notes", "adresse", "horaires"} for h in normalized)


def read_tsv(tsv_path: Path) -> Tuple[List[str], List[Dict[str, str]], List[Tuple[int, int, str, bool]]]:
	text = tsv_path.read_text(encoding="utf-8-sig")
	lines = text.splitlines()

	if not lines:
		return [], [], []

	header_reader = csv.reader([lines[0]], delimiter="\t")
	try:
		candidate_headers = next(header_reader)
	except StopIteration:
		return [], [], []

	missing_header = not _looks_like_header(candidate_headers)
	if missing_header and len(candidate_headers) == len(DEFAULT_HEADERS):
		headers = DEFAULT_HEADERS
		data_lines = lines
		start_offset = 1
	else:
		headers = candidate_headers
		data_lines = lines[1:]
		start_offset = 2

	rows: List[Dict[str, str]] = []
	issues: List[Tuple[int, int, str, bool]] = []
	expected_tabs = max(len(headers) - 1, 0)

	for offset, raw_line in enumerate(data_lines, start=start_offset):
		if not raw_line.strip():
			continue

		tab_count = raw_line.count("\t")
		if tab_count == expected_tabs:
			values = raw_line.split("\t")
			assert len(values) == len(headers), (
				f"Line {offset}: expected {len(headers)} columns, got {len(values)}"
			)
			rows.append(dict(zip(headers, values)))
		else:
			repaired = repair_line(raw_line, headers)
			success = repaired is not None
			issues.append((offset, tab_count, raw_line, success))
			if success:
				rows.append(repaired)

	return headers, rows, issues


HORAIRES_PATTERNS = re.compile(
		(
			r"\b(?:Lun|Mar|Mer|Jeu|Ven|Sam|Dim)\b"
			+ r"|\b\d{1,2}(?:\s*[½1/2])?\s*à\s*\d{1,2}(?:\s*[½1/2])?\b"
			+ r"|\bmidi\b"
			+ r"|\bsoir\b"
		)
	)

NOTES_REGEXES = [
		re.compile(pattern, re.IGNORECASE)
		for pattern in (
			r"\bA\s*cc?\.?\s*(?:d[eu]s?\s*)?H[ôo0]p\.?\b",
			r"\bM\.?\s*(?:d[eu]s?\s*)?H[ôo0]p\.?\b",
			r"\bCh?\.?\s*(?:d[eu]s?\s*)?H[ôo0]p\.?\b",
			r"\bAgr[ée]?(?:g[ée])?\.?\b",
			r"\bP\.?\s*F\.?\s*P\.?\b",
			r"\bM\.?\s*A\.?\s*M\.?\b",
			r"\bM\.?\s*A\.?\s*S\.?\b",
			r"\bEx[\-\s]*(?:ou\s+anc\.?\s*)?(?:Int|Intern[ei])\.?\s*d[eu]s?\s*H[ôo0]p\.?\b",
			r"\bLaur?\.?\s*d[eu]\s*l[’']?Acad\.?\b",
			r"\bDent?\.?\b",
			r"\bH[ôo0]p\.?\b",
			r"\bM[ée]d\.?\b",
			r"\bChir?\.?\b",
			r"\bProf?\.?\b",
			r"\bPros?\.?\b",
			r"\bPr[ée]p\.?\b",
			r"\bClin?\.?\b",
			r"\bMal\.?\b",
		)
]


def repair_line(raw_line: str, headers: List[str]) -> Optional[Dict[str, str]]:
	"""Attempt to reconstruct malformed TSV entries following project heuristics."""
	if not headers:
		return None

	parts = [part.strip() for part in raw_line.split("\t") if part.strip()]
	if not parts:
		return None

	nom = parts[0]
	remaining = parts[1:]

	annee = ""
	for idx, fragment in enumerate(remaining):
		year_match = re.search(r"(\d{4})", fragment)
		if year_match:
			annee = year_match.group(1)
			del remaining[idx]
			break

	horaires = ""
	for idx in range(len(remaining) - 1, -1, -1):
		fragment = remaining[idx]
		if HORAIRES_PATTERNS.search(fragment):
			horaires = fragment
			del remaining[idx]
			break

	notes_segments: List[str] = []
	adresse_segments: List[str] = []

	for fragment in remaining:
		matched = any(regex.search(fragment) for regex in NOTES_REGEXES)
		if matched:
			if "," in fragment:
				note_part, _, addr_part = fragment.partition(",")
				notes_segments.append(note_part.strip())
				if addr_part.strip():
					adresse_segments.append(addr_part.strip())
			else:
				notes_segments.append(fragment)
		else:
			adresse_segments.append(fragment)

	notes = ", ".join(notes_segments)
	adresse = ", ".join(adresse_segments)

	fields = [nom, annee, notes, adresse, horaires]
	if len(fields) != len(headers):
		fields.extend([""] * (len(headers) - len(fields)))
	elif len(fields) > len(headers):
		fields = fields[: len(headers)]

	return dict(zip(headers, fields))


def repair_file(tsv_path: Path, output_base: Path, input_root: Path) -> Dict[str, object]:
	headers, rows, tab_issues = read_tsv(tsv_path)
	failed_count = sum(1 for issue in tab_issues if not issue[3])
	rel_path = tsv_path.relative_to(input_root)
	output_path = output_base / rel_path

	if headers:
		output_path.parent.mkdir(parents=True, exist_ok=True)
		with output_path.open("w", encoding="utf-8", newline="") as handle:
			writer = csv.writer(handle, delimiter="\t")
			writer.writerow(headers)
			for row in rows:
				writer.writerow([row.get(header, "") for header in headers])

	return {
		"failed": failed_count,
		"output": output_path if headers else None,
		"total": len(rows),
		"issues": len(tab_issues),
		"headers": headers,
		"tab_issues": tab_issues,
	}


def main() -> None:
	args = parse_args()
	input_dir = args.input_dir.resolve()
	if not input_dir.exists():
		raise FileNotFoundError(f"Input directory not found: {input_dir}")

	search_iter = input_dir.rglob(args.pattern) if args.recursive else input_dir.glob(args.pattern)
	tsv_paths = sorted(path for path in search_iter if path.is_file())
	if args.limit is not None:
		tsv_paths = tsv_paths[: args.limit]

	if not tsv_paths:
		print(f"No TSV files found in {input_dir} matching pattern '{args.pattern}'")
		return

	output_base = args.output_dir.resolve()
	print(f"Input directory: {input_dir}")
	print(f"Output directory: {output_base}")
	print(f"Discovered {len(tsv_paths)} TSV file(s) to repair\n")

	summary: Dict[str, Dict[str, object]] = {}
	for tsv_path in tsv_paths:
		result = repair_file(tsv_path, output_base, input_dir)
		summary[str(tsv_path)] = result

		print(f"Processed {tsv_path.name}: {result['total']} rows")
		if result["headers"]:
			columns = ", ".join(result["headers"])
			print(f"  Columns: {columns}")
		else:
			print("  Warning: TSV missing header row")

		if result["tab_issues"]:
			print("  Tab mismatches detected:")
			for line_no, count, raw_line, success in result["tab_issues"]:
				fields = raw_line.split("\t")
				display = " || ".join(fields)
				status = "repaired" if success else "FAILED"
				print(f"    Line {line_no}: {count} tab(s) [{status}] :: {display}")

		failed_count = result["failed"]
		if failed_count:
			print(f"  WARNING: {failed_count} line(s) could not be repaired.")
		elif result["tab_issues"]:
			print("  All malformed lines repaired.")

		output_path = result["output"]
		if output_path:
			print(f"  Repaired TSV saved to {output_path}\n")
		else:
			print("  Skipped saving due to missing header definition\n")

	print("Repair summary:")
	for tsv_path, data in summary.items():
		failed_count = data.get("failed", 0) if data else 0
		issues = data.get("issues", 0) if data else 0
		output_path = data.get("output") if data else None
		if failed_count:
			message = f"{failed_count} line(s) unrepaired"
		elif issues:
			message = "fully repaired"
		else:
			message = "no issues detected"
		location = f" -> {output_path}" if output_path else ""
		print(f"  {Path(tsv_path).name}: {message}{location}")


if __name__ == "__main__":
	main()
