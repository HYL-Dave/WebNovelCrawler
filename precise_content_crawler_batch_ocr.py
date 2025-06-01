#!/usr/bin/env python3
"""
End-to-end batch GPT-OCR: crawl chapter images and perform batch OCR per image.
Usage:
    python precise_content_crawler_batch_ocr.py \
        --csv m1.csv m2.csv [more.csv ...] \
        --rules content_rules.json \
        --openai-key YOUR_KEY \
        --workers 4 \
        --chunk-height 760 \
        --overlap 20 \
        --bottom-skip 60 \
        --min-overlap-chars 20 \
        --ocr-model o4-mini \
        --proofread-model o4-mini \
        --output-dir precise_output_batch

    This script reads URLs from one or more CSV files (creating a subdirectory per CSV),
    captures the content region screenshot for each URL, splits each image into overlapping
    chunks (excluding bottom-skip pixels), sends all chunks of the same image in a single
    GPT-OCR request, merges and optionally proofreads the OCR results, then saves both
    the raw chapter image and the final text. It can run jobs in parallel using multiple
    worker threads.

單圖補救模式:
    python precise_content_crawler_batch_ocr.py --image precise_output_batch_o4_mini_v4/m8/0016_chapter.png \
       --ocr-model o4-mini --proofread-model o4-mini --openai-key sk-...
即可在同目錄生成 0016_chapter_gptocr_batch.txt，用於事後補 OCR 文本。
"""
import argparse
import os
import csv
import json
import base64
import re
import openai
from precise_content_crawler import (
    split_image,
    merge_texts,
    proofread_text,
    PreciseContentCrawler,
)
import concurrent.futures
import sys


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

    # add a system-level instruction to enforce strict JSON-array-only output
    system_msg = (
        "你是一个严格的 OCR 助手，接收多张图片，务必将识别结果按顺序返回 JSON 数组，"
        "禁止输出任何多余内容或注释。"
    )
    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": parts},
        ],
    )
    raw = resp.choices[0].message.content

    # ---------------- Robust JSON extraction ----------------
    # GPT 有时会在 JSON 数组前后包裹 ```json 代碼塊、額外提示或重複輸出，
    # 導致 json.loads() 報 Extra data。這裡使用兩步策略：
    # 1. 嘗試透過 JSONDecoder().raw_decode 解析首個合法 JSON 值。
    # 2. 若失敗，再回退到正則提取首個 "[ ... ]" 子串（非貪婪，避免抓到後續雜訊）。

    cleaned = raw.strip()

    # 去除 ```json ... ``` 代碼塊包裹
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"```\s*$", "", cleaned)

    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(cleaned)
    except json.JSONDecodeError:
        # 非貪婪匹配首個 JSON array
        m = re.search(r"\[.*?\]", cleaned, flags=re.S)
        if not m:
            raise ValueError(f"无法从 OCR 输出中解析 JSON 数组：{raw!r}")
        data = json.loads(m.group(0))
    # 验证返回长度与输入 chunk 数一致
    if not isinstance(data, list) or len(data) != len(image_paths):
        raise ValueError(
            f"OCR 结果数与 chunk 数不符，预期 {len(image_paths)}，实际 {len(data)}：{data!r}"
        )
    return data


def batch_ocr_for_image(
    image_path: str,
    ocr_model: str,
    proofread_model: str,
    chunk_height: int,
    overlap: int,
    min_overlap_chars: int,
    bottom_skip: int,
) -> str:
    chunks = split_image(image_path, chunk_height, overlap, bottom_skip)
    print(f"  Sending {len(chunks)} chunks in a single OCR request")
    texts = ocr_chunks_batch(chunks, ocr_model)
    merged = merge_texts(texts, min_overlap_chars)
    if proofread_model:
        merged = proofread_text(merged, proofread_model)
    return clean_content(merged)

def process_job(job, rules_file, ocr_model, proofread_model,
                chunk_height, overlap, min_overlap_chars,
                bottom_skip, openai_key):
    sub_out, idx, url = job
    openai.api_key = openai_key
    crawler = PreciseContentCrawler(
        rules_file=rules_file, use_ocr=False, use_openai=False, openai_key=None
    )
    name = os.path.basename(sub_out)
    print(f"[{name}|{idx}] {url}")
    _, content_image = crawler.capture_content_only(url)
    if not content_image:
        print(f"  failed to capture content image for {url}")
        return

    base = os.path.join(sub_out, f"{idx:04d}_chapter")
    image_path = base + ".png"
    content_image.save(image_path)
    print(f"  saved image: {image_path}")

    text = batch_ocr_for_image(
        image_path, ocr_model, proofread_model,
        chunk_height, overlap, min_overlap_chars,
        bottom_skip
    )
    out_path = base + "_gptocr_batch.txt"
    with open(out_path, "w", encoding="utf-8") as fw:
        fw.write(text)
    print(f"  saved OCR result: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch GPT-OCR end-to-end: crawl images and OCR"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--csv", nargs="+",
        help="CSV file(s) containing URLs list(s)"
    )
    group.add_argument(
        "--image",
        help="Process a single chapter image (PNG) that has already been captured"
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
        "--overlap", type=int, default=20,
        help="overlap pixels between chunks"
    )
    parser.add_argument(
        "--bottom-skip", type=int, default=60,
        help="pixels to skip at bottom of image before chunking (default: 60)"
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
        "--workers", type=int, default=1,
        help="number of parallel worker processes (default: 1)",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="only process first 3 URLs per CSV",
    )
    args = parser.parse_args()

    openai.api_key = args.openai_key

    # ------------------------------------------------------------
    # Mode 1: single image OCR
    # ------------------------------------------------------------
    if args.image:
        img_path = args.image
        if not os.path.isfile(img_path):
            print(f"Image not found: {img_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Processing single image: {img_path}")

        text = batch_ocr_for_image(
            img_path,
            args.ocr_model,
            args.proofread_model,
            args.chunk_height,
            args.overlap,
            args.min_overlap_chars,
            args.bottom_skip,
        )

        # default output file: same base name + _gptocr_batch.txt
        out_path = os.path.splitext(img_path)[0] + "_gptocr_batch.txt"
        with open(out_path, "w", encoding="utf-8") as fw:
            fw.write(text)
        print(f"✓ OCR result saved to {out_path}")
        return

    # ------------------------------------------------------------
    # Mode 2: batch crawl & OCR via CSV
    # ------------------------------------------------------------
    # Build jobs: for each CSV file, read URLs and prepare subdirectory
    jobs = []
    for csv_path in args.csv or []:
        name = os.path.splitext(os.path.basename(csv_path))[0]
        sub_out = os.path.join(args.output_dir, name)
        os.makedirs(sub_out, exist_ok=True)

        urls = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) > 1 and row[1].startswith("http"):
                    urls.append(row[1].strip())
        if args.test:
            urls = urls[:3]

        for idx, url in enumerate(urls, 1):
            jobs.append((sub_out, idx, url))

    # Process jobs, optionally in parallel
    if args.workers > 1:
        print(f"Starting processing with {args.workers} workers...")
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    process_job, job, args.rules,
                    args.ocr_model, args.proofread_model,
                    args.chunk_height, args.overlap,
                    args.min_overlap_chars, args.bottom_skip,
                    args.openai_key
                ): job
                for job in jobs
            }
            for future in concurrent.futures.as_completed(futures):
                job = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing {job}: {e}", file=sys.stderr)
    else:
        for job in jobs:
            try:
                process_job(
                    job, args.rules, args.ocr_model,
                    args.proofread_model, args.chunk_height,
                    args.overlap, args.min_overlap_chars,
                    args.bottom_skip, args.openai_key
                )
            except Exception as e:
                print(f"Error processing {job}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()