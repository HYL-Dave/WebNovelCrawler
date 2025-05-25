#!/usr/bin/env python3
"""
純 HTTP 反向工程抓取小說內容 (initTxt API)
無需瀏覽器，通過解析 initTxt API 下載純文本並保存

用法:
  python3 smoke_http_only.py --csv m1.csv --output out_dir [--proxy-file proxies.txt] [--timeout 15] [--test]
"""

import argparse
import os

from http_utils import (
    load_proxies,
    extract_init_txt_url_http,
    fetch_initTxt_content_http,
)
from novel_crawler_stealth import read_urls_from_csv, clean_content


def main():
    parser = argparse.ArgumentParser(
        description="純 HTTP 抓取小說內容 (initTxt API)"
    )
    parser.add_argument('--csv', required=True, help='CSV 文件，包含 URL 列')
    parser.add_argument('--output', required=True, help='輸出目錄')
    parser.add_argument(
        '--proxy-file', default=None,
        help='可選，代理文件，每行一個代理，支持 http(s)://user:pass@ip:port'
    )
    parser.add_argument(
        '--timeout', type=int, default=15,
        help='HTTP 請求超時 (秒)'
    )
    parser.add_argument(
        '--test', action='store_true',
        help='測試模式，僅抓取第一條 URL'
    )
    args = parser.parse_args()

    proxies = None
    if args.proxy_file:
        proxies = load_proxies(args.proxy_file)
        if not proxies:
            print(f"警告: 未從 {args.proxy_file} 加載到任何代理，將不使用代理")

    urls = read_urls_from_csv(args.csv)
    if not urls:
        print("未讀取到任何 URL，請檢查 CSV 文件格式。")
        return
    if args.test:
        urls = urls[:1]

    os.makedirs(args.output, exist_ok=True)
    for idx, url in enumerate(urls, start=1):
        print(f"[{idx}/{len(urls)}] 處理: {url}")
        try:
            init_url = extract_init_txt_url_http(
                url, proxies=proxies, timeout=args.timeout
            )
            print(f"  initTxt URL: {init_url}")
            text = fetch_initTxt_content_http(
                init_url, referer=url, proxies=proxies, timeout=args.timeout
            )
            text = clean_content(text)
            out_file = os.path.join(args.output, f"{idx}.txt")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"  已保存: {out_file} (長度 {len(text)})")
        except Exception as e:
            print(f"  錯誤: {e}")


if __name__ == '__main__':
    main()