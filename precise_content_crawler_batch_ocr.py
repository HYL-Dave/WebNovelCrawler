#!/usr/bin/env python3
"""
Draft script: batch GPT-OCR by grouping all chunks of each image into one request.

This script demonstrates how to split each chapter image into overlapping chunks
and send all chunks from the same image in a single GPT-OCR API call.
It reuses split_image, merge_texts, proofread_text, and the internal cleaning logic
from precise_content_crawler via PreciseContentCrawler._clean_content.
"""

import argparse
import os
import json
import base64
import openai
from precise_content_crawler import split_image, merge_texts, proofread_text, PreciseContentCrawler

def clean_content(text: str) -> str:
    """Invoke internal cleaning logic from PreciseContentCrawler._clean_content."""
    return PreciseContentCrawler._clean_content(None, text)

def ocr_chunks_batch(image_paths: list[str], model: str) -> list[str]:
    """
    Batch OCR for multiple chunks: send a single request with multiple image_url parts.
    Expects a JSON array of recognized texts corresponding to image_paths order.
    """
    parts = [
        {"type": "text", "text": (
            "请识别以下多张图片（按顺序编号）中的文字，并以 JSON 数组形式返回每张图片对应的纯文本字符串，仅输出 JSON 数组，不要额外说明："
        )}
    ]
    for path in image_paths:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}})

    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": parts}],
    )
    result = json.loads(resp.choices[0].message.content)
    return result

def batch_ocr_for_image(image_path: str,
                        ocr_model: str,
                        proofread_model: str,
                        chunk_height: int,
                        overlap: int,
                        min_overlap_chars: int) -> str:
    """
    Split the image into overlapping chunks and batch all chunks into one OCR request.
    """
    chunks = split_image(image_path, chunk_height, overlap)
    print(f"    Sending {len(chunks)} chunks in a single OCR request")
    texts = ocr_chunks_batch(chunks, ocr_model)
    merged = merge_texts(texts, min_overlap_chars)
    if proofread_model:
        merged = proofread_text(merged, proofread_model)
    return clean_content(merged)

def main():
    parser = argparse.ArgumentParser(description="Batch GPT-OCR via multi-chunk requests")
    parser.add_argument("--image-dir", required=True, help="directory of chapter PNGs")
    parser.add_argument("--output-dir", required=True, help="directory to save batch OCR text")
    parser.add_argument("--chunk-height", type=int, default=760)
    parser.add_argument("--overlap", type=int, default=20)
    parser.add_argument("--min-overlap-chars", type=int, default=20)
    parser.add_argument("--ocr-model", default="o4-mini")
    parser.add_argument("--proofread-model", default="")
    parser.add_argument("--openai-key", required=True)
    args = parser.parse_args()

    openai.api_key = args.openai_key
    os.makedirs(args.output_dir, exist_ok=True)

    pngs = sorted(f for f in os.listdir(args.image_dir) if f.endswith("_chapter.png"))
    for png in pngs:
        idx = png.split("_")[0]
        image_path = os.path.join(args.image_dir, png)
        print(f"[{idx}] OCR batch start...")
        text = batch_ocr_for_image(
            image_path,
            args.ocr_model,
            args.proofread_model,
            args.chunk_height,
            args.overlap,
            args.min_overlap_chars,
        )
        out_file = os.path.join(args.output_dir, f"{idx}_chapter_gptocr_batch.txt")
        with open(out_file, "w", encoding="utf-8") as fw:
            fw.write(text)
        print(f"[{idx}] saved to {out_file}")

if __name__ == "__main__":
    main()