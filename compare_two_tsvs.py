#!/usr/bin/env python3
"""Compare two golden-truth TSV files using jiwer metrics (WER/CER) and alignments."""
import argparse
from pathlib import Path

import jiwer


def load_tsv(path: str) -> str:
    text = Path(path).read_text(encoding="utf-8").strip().replace("\t", " ")
    return " ".join(text.split("\n")[1:])  # drop header, join rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two TSV files using jiwer metrics.")
    parser.add_argument(
        "--hyp",
        dest="hyp_path",
        type=Path,
        default=Path("/Users/renyi/Downloads/rosenwald/extraire-tesseract-openai/golden-truth/colab-1887-32.tsv"),
        help="Hypothesis TSV path (default: current hardcoded value)",
    )

    args = parser.parse_args()

    # Absolute paths requested by the user
    ref_path = Path("/Users/renyi/Downloads/rosenwald/extraire-tesseract-openai/golden-truth/1887-page-0032.tsv")
    hyp_path = args.hyp_path

    reference = load_tsv(ref_path)
    hypothesis = load_tsv(hyp_path)

    tr_word = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.Strip(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.ReduceToListOfListOfWords(),
    ])

    tr_char = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.Strip(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.ReduceToListOfListOfChars(),
    ])

    word_compare = jiwer.process_words(reference, hypothesis, tr_word, tr_word)
    char_compare = jiwer.process_characters(reference, hypothesis, tr_char, tr_char)

    print(f"Reference: {ref_path}")
    print(f"Hypothesis: {hyp_path}\n")
    print(f"WER: {word_compare.wer:.4f}")
    print(f"CER: {char_compare.cer:.4f}\n")
    print("Word alignment:\n" + jiwer.visualize_alignment(word_compare))
    print("\nCharacter alignment:\n" + jiwer.visualize_alignment(char_compare))


if __name__ == "__main__":
    main()
