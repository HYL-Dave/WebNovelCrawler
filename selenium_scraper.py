#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小說爬蟲 - Selenium版本 (支持命令行參數)
https://czbooks.net/
使用方法：
    python scraper.py input.csv --start 1 --end 10 --delay 3 --output novels
    python scraper.py input.csv --all --headless
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
from pathlib import Path


class SeleniumNovelScraper:
    def __init__(self, csv_file_path, output_dir="novel_chapters", headless=False, user_agent=None):
        """
        初始化Selenium爬蟲
        """
        self.csv_file_path = csv_file_path
        self.output_dir = output_dir
        self.headless = headless
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.driver = None

        # 創建輸出目錄
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 設置日誌
        self.setup_logging()

    def setup_logging(self):
        """設置日誌系統"""
        log_file = Path(self.output_dir) / 'scraping.log'

        # 清除之前的handlers
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

            # 基本設置
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 設置用戶代理
            chrome_options.add_argument(f'--user-agent={self.user_agent}')

            # 無頭模式
            if self.headless:
                chrome_options.add_argument('--headless')
                self.logger.info("運行在無頭模式")

            # 其他優化設置
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-default-apps')

            # 初始化瀏覽器
            try:
                # 嘗試使用webdriver-manager自動管理ChromeDriver
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                # 如果沒有webdriver-manager，使用系統PATH中的chromedriver
                self.driver = webdriver.Chrome(options=chrome_options)

            # 隱藏自動化特徵
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            self.logger.info("瀏覽器驅動設置成功")
            return True

        except Exception as e:
            self.logger.error(f"瀏覽器驅動設置失敗: {e}")
            self.logger.error("請確保已安裝Chrome瀏覽器和ChromeDriver")
            self.logger.error("或運行: pip install webdriver-manager")
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

    def human_like_delay(self, min_seconds=2, max_seconds=5):
        """模擬人類閱讀的延遲"""
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)

    def extract_content_selenium(self):
        """使用Selenium提取頁面內容"""
        try:
            # 等待頁面加載完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 嘗試多個可能的內容選擇器
            content_selectors = [
                "div[class*='content']",
                "div[id*='content']",
                ".chapter-content",
                ".novel-content",
                ".text-content",
                "article",
                ".main-text",
                "div[class*='text']",
                ".reading-content",
                "#chapterContent"
            ]

            content = ""
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            text = element.text.strip()
                            if len(text) > len(content):
                                content = text
                        if content:
                            self.logger.debug(f"使用選擇器找到內容: {selector}")
                            break
                except:
                    continue

            # 如果還是找不到，嘗試所有div元素
            if not content:
                try:
                    divs = self.driver.find_elements(By.TAG_NAME, "div")
                    if divs:
                        content = max(divs, key=lambda div: len(div.text)).text.strip()
                        self.logger.debug("使用最長div元素獲取內容")
                except:
                    pass

            return content

        except TimeoutException:
            self.logger.warning("頁面加載超時")
            return ""
        except Exception as e:
            self.logger.error(f"提取內容失敗: {e}")
            return ""

    def scrape_chapter(self, chapter_info):
        """爬取單個章節"""
        try:
            url = chapter_info['url']
            title = chapter_info['title']

            self.logger.info(f"正在爬取: {title}")

            # 訪問頁面
            self.driver.get(url)

            # 模擬人類行為 - 隨機滾動
            self.driver.execute_script("window.scrollTo(0, Math.floor(Math.random() * 1000));")

            # 等待一下讓頁面完全加載
            self.human_like_delay(1, 3)

            # 提取內容
            content = self.extract_content_selenium()

            if content and len(content) > 50:  # 確保內容不是太短
                self.logger.info(f"✓ 成功: {title} (內容長度: {len(content)})")
                return {
                    'title': title,
                    'url': url,
                    'content': content,
                    'status': 'success'
                }
            else:
                self.logger.warning(f"✗ 內容太短或為空: {title}")
                # 保存頁面源碼用於調試
                debug_filename = f"debug_{title[:30].replace('/', '_').replace('?', '').replace(':', '')}.html"
                debug_path = Path(self.output_dir) / debug_filename
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                return {
                    'title': title,
                    'url': url,
                    'content': content,
                    'status': 'no_content',
                    'debug_file': str(debug_path)
                }

        except Exception as e:
            self.logger.error(f"✗ 爬取失敗 {chapter_info['title']}: {e}")
            return {
                'title': chapter_info['title'],
                'url': chapter_info['url'],
                'content': '',
                'status': 'error',
                'error': str(e)
            }

    def save_chapter(self, chapter_data, chapter_num):
        """保存章節內容"""
        try:
            safe_title = "".join(
                c for c in chapter_data['title'] if c.isalnum() or c in (' ', '-', '_', '！', '？')).rstrip()
            filename = f"{chapter_num:03d}_{safe_title[:50]}.txt"  # 限制檔名長度
            filepath = Path(self.output_dir) / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"標題: {chapter_data['title']}\n")
                f.write(f"網址: {chapter_data['url']}\n")
                f.write(f"狀態: {chapter_data['status']}\n")
                f.write(f"章節編號: {chapter_num}\n")
                f.write("-" * 50 + "\n\n")
                f.write(chapter_data['content'])

            return str(filepath)
        except Exception as e:
            self.logger.error(f"保存章節失敗: {e}")
            return None

    def scrape_range(self, start_chapter=1, end_chapter=5, delay_range=(3, 6)):
        """
        爬取指定範圍的章節
        """
        if not self.setup_driver():
            return []

        try:
            chapters = self.load_chapter_list()
            if not chapters:
                self.logger.error("沒有找到有效章節")
                return []

            # 調整章節範圍
            total_chapters = len(chapters)
            end_chapter = min(end_chapter, total_chapters)

            if start_chapter > total_chapters:
                self.logger.error(f"開始章節 {start_chapter} 超過總章節數 {total_chapters}")
                return []

            selected_chapters = chapters[start_chapter - 1:end_chapter]
            self.logger.info(f"將爬取第 {start_chapter} 到第 {end_chapter} 章，共 {len(selected_chapters)} 章")

            results = []
            success_count = 0

            for i, chapter_info in enumerate(selected_chapters, start_chapter):
                result = self.scrape_chapter(chapter_info)

                if result['status'] == 'success':
                    filepath = self.save_chapter(result, i)
                    if filepath:
                        result['saved_path'] = filepath
                        success_count += 1

                results.append(result)

                # 進度報告
                progress = f"[{i - start_chapter + 1}/{len(selected_chapters)}]"
                self.logger.info(f"{progress} 進度更新 - 成功: {success_count}")

                # 人類化延遲
                if i < end_chapter:
                    self.human_like_delay(delay_range[0], delay_range[1])

            # 保存摘要
            self.save_summary(results, start_chapter, end_chapter)

            # 最終統計
            failed_count = len(results) - success_count
            self.logger.info(f"🎉 完成！成功: {success_count}, 失敗: {failed_count}")

            return results

        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("瀏覽器已關閉")

    def save_summary(self, results, start_chapter, end_chapter):
        """保存爬取結果摘要"""
        summary = {
            'range': f"{start_chapter}-{end_chapter}",
            'total_attempted': len(results),
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] != 'success'),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': results
        }

        summary_path = Path(self.output_dir) / f'summary_{start_chapter}-{end_chapter}.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self.logger.info(f"📊 結果摘要已保存: {summary_path}")


def parse_arguments():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(
        description='小說爬蟲 - Selenium版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  %(prog)s input.csv --start 1 --end 10
  %(prog)s input.csv --all --headless --delay 5
  %(prog)s input.csv -s 50 -e 100 -o my_novels --delay 3-8
        """
    )

    # 必需參數
    parser.add_argument('csv_file', help='CSV檔案路徑')

    # 章節範圍
    range_group = parser.add_mutually_exclusive_group(required=True)
    range_group.add_argument('--start', '-s', type=int, metavar='N',
                             help='開始章節編號')
    range_group.add_argument('--all', action='store_true',
                             help='爬取所有章節')

    parser.add_argument('--end', '-e', type=int, metavar='N',
                        help='結束章節編號 (與--start一起使用)')

    # 基本設置
    parser.add_argument('--output', '-o', default='novel_chapters',
                        help='輸出目錄 (預設: novel_chapters)')
    parser.add_argument('--delay', '-d', default='3-6',
                        help='延遲時間範圍，秒 (預設: 3-6)')

    # 瀏覽器設置
    parser.add_argument('--headless', action='store_true',
                        help='無頭模式運行（不顯示瀏覽器窗口）')
    parser.add_argument('--user-agent', '-ua',
                        help='自定義User-Agent')

    # 其他選項
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='顯示詳細日誌')
    parser.add_argument('--test', '-t', action='store_true',
                        help='測試模式：只爬取前3章')

    return parser.parse_args()


def parse_delay_range(delay_str):
    """解析延遲時間範圍"""
    try:
        if '-' in delay_str:
            min_delay, max_delay = map(float, delay_str.split('-'))
            return (min_delay, max_delay)
        else:
            delay = float(delay_str)
            return (delay, delay + 2)
    except ValueError:
        return (3, 6)  # 預設值


def main():
    """主函數"""
    args = parse_arguments()

    # 設置日誌級別
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 解析延遲範圍
    delay_range = parse_delay_range(args.delay)

    # 決定章節範圍
    if args.test:
        start_chapter, end_chapter = 1, 3
        print("🧪 測試模式：爬取前3章")
    elif args.all:
        start_chapter, end_chapter = 1, float('inf')
        print("📚 爬取所有章節")
    else:
        start_chapter = args.start
        end_chapter = args.end or args.start
        print(f"📖 爬取第 {start_chapter} 到第 {end_chapter} 章")

    # 創建爬蟲實例
    scraper = SeleniumNovelScraper(
        csv_file_path=args.csv_file,
        output_dir=args.output,
        headless=args.headless,
        user_agent=args.user_agent
    )

    # 如果是爬取所有章節，先載入章節列表確定總數
    if end_chapter == float('inf'):
        chapters = scraper.load_chapter_list()
        if chapters:
            end_chapter = len(chapters)
            print(f"📚 總共 {end_chapter} 章")
        else:
            print("❌ 無法載入章節列表")
            return

    # 開始爬取
    print(f"🚀 開始爬取... (延遲: {delay_range[0]}-{delay_range[1]}秒)")
    results = scraper.scrape_range(start_chapter, end_chapter, delay_range)

    # 顯示結果
    if results:
        success_count = sum(1 for r in results if r['status'] == 'success')
        total_count = len(results)
        print(f"\n🎉 爬取完成！")
        print(f"   成功: {success_count}/{total_count}")
        print(f"   輸出目錄: {args.output}")
    else:
        print("\n❌ 爬取失敗")


if __name__ == "__main__":
    main()