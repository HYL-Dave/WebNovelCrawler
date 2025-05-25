#!/usr/bin/env python3
"""
冒煙測試腳本：對比 stealth 與 advanced stealth 版在移動端的抓取效果
"""
import argparse

from novel_crawler_stealth import setup_stealth_driver, crawl_novel_content_stealth
from novel_crawler_advanced_stealth import StealthCrawler, clean_content as adv_clean_content


def main():
    parser = argparse.ArgumentParser(description="移動端抓取冒煙測試")
    parser.add_argument('--url', required=True, help="移動端章節 URL")
    parser.add_argument('--timeout', type=int, default=30, help="最大重試秒數")
    args = parser.parse_args()

    print("== Stealth 版測試 ==")
    driver = setup_stealth_driver(headless=True)
    try:
        content1 = crawl_novel_content_stealth(driver, args.url, max_retries=1)
        preview1 = content1[:200] if content1 else ''
        print(preview1)
    finally:
        driver.quit()

    print("\n== Advanced Stealth 版測試 ==")
    crawler = StealthCrawler(headless=True)
    try:
        if crawler.get_with_retry(args.url, max_retries=1):
            content2 = crawler.extract_novel_content()
            content2 = adv_clean_content(content2) if content2 else ''
            print(content2[:200])
        else:
            print("訪問失敗")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()