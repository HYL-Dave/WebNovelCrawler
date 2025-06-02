#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分頁章節爬蟲 - 專門處理Novel543等有分頁的小說網站
自動檢測並爬取所有分頁內容
"""

import argparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import os
import json
import logging
import random
import sys
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse


class PaginatedNovelScraper:
    def __init__(self, csv_file_path, output_dir="paginated_novels", headless=False):
        """
        初始化分頁小說爬蟲
        """
        self.csv_file_path = csv_file_path
        self.output_dir = output_dir
        self.headless = headless
        self.driver = None

        # 分頁檢測的正則表達式
        self.pagination_patterns = [
            r'\((\d+)/(\d+)\)',  # (1/2), (2/3) 等
            r'第(\d+)頁/共(\d+)頁',  # 第1頁/共3頁
            r'(\d+)/(\d+)頁',  # 1/3頁
        ]

        # 創建輸出目錄
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.setup_logging()

    def setup_logging(self):
        """設置日誌系統"""
        log_file = Path(self.output_dir) / 'paginated_scraping.log'

        logging.getLogger().handlers.clear()

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """設置Chrome瀏覽器驅動"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'--user-agent={user_agent}')

            if self.headless:
                chrome_options.add_argument('--headless')
                self.logger.info("運行在無頭模式")

            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                self.driver = webdriver.Chrome(options=chrome_options)

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("瀏覽器驅動設置成功")
            return True

        except Exception as e:
            self.logger.error(f"瀏覽器驅動設置失敗: {e}")
            return False

    def load_chapter_list(self):
        """載入章節列表"""
        try:
            if not Path(self.csv_file_path).exists():
                raise FileNotFoundError(f"找不到CSV檔案: {self.csv_file_path}")

            df = pd.read_csv(self.csv_file_path, encoding='utf-8')
            df = df.dropna()

            chapters = []
            for _, row in df.iterrows():
                title = row['tablescraper-selected-row']
                url = row['tablescraper-selected-row href']
                if title and url:
                    chapters.append({
                        'title': str(title).strip(),
                        'url': str(url).strip()
                    })

            self.logger.info(f"載入了 {len(chapters)} 個章節")
            return chapters
        except Exception as e:
            self.logger.error(f"載入CSV檔案失敗: {e}")
            return []

    def detect_pagination(self, title):
        """
        檢測標題中的分頁信息
        返回: (current_page, total_pages) 或 None
        """
        for pattern in self.pagination_patterns:
            match = re.search(pattern, title)
            if match:
                current_page = int(match.group(1))
                total_pages = int(match.group(2))
                self.logger.debug(f"檢測到分頁: {current_page}/{total_pages}")
                return current_page, total_pages
        return None

    def construct_page_url(self, base_url, page_number):
        """
        根據基礎URL和頁碼構造分頁URL
        例: https://www.novel543.com/0621496793/8096_1.html -> https://www.novel543.com/0621496793/8096_1_2.html
        """
        try:
            # 解析URL
            parsed = urlparse(base_url)
            path_parts = parsed.path.split('/')

            # 找到最後一個部分（檔案名）
            filename = path_parts[-1]

            # 處理不同的URL模式
            if '.html' in filename:
                # 移除.html後綴
                base_name = filename.replace('.html', '')

                # 構造新的檔案名
                new_filename = f"{base_name}_{page_number}.html"

                # 重新構造URL
                path_parts[-1] = new_filename
                new_path = '/'.join(path_parts)

                new_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    new_path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))

                self.logger.debug(f"構造分頁URL: {new_url}")
                return new_url
            else:
                self.logger.warning(f"無法處理的URL格式: {base_url}")
                return None

        except Exception as e:
            self.logger.error(f"構造分頁URL失敗: {e}")
            return None

    def extract_content_from_page(self):
        """從當前頁面提取內容"""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 針對Novel543的特定選擇器
            content_selectors = [
                "#content",
                ".content",
                ".novel-content",
                ".chapter-content",
                ".text-content",
                "div[class*='content']",
                "div[id*='content']",
                ".reading-content",
                "#chapterContent"
            ]

            content = ""
            title = ""

            # 先嘗試獲取標題
            title_selectors = ["h1", ".title", ".chapter-title", "h2", "h3"]
            for selector in title_selectors:
                try:
                    title_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if title_element:
                        title = title_element.text.strip()
                        break
                except:
                    continue

            # 獲取內容
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            text = element.text.strip()
                            if len(text) > len(content):
                                content = text
                        if content and len(content) > 100:  # 確保內容足夠長
                            break
                except:
                    continue

            # 如果還是找不到，使用通用方法
            if not content:
                try:
                    divs = self.driver.find_elements(By.TAG_NAME, "div")
                    if divs:
                        content = max(divs, key=lambda div: len(div.text)).text.strip()
                except:
                    pass

            return title, content

        except Exception as e:
            self.logger.error(f"提取頁面內容失敗: {e}")
            return "", ""

    def scrape_paginated_chapter(self, chapter_info):
        """爬取包含分頁的完整章節"""
        try:
            base_url = chapter_info['url']
            chapter_title = chapter_info['title']

            self.logger.info(f"🔍 開始分析章節: {chapter_title}")

            # 訪問第一頁
            self.driver.get(base_url)
            time.sleep(random.uniform(2, 4))

            # 獲取第一頁的標題和內容
            page_title, page_content = self.extract_content_from_page()

            if not page_content:
                self.logger.warning(f"❌ 無法獲取第一頁內容: {chapter_title}")
                return {
                    'title': chapter_title,
                    'url': base_url,
                    'content': '',
                    'status': 'no_content',
                    'pages': 0
                }

            # 檢測是否有分頁
            pagination_info = self.detect_pagination(page_title)

            if pagination_info is None:
                # 沒有分頁，直接返回
                self.logger.info(f"✅ 單頁章節: {chapter_title}")
                return {
                    'title': chapter_title,
                    'url': base_url,
                    'content': page_content,
                    'status': 'success',
                    'pages': 1
                }

            # 有分頁，獲取所有頁面
            current_page, total_pages = pagination_info
            self.logger.info(f"📄 檢測到分頁章節: {total_pages} 頁")

            all_content = [page_content]  # 第一頁內容
            failed_pages = []

            # 爬取剩餘頁面
            for page_num in range(2, total_pages + 1):
                try:
                    page_url = self.construct_page_url(base_url, page_num)
                    if not page_url:
                        failed_pages.append(page_num)
                        continue

                    self.logger.info(f"  📖 爬取第 {page_num}/{total_pages} 頁...")
                    self.driver.get(page_url)
                    time.sleep(random.uniform(1, 3))

                    _, content = self.extract_content_from_page()

                    if content:
                        all_content.append(content)
                        self.logger.debug(f"    ✅ 第{page_num}頁成功 (長度: {len(content)})")
                    else:
                        failed_pages.append(page_num)
                        self.logger.warning(f"    ❌ 第{page_num}頁內容為空")

                except Exception as e:
                    failed_pages.append(page_num)
                    self.logger.error(f"    ❌ 第{page_num}頁爬取失敗: {e}")

            # 合併所有內容
            combined_content = '\n\n'.join(all_content)

            success_pages = total_pages - len(failed_pages)
            status = 'success' if success_pages >= total_pages * 0.8 else 'partial_success'

            self.logger.info(f"🎉 章節完成: {success_pages}/{total_pages} 頁成功")

            return {
                'title': chapter_title,
                'url': base_url,
                'content': combined_content,
                'status': status,
                'pages': success_pages,
                'total_pages': total_pages,
                'failed_pages': failed_pages
            }

        except Exception as e:
            self.logger.error(f"❌ 章節爬取失敗 {chapter_info['title']}: {e}")
            return {
                'title': chapter_info['title'],
                'url': chapter_info['url'],
                'content': '',
                'status': 'error',
                'pages': 0,
                'error': str(e)
            }

    def save_chapter(self, chapter_data, chapter_num):
        """保存章節內容"""
        try:
            safe_title = "".join(
                c for c in chapter_data['title'] if c.isalnum() or c in (' ', '-', '_', '！', '？')).rstrip()
            filename = f"{chapter_num:03d}_{safe_title[:50]}.txt"
            filepath = Path(self.output_dir) / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"標題: {chapter_data['title']}\n")
                f.write(f"網址: {chapter_data['url']}\n")
                f.write(f"狀態: {chapter_data['status']}\n")
                f.write(f"章節編號: {chapter_num}\n")
                f.write(f"總頁數: {chapter_data.get('total_pages', 1)}\n")
                f.write(f"成功頁數: {chapter_data.get('pages', 1)}\n")
                if chapter_data.get('failed_pages'):
                    f.write(f"失敗頁數: {chapter_data['failed_pages']}\n")
                f.write("-" * 50 + "\n\n")
                f.write(chapter_data['content'])

            return str(filepath)
        except Exception as e:
            self.logger.error(f"保存章節失敗: {e}")
            return None

    def scrape_range(self, start_chapter=1, end_chapter=5, delay_range=(3, 6)):
        """爬取指定範圍的章節"""
        if not self.setup_driver():
            return []

        try:
            chapters = self.load_chapter_list()
            if not chapters:
                return []

            total_chapters = len(chapters)
            end_chapter = min(end_chapter, total_chapters)

            selected_chapters = chapters[start_chapter - 1:end_chapter]
            self.logger.info(f"🚀 開始爬取第 {start_chapter} 到第 {end_chapter} 章，共 {len(selected_chapters)} 章")

            results = []
            success_count = 0
            total_pages = 0

            for i, chapter_info in enumerate(selected_chapters, start_chapter):
                result = self.scrape_paginated_chapter(chapter_info)

                if result['status'] in ['success', 'partial_success']:
                    filepath = self.save_chapter(result, i)
                    if filepath:
                        result['saved_path'] = filepath
                        success_count += 1
                        total_pages += result.get('pages', 0)

                results.append(result)

                # 進度報告
                progress = f"[{i - start_chapter + 1}/{len(selected_chapters)}]"
                pages_info = f"(共爬取 {total_pages} 頁)"
                self.logger.info(f"{progress} 進度更新 - 成功: {success_count} {pages_info}")

                # 延遲
                if i < end_chapter:
                    delay = random.uniform(delay_range[0], delay_range[1])
                    time.sleep(delay)

            # 保存摘要
            self.save_summary(results, start_chapter, end_chapter, total_pages)

            failed_count = len(results) - success_count
            self.logger.info(f"🎉 爬取完成！成功: {success_count}, 失敗: {failed_count}, 總頁數: {total_pages}")

            return results

        finally:
            if self.driver:
                self.driver.quit()

    def save_summary(self, results, start_chapter, end_chapter, total_pages):
        """保存爬取結果摘要"""
        summary = {
            'range': f"{start_chapter}-{end_chapter}",
            'total_chapters': len(results),
            'successful_chapters': sum(1 for r in results if r['status'] in ['success', 'partial_success']),
            'total_pages_scraped': total_pages,
            'average_pages_per_chapter': total_pages / len(results) if results else 0,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'chapter_details': [
                {
                    'title': r['title'],
                    'status': r['status'],
                    'pages': r.get('pages', 0),
                    'total_pages': r.get('total_pages', 1)
                } for r in results
            ]
        }

        summary_path = Path(self.output_dir) / f'paginated_summary_{start_chapter}-{end_chapter}.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='分頁小說爬蟲')
    parser.add_argument('csv_file', help='CSV檔案路徑')
    parser.add_argument('--start', '-s', type=int, default=1, help='開始章節')
    parser.add_argument('--end', '-e', type=int, default=5, help='結束章節')
    parser.add_argument('--output', '-o', default='paginated_novels', help='輸出目錄')
    parser.add_argument('--delay', '-d', default='3-6', help='延遲時間範圍')
    parser.add_argument('--headless', action='store_true', help='無頭模式')
    parser.add_argument('--test', action='store_true', help='測試模式（前3章）')

    args = parser.parse_args()

    # 解析延遲範圍
    try:
        if '-' in args.delay:
            min_delay, max_delay = map(float, args.delay.split('-'))
            delay_range = (min_delay, max_delay)
        else:
            delay = float(args.delay)
            delay_range = (delay, delay + 2)
    except:
        delay_range = (3, 6)

    # 測試模式
    if args.test:
        start_chapter, end_chapter = 1, 3
        print("🧪 測試模式：爬取前3章")
    else:
        start_chapter, end_chapter = args.start, args.end

    print(f"🔍 分頁小說爬蟲啟動")
    print(f"📖 爬取範圍: 第{start_chapter}-{end_chapter}章")
    print(f"⏱️  延遲設置: {delay_range[0]}-{delay_range[1]}秒")

    scraper = PaginatedNovelScraper(
        csv_file_path=args.csv_file,
        output_dir=args.output,
        headless=args.headless
    )

    results = scraper.scrape_range(start_chapter, end_chapter, delay_range)

    if results:
        success_count = sum(1 for r in results if r['status'] in ['success', 'partial_success'])
        total_pages = sum(r.get('pages', 0) for r in results)
        print(f"\n🎉 爬取完成！")
        print(f"   成功章節: {success_count}/{len(results)}")
        print(f"   總頁數: {total_pages}")
        print(f"   輸出目錄: {args.output}")


if __name__ == "__main__":
    main()