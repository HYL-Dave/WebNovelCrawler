#!/usr/bin/env python3
"""
OCR experiment using GPT-4.1-mini:
- Split input image into overlapping chunks
- Transcribe each chunk via GPT-4.1-mini vision
- Merge results (deduplicate overlaps) and compare against reference text

Dependencies:
  pip install openai pillow

Usage:
  python gpt4_mini_ocr_experiment.py \
      --image precise_output_v2/0120_chapter.png \
      --ref precise_output_v2/0120_chapter.txt \
      [--chunk_height 1000] [--overlap 200] [--min_overlap_chars 10] [--model gpt-4.1-mini] [--proofread_model gpt-4.1-mini]

Example:
  python gpt4_mini_ocr_experiment.py \
      --image precise_output_v2/0120_chapter.png \
      --ref precise_output_v2/0120_chapter.txt \
      --chunk_height 760 \
      --overlap 40 \
      --min_overlap_chars 10 \
      --model gpt-4.1-mini \
      --proofread_model gpt-4.1-mini
"""

import argparse
import os
from difflib import SequenceMatcher

from PIL import Image
import openai
import base64


def split_image(image_path: str, max_height: int, overlap: int) -> list[str]:
    """Split the input image into vertically overlapping chunks."""
    img = Image.open(image_path)
    width, height = img.size
    base, _ = os.path.splitext(image_path)
    if overlap >= max_height:
        raise ValueError("`overlap` must be smaller than `chunk_height`")
    step = max_height - overlap
    chunks: list[str] = []
    top = 0
    idx = 0
    while top < height:
        bottom = min(top + max_height, height)
        tile = img.crop((0, top, width, bottom))
        chunk_path = f"{base}_chunk_{idx}.png"
        tile.save(chunk_path)
        chunks.append(chunk_path)
        idx += 1
        if bottom >= height:
            break
        top += step
    return chunks


def ocr_chunk(image_path: str, model: str) -> str:
    """Call GPT model to OCR the given image chunk via Base64 data URI (openai>=1.x)."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"
    parts = [
        {"type": "text",      "text": "请识别以下图片中的文字，并仅返回纯文本，不要额外说明："},
        {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
    ]
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": parts}],
    )
    return resp.choices[0].message.content.strip()


def compute_accuracy(reference: str, hypothesis: str) -> float:
    """Compute simple similarity ratio between reference and hypothesis."""
    return SequenceMatcher(None, reference, hypothesis).ratio()


def merge_texts(chunks: list[str], min_overlap_chars: int) -> str:
    """Merge OCR outputs from overlapping chunks, removing duplicated overlaps."""
    merged = chunks[0]
    for text in chunks[1:]:
        sm = SequenceMatcher(None, merged, text)
        match = sm.find_longest_match(0, len(merged), 0, len(text))
        if (
            match.size >= min_overlap_chars
            and match.a + match.size == len(merged)
            and match.b == 0
        ):
            text = text[match.size:]
        merged += text
    return merged.strip()


def proofread_text(text: str, model: str = "gpt-4.1-mini") -> str:
    """Use GPT to proofread OCR result, correcting typos/omissions and returning clean text."""
    prompt = (
        "你是中文文本校对助手。\n"
        "下面是一段OCR识别的中文文本，请你纠正其中的错字、漏字或标点，并仅输出校对后的正文：\n\n"
        + text
    )
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(
        description="OCR experiment with GPT-4.1-mini and accuracy measurement"
    )
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--ref", required=True, help="Path to reference text file")
    parser.add_argument(
        "--chunk_height",
        type=int,
        default=1000,
        help="Max height of each image chunk (px)",
    )
    parser.add_argument(
        "--model", default="gpt-4.1-mini", help="GPT model name for OCR"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Vertical overlap between chunks (px)",
    )
    parser.add_argument(
        "--min_overlap_chars",
        type=int,
        default=10,
        help="Min characters to consider overlap when merging text chunks",
    )
    parser.add_argument(
        "--proofread_model",
        default="",
        help="GPT model name for proofreading OCR merged text (skip if empty)",
    )
    args = parser.parse_args()

    # Split image into overlapping chunks and run OCR on each
    chunks = split_image(args.image, args.chunk_height, args.overlap)
    outputs = []
    for idx, chunk_path in enumerate(chunks, 1):
        print(f"[{idx}/{len(chunks)}] OCR chunk: {chunk_path}")
        text = ocr_chunk(chunk_path, args.model)
        outputs.append(text)

    result_text = merge_texts(outputs, args.min_overlap_chars)

    # Save OCR result
    out_file = f"{os.path.splitext(args.image)[0]}_ocr_{args.model}.txt"
    with open(out_file, "w", encoding="utf-8") as outf:
        outf.write(result_text)
    print(f"OCR output saved to {out_file}")

    # Stage 2: optional proofreading with GPT
    if args.proofread_model:
        print(f"[校对阶段] 用 {args.proofread_model} 对合并结果做校对纠错…")
        corrected = proofread_text(result_text, args.proofread_model)
        proof_file = f"{os.path.splitext(args.image)[0]}_ocr_{args.model}_proofread.txt"
        with open(proof_file, "w", encoding="utf-8") as pf:
            pf.write(corrected)
        print(f"Proofread output saved to {proof_file}")
        result_text = corrected

    # Load reference and compute accuracy
    with open(args.ref, "r", encoding="utf-8") as ref_f:
        reference = ref_f.read().strip()

    accuracy = compute_accuracy(reference, result_text)
    print(f"Accuracy vs reference: {accuracy:.2%}")


if __name__ == "__main__":
    main()