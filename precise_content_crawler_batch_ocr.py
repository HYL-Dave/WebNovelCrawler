#!/usr/bin/env python3
"""
End-to-end batch GPT-OCR: crawl chapter images and perform batch OCR per image.
Usage:
    python precise_content_crawler_batch_ocr.py \
        --csv urls.csv \
        --rules content_rules.json \
        --openai-key YOUR_KEY \
        --chunk-height 760 \
        --overlap 20 \
        --min-overlap-chars 20 \
        --ocr-model o4-mini \
        --proofread-model o4-mini \
        --output-dir precise_output_batch

This script reads URLs from a CSV, captures the content region screenshot for each URL,
splits each image into overlapping chunks, sends all chunks of the same image in a single
GPT-OCR request, merges and optionally proofreads the OCR results, then saves both the
raw chapter image and the final text.
"""
import argparse
import os
import csv
import json
import base64
import openai
from precise_content_crawler import (
    split_image,
    merge_texts,
    proofread_text,
    PreciseContentCrawler,
)


def clean_content(text: str) -> str:
    return PreciseContentCrawler._clean_content(None, text)


def ocr_chunks_batch(image_paths: list[str], model: str) -> list[str]:
    prompt = (
        f"请识别下面{len(image_paths)}个 chunk（按顺序编号），"
        "并严格按照顺序将每个 chunk 的识别文本作为 JSON 数组中的一个字符串返回。"
        "仅输出合法的 JSON 数组，不要多余注释或解释。"
    )
    parts = [{"type": "text", "text": prompt}]
    for path in image_paths:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
        })

    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": parts}],
    )
    return json.loads(resp.choices[0].message.content)


def batch_ocr_for_image(
    image_path: str,
    ocr_model: str,
    proofread_model: str,
    chunk_height: int,
    overlap: int,
    min_overlap_chars: int,
) -> str:
    chunks = split_image(image_path, chunk_height, overlap)
    print(f"  Sending {len(chunks)} chunks in a single OCR request")
    texts = ocr_chunks_batch(chunks, ocr_model)
    merged = merge_texts(texts, min_overlap_chars)
    if proofread_model:
        merged = proofread_text(merged, proofread_model)
    return clean_content(merged)


def main():
    parser = argparse.ArgumentParser(
        description="Batch GPT-OCR end-to-end: crawl images and OCR"
    )
    parser.add_argument(
        "--csv", required=True, help="CSV file containing URLs list"
    )
    parser.add_argument(
        "--rules", help="content selector rules JSON file"
    )
    parser.add_argument(
        "--output-dir",
        default="precise_output_batch",
        help="directory for saving images and OCR output",
    )
    parser.add_argument(
        "--chunk-height", type=int, default=760
    )
    parser.add_argument(
        "--overlap", type=int, default=20
    )
    parser.add_argument(
        "--min-overlap-chars", type=int, default=20
    )
    parser.add_argument(
        "--ocr-model", default="o4-mini"
    )
    parser.add_argument(
        "--proofread-model",
        default="",
        help="GPT proofreading model, empty to skip",
    )
    parser.add_argument(
        "--openai-key",
        required=True,
        help="OpenAI API key for GPT-OCR",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="only process first 3 URLs",
    )
    args = parser.parse_args()

    openai.api_key = args.openai_key
    urls = []
    with open(args.csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) > 1 and row[1].startswith("http"):
                urls.append(row[1].strip())
    if args.test:
        urls = urls[:3]

    crawler = PreciseContentCrawler(
        rules_file=args.rules,
        use_ocr=False,
        use_openai=False,
        openai_key=None,
    )
    os.makedirs(args.output_dir, exist_ok=True)

    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] {url}")
        _, content_image = crawler.capture_content_only(url)
        if not content_image:
            print(f"  failed to capture content image for {url}")
            continue

        base = os.path.join(args.output_dir, f"{idx:04d}_chapter")
        image_path = base + ".png"
        content_image.save(image_path)
        print(f"  saved image: {image_path}")

        text = batch_ocr_for_image(
            image_path,
            args.ocr_model,
            args.proofread_model,
            args.chunk_height,
            args.overlap,
            args.min_overlap_chars,
        )
        out_path = base + "_gptocr_batch.txt"
        with open(out_path, "w", encoding="utf-8") as fw:
            fw.write(text)
        print(f"  saved OCR result: {out_path}")


if __name__ == "__main__":
    main()