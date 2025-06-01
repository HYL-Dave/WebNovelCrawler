import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import json
from urllib.parse import urljoin, urlparse
import logging


class NovelScraper:
    def __init__(self, csv_file_path, output_dir="novel_chapters"):
        """
        初始化爬蟲

        Args:
            csv_file_path: CSV檔案路徑
            output_dir: 輸出目錄
        """
        self.csv_file_path = csv_file_path
        self.output_dir = output_dir
        self.session = requests.Session()

        # 更強化的請求標頭，模擬真實瀏覽器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-TW,zh-CN;q=0.9,zh;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Referer': 'https://czbooks.net/',
        })

        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        # 設置日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{output_dir}/scraping.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # 初始化session，訪問主頁獲取cookies
        self.init_session()

    def init_session(self):
        """初始化會話，先訪問主頁獲取必要的cookies"""
        try:
            self.logger.info("正在初始化會話...")
            response = self.session.get('https://czbooks.net/', timeout=10)
            if response.status_code == 200:
                self.logger.info("會話初始化成功")
            else:
                self.logger.warning(f"主頁訪問狀態碼: {response.status_code}")
        except Exception as e:
            self.logger.warning(f"初始化會話失敗: {e}")

    def get_with_retry(self, url, max_retries=3, base_delay=2):
        """帶重試機制的GET請求"""
        for attempt in range(max_retries):
            try:
                # 每次請求前更新referer
                self.session.headers.update({'Referer': 'https://czbooks.net/'})

                response = self.session.get(url, timeout=15)

                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    self.logger.warning(f"403錯誤，嘗試 {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        # 漸進式延遲
                        delay = base_delay * (2 ** attempt)
                        self.logger.info(f"等待 {delay} 秒後重試...")
                        time.sleep(delay)
                else:
                    response.raise_for_status()

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"請求失敗，{delay}秒後重試: {e}")
                    time.sleep(delay)
                else:
                    raise e

        return None

    def load_chapter_list(self):
        """載入章節列表"""
        try:
            df = pd.read_csv(self.csv_file_path, encoding='utf-8')
            # 清理空值
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

    def extract_content(self, html):
        """
        從HTML中提取小說內容
        需要根據實際網站結構調整選擇器
        """
        soup = BeautifulSoup(html, 'html.parser')

        # 常見的小說內容選擇器（需要根據實際網站調整）
        content_selectors = [
            '.chapter-content',
            '.content',
            '.novel-content',
            '#content',
            '.text-content',
            'div[class*="content"]',
            'div[id*="content"]'
        ]

        content = ""
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(strip=True)
                break

        # 如果找不到特定選擇器，嘗試查找包含最多文字的div
        if not content:
            divs = soup.find_all('div')
            if divs:
                content = max(divs, key=lambda div: len(div.get_text())).get_text(strip=True)

        return content

    def scrape_chapter(self, chapter_info):
        """爬取單個章節"""
        try:
            url = chapter_info['url']
            title = chapter_info['title']

            self.logger.info(f"正在爬取: {title}")

            # 使用新的重試機制
            response = self.get_with_retry(url)

            if response is None:
                return {
                    'title': title,
                    'url': url,
                    'content': '',
                    'status': 'failed_after_retries'
                }

            response.encoding = 'utf-8'
            content = self.extract_content(response.text)

            if content:
                self.logger.info(f"成功爬取: {title} (內容長度: {len(content)})")
                return {
                    'title': title,
                    'url': url,
                    'content': content,
                    'status': 'success'
                }
            else:
                self.logger.warning(f"無法提取內容: {title}")
                # 保存原始HTML用於調試
                debug_path = os.path.join(self.output_dir, f"debug_{title[:50]}.html")
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                return {
                    'title': title,
                    'url': url,
                    'content': '',
                    'status': 'no_content',
                    'debug_file': debug_path
                }

        except Exception as e:
            self.logger.error(f"爬取失敗 {chapter_info['title']}: {e}")
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
            # 清理檔案名稱中的非法字符
            safe_title = "".join(c for c in chapter_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{chapter_num:03d}_{safe_title}.txt"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"標題: {chapter_data['title']}\n")
                f.write(f"網址: {chapter_data['url']}\n")
                f.write(f"狀態: {chapter_data['status']}\n")
                f.write("-" * 50 + "\n\n")
                f.write(chapter_data['content'])

            return filepath
        except Exception as e:
            self.logger.error(f"保存章節失敗: {e}")
            return None

    def scrape_all(self, delay=3, start_chapter=1, end_chapter=None):
        """
        爬取所有章節

        Args:
            delay: 每次請求間的延遲秒數 (增加到3秒)
            start_chapter: 開始章節編號
            end_chapter: 結束章節編號 (None表示到最後)
        """
        chapters = self.load_chapter_list()
        if not chapters:
            self.logger.error("沒有找到有效章節")
            return

        # 選擇要爬取的範圍
        if end_chapter is None:
            end_chapter = len(chapters)

        selected_chapters = chapters[start_chapter - 1:end_chapter]
        self.logger.info(
            f"將爬取第 {start_chapter} 到第 {min(end_chapter, len(chapters))} 章，共 {len(selected_chapters)} 章")

        results = []
        failed_chapters = []

        for i, chapter_info in enumerate(selected_chapters, start_chapter):
            result = self.scrape_chapter(chapter_info)

            if result['status'] == 'success':
                # 保存章節
                filepath = self.save_chapter(result, i)
                if filepath:
                    result['saved_path'] = filepath
                results.append(result)
            else:
                failed_chapters.append(chapter_info)
                results.append(result)

            # 進度報告
            if i % 5 == 0:  # 每5章報告一次
                success_count = sum(1 for r in results if r['status'] == 'success')
                self.logger.info(f"進度: {i}/{end_chapter} ({success_count} 成功)")

            # 更長的延遲以避免被封IP
            if i < len(selected_chapters):  # 不是最後一章
                self.logger.info(f"等待 {delay} 秒...")
                time.sleep(delay)

        # 保存結果摘要
        self.save_summary(results, failed_chapters)

        success_count = sum(1 for r in results if r['status'] == 'success')
        self.logger.info(
            f"完成！總共 {len(selected_chapters)} 章，成功 {success_count} 章，失敗 {len(failed_chapters)} 章")

    def save_summary(self, results, failed_chapters):
        """保存爬取結果摘要"""
        summary = {
            'total_chapters': len(results),
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'failed': len(failed_chapters),
            'results': results,
            'failed_chapters': failed_chapters
        }

        summary_path = os.path.join(self.output_dir, 'scraping_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self.logger.info(f"結果摘要已保存至: {summary_path}")

    def create_ebook(self, output_filename="novel.txt"):
        """將所有章節合併成一個電子書檔案"""
        try:
            chapters = []
            for filename in sorted(os.listdir(self.output_dir)):
                if filename.endswith('.txt') and filename != output_filename:
                    filepath = os.path.join(self.output_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        chapters.append(f.read())

            ebook_path = os.path.join(self.output_dir, output_filename)
            with open(ebook_path, 'w', encoding='utf-8') as f:
                f.write('\n\n' + '=' * 80 + '\n\n'.join(chapters))

            self.logger.info(f"電子書已創建: {ebook_path}")
            return ebook_path
        except Exception as e:
            self.logger.error(f"創建電子書失敗: {e}")
            return None


# 使用範例
if __name__ == "__main__":
    # 創建爬蟲實例
    scraper = NovelScraper('czbooks_1.csv', 'novel_output')

    # 建議先測試前幾章，確認可以正常工作
    print("建議先測試前5章...")
    scraper.scrape_all(delay=3, start_chapter=1, end_chapter=5)

    # 如果測試成功，再爬取全部
    # scraper.scrape_all(delay=3)  # 增加延遲到3秒

    # 創建合併的電子書檔案
    scraper.create_ebook("complete_novel.txt")

    print("爬取完成！請檢查 'novel_output' 目錄中的結果。")