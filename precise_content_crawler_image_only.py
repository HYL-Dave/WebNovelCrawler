#!/usr/bin/env python3
"""
Script for crawling chapter content images without OCR.
Reads URLs from a CSV and captures the content region screenshot for each URL.
Usage:
    python precise_content_crawler_image_only.py \
        --csv urls.csv \
        --rules content_rules.json \
        --output-dir precise_images \
        [--test]
"""
import argparse
import os
import csv
from precise_content_crawler import PreciseContentCrawler


def main():
    parser = argparse.ArgumentParser(
        description="Crawl chapter content images only"
    )
    parser.add_argument(
        "--csv", required=True, help="CSV file containing URLs list"
    )
    parser.add_argument(
        "--rules", help="content selector rules JSON file"
    )
    parser.add_argument(
        "--output-dir",
        default="precise_images",
        help="directory to save content images",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="only process first 3 URLs",
    )
    args = parser.parse_args()

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

        image_path = os.path.join(
            args.output_dir, f"{idx:04d}_chapter.png"
        )
        content_image.save(image_path)
        print(f"  saved image: {image_path}")


if __name__ == "__main__":
    main()