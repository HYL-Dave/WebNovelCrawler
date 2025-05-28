#!/usr/bin/env python3
"""
OCR experiment using GPT-4.1-mini:
- Split input image into chunks
- Transcribe each chunk via GPT-4.1-mini vision
- Merge results and compare against reference text

Dependencies:
  pip install openai pillow

Usage:
  python gpt4_mini_ocr_experiment.py \
      --image precise_output_v2/0120_chapter.png \
      --ref precise_output_v2/0120_chapter.txt \
      [--chunk_height 1000] [--model gpt-4.1-mini]
"""

import argparse
import os
from difflib import SequenceMatcher

from PIL import Image
import openai


def split_image(image_path: str, max_height: int) -> list[str]:
    """Split the image vertically into chunks of max_height."""
    img = Image.open(image_path)
    width, height = img.size
    chunks = []
    base, _ = os.path.splitext(image_path)
    for idx, top in enumerate(range(0, height, max_height)):
        bottom = min(top + max_height, height)
        box = (0, top, width, bottom)
        chunk = img.crop(box)
        chunk_path = f"{base}_chunk_{idx}.png"
        chunk.save(chunk_path)
        chunks.append(chunk_path)
    return chunks


def ocr_chunk(image_path: str, model: str) -> str:
    """Call GPT model to OCR the given image chunk."""
    with open(image_path, "rb") as f:
        # Use the new OpenAI Python client interface for chat completions (openai>=1.0.0)
        resp = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "请识别以下图片中的文字，并仅返回纯文本，不要额外说明："},
                {"role": "user", "content": f},
            ],
        )
    return resp.choices[0].message.content.strip()


def compute_accuracy(reference: str, hypothesis: str) -> float:
    """Compute simple similarity ratio between reference and hypothesis."""
    return SequenceMatcher(None, reference, hypothesis).ratio()


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
    args = parser.parse_args()

    # Split image and run OCR on each part
    chunks = split_image(args.image, args.chunk_height)
    outputs = []
    for idx, chunk_path in enumerate(chunks, 1):
        print(f"[{idx}/{len(chunks)}] OCR chunk: {chunk_path}")
        text = ocr_chunk(chunk_path, args.model)
        outputs.append(text)

    result_text = "\n".join(outputs).strip()

    # Save OCR result
    out_file = f"{os.path.splitext(args.image)[0]}_ocr_{args.model}.txt"
    with open(out_file, "w", encoding="utf-8") as outf:
        outf.write(result_text)
    print(f"OCR output saved to {out_file}")

    # Load reference and compute accuracy
    with open(args.ref, "r", encoding="utf-8") as ref_f:
        reference = ref_f.read().strip()

    accuracy = compute_accuracy(reference, result_text)
    print(f"Accuracy vs reference: {accuracy:.2%}")


if __name__ == "__main__":
    main()