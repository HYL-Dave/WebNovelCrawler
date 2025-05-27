#!/usr/bin/env python3
"""
修復版綜合小說爬蟲
整合了 Firefox 驅動修復、OCR 檢測修復和進階解碼器
"""

import os
import sys
import time
import csv
import argparse
from urllib.parse import urljoin, urlparse

# 確保只使用 Firefox
FORCE_FIREFOX = True


def read_urls_from_csv(csv_file):
    """從 CSV 文件讀取 URL（修復版）"""
    urls = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        # 跳過標題行
        next(reader, None)

        for row in reader:
            # m1.csv 格式：第一列是章節名，第二列是 URL
            if len(row) > 1 and row[1].startswith('http'):
                url = row[1].strip('"')  # 移除可能的引號
                urls.append(url)

    return urls

class ComprehensiveCrawler:
    def __init__(self, use_ocr=False, delay=3, headless=True):
        self.use_ocr = use_ocr
        self.delay = delay
        self.headless = headless
        self.driver = None
        self.ocr_reader = None
        self.decoder = None

        # 檢查功能
        self.check_features()

        # 設置驅動
        if not self.setup_driver():
            print("無法設置瀏覽器驅動，退出")
            sys.exit(1)

    def check_features(self):
        """檢查可用功能"""
        print("功能狀態:")

        # 檢查 Firefox
        try:
            import subprocess
            result = subprocess.run(['firefox', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("  Firefox: ✓")
            else:
                print("  Firefox: ✗")
        except:
            print("  Firefox: ✗")

        # 檢查解碼器
        try:
            from advanced_decoder import AdvancedDecoder
            self.decoder = AdvancedDecoder()
            print("  解碼器: ✓")
        except:
            print("  解碼器: ✗ (使用基本解碼)")

        # 檢查 OCR
        if self.use_ocr:
            has_ocr, ocr_info = self.check_ocr_dependencies()
            if has_ocr:
                print("  OCR: ✓")
                self.ocr_reader = ocr_info
            else:
                print(f"  OCR: ✗ ({ocr_info})")
                self.use_ocr = False
        else:
            print("  OCR: 未啟用")

    def check_ocr_dependencies(self):
        """檢查 OCR 依賴"""
        try:
            import torch
            import torchvision
            import cv2
            import PIL
            import skimage
            import scipy
            import numpy
            import easyocr

            # 初始化 reader
            print("    正在初始化 OCR...")
            reader = easyocr.Reader(['ch_sim', 'en'], gpu=torch.cuda.is_available())
            return True, reader
        except ImportError as e:
            return False, f"缺少依賴: {str(e)}"
        except Exception as e:
            return False, f"初始化失敗: {str(e)}"

    def setup_driver(self):
        """設置 Firefox 驅動"""
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.service import Service
            from selenium.webdriver.firefox.options import Options

            print("正在設置 Firefox 驅動...")

            # 嘗試使用 webdriver-manager
            try:
                from webdriver_manager.firefox import GeckoDriverManager

                options = Options()
                if self.headless:
                    options.add_argument('--headless')

                # 反檢測設置
                options.set_preference("dom.webdriver.enabled", False)
                options.set_preference('useAutomationExtension', False)
                options.set_preference("general.useragent.override",
                                       "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")

                # 禁用圖片（加速）
                options.set_preference('permissions.default.image', 2)

                service = Service(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)
                print("✓ Firefox 驅動設置成功")
                return True

            except Exception as e:
                print(f"webdriver-manager 失敗: {e}")

                # 嘗試使用系統 geckodriver
                import subprocess
                result = subprocess.run(['which', 'geckodriver'], capture_output=True, text=True)
                if result.returncode == 0:
                    geckodriver_path = result.stdout.strip()

                    options = Options()
                    if self.headless:
                        options.add_argument('--headless')

                    service = Service(geckodriver_path)
                    self.driver = webdriver.Firefox(service=service, options=options)
                    print("✓ Firefox 驅動設置成功（使用系統 geckodriver）")
                    return True

                print("✗ 無法找到 geckodriver")
                print("請安裝：")
                print("1. uv pip install webdriver-manager")
                print("2. 或從 https://github.com/mozilla/geckodriver/releases 下載")
                return False

        except Exception as e:
            print(f"✗ Firefox 驅動設置失敗: {e}")
            return False

    def decode_content(self, content):
        """解碼內容"""
        if self.decoder:
            # 使用進階解碼器
            results = self.decoder.decode_all(content)

            # 找出包含最多中文的結果
            best_result = content
            best_chinese_count = len(self.decoder.extract_chinese(content))

            for method, decoded in results.items():
                chinese_count = len(self.decoder.extract_chinese(decoded))
                if chinese_count > best_chinese_count:
                    best_result = decoded
                    best_chinese_count = chinese_count

            return best_result
        else:
            # 基本解碼
            import html
            return html.unescape(content)

    def crawl_page(self, url):
        """爬取單個頁面"""
        try:
            print(f"訪問: {url}")
            self.driver.get(url)
            time.sleep(self.delay)

            # 獲取頁面源碼
            page_source = self.driver.page_source

            # 嘗試各種方法提取內容
            content = ""

            # 1. 查找常見的內容容器
            from selenium.webdriver.common.by import By
            content_selectors = [
                "div.content", "div#content", "div.chapter-content",
                "div.article-content", "div.text-content",
                "article", "main", "div.main-content"
            ]

            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        content = "\n".join([e.text for e in elements])
                        if content.strip():
                            break
                except:
                    continue

            # 2. 如果沒找到，獲取 body 內容
            if not content.strip():
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    content = body.text
                except:
                    content = ""

            # 3. 解碼內容
            decoded_content = self.decode_content(content)

            # 4. OCR 處理（如果啟用且內容太少）
            if self.use_ocr and len(decoded_content.strip()) < 100:
                print("  內容太少，嘗試 OCR...")
                # 截圖並 OCR
                screenshot = self.driver.get_screenshot_as_png()
                from PIL import Image
                import io
                import numpy as np

                img = Image.open(io.BytesIO(screenshot))
                img_array = np.array(img)

                ocr_results = self.ocr_reader.readtext(img_array)
                ocr_text = "\n".join([text for _, text, conf in ocr_results if conf > 0.5])

                if len(ocr_text) > len(decoded_content):
                    decoded_content = ocr_text

            return decoded_content

        except Exception as e:
            print(f"  錯誤: {e}")
            return ""

    def crawl_urls(self, urls, output_dir="output"):
        """爬取多個 URL"""
        os.makedirs(output_dir, exist_ok=True)

        for i, url in enumerate(urls, 1):
            print(f"\n爬取 {i}/{len(urls)}: {url}")

            content = self.crawl_page(url)

            if content:
                # 生成文件名
                filename = f"{i:04d}_{urlparse(url).path.replace('/', '_')}.txt"
                filepath = os.path.join(output_dir, filename)

                # 保存內容
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  已保存: {filepath} ({len(content)} 字)")
            else:
                print("  無內容")

    def __del__(self):
        """清理資源"""
        if self.driver:
            self.driver.quit()


def main():
    parser = argparse.ArgumentParser(description='修復版綜合小說爬蟲')
    parser.add_argument('--csv', required=True, help='包含 URL 的 CSV 文件')
    parser.add_argument('--use-ocr', action='store_true', help='使用 OCR')
    parser.add_argument('--delay', type=int, default=3, help='頁面間延遲（秒）')
    parser.add_argument('--headless', action='store_true', help='無頭模式')
    parser.add_argument('--output', default='output', help='輸出目錄')
    parser.add_argument('--test', action='store_true', help='測試模式（只爬取前5個）')

    args = parser.parse_args()

    # 讀取 CSV
    urls = read_urls_from_csv(args.csv)

    print(f"找到 {len(urls)} 個URL")

    if args.test:
        urls = urls[:5]
        print("測試模式：只爬取前5個URL")

    # 創建爬蟲
    crawler = ComprehensiveCrawler(
        use_ocr=args.use_ocr,
        delay=args.delay,
        headless=args.headless
    )

    # 開始爬取
    crawler.crawl_urls(urls, args.output)

    print("\n爬取完成！")


if __name__ == "__main__":
    main()