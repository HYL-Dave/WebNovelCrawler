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

class SeleniumNovelScraper:
    def __init__(self, csv_file_path, output_dir="novel_chapters"):
        """
        初始化Selenium爬蟲
        
        Args:
            csv_file_path: CSV檔案路徑
            output_dir: 輸出目錄
        """
        self.csv_file_path = csv_file_path
        self.output_dir = output_dir
        self.driver = None
        
        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)
        
        # 設置日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{output_dir}/selenium_scraping.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """設置Chrome瀏覽器驅動"""
        try:
            chrome_options = Options()
            
            # 設置瀏覽器選項
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 設置用戶代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 如果要在背景運行，取消下面這行的註釋
            # chrome_options.add_argument('--headless')
            
            # 初始化瀏覽器
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 隱藏自動化特徵
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("瀏覽器驅動設置成功")
            return True
            
        except Exception as e:
            self.logger.error(f"瀏覽器驅動設置失敗: {e}")
            return False

    def load_chapter_list(self):
        """載入章節列表"""
        try:
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
                "div[class*='text']"
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # 取最長的文本內容
                        for element in elements:
                            text = element.text.strip()
                            if len(text) > len(content):
                                content = text
                        if content:
                            break
                except:
                    continue
            
            # 如果還是找不到，嘗試所有div元素
            if not content:
                try:
                    divs = self.driver.find_elements(By.TAG_NAME, "div")
                    if divs:
                        content = max(divs, key=lambda div: len(div.text)).text.strip()
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
                self.logger.info(f"成功爬取: {title} (內容長度: {len(content)})")
                return {
                    'title': title,
                    'url': url,
                    'content': content,
                    'status': 'success'
                }
            else:
                self.logger.warning(f"內容太短或為空: {title}")
                # 保存頁面源碼用於調試
                debug_path = os.path.join(self.output_dir, f"debug_{title[:50].replace('/', '_')}.html")
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                return {
                    'title': title,
                    'url': url,
                    'content': content,
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

    def scrape_all(self, start_chapter=1, end_chapter=5):
        """
        爬取章節
        
        Args:
            start_chapter: 開始章節編號
            end_chapter: 結束章節編號
        """
        if not self.setup_driver():
            return
        
        try:
            chapters = self.load_chapter_list()
            if not chapters:
                self.logger.error("沒有找到有效章節")
                return
            
            selected_chapters = chapters[start_chapter-1:end_chapter]
            self.logger.info(f"將爬取第 {start_chapter} 到第 {end_chapter} 章，共 {len(selected_chapters)} 章")
            
            results = []
            
            for i, chapter_info in enumerate(selected_chapters, start_chapter):
                result = self.scrape_chapter(chapter_info)
                
                if result['status'] == 'success':
                    filepath = self.save_chapter(result, i)
                    if filepath:
                        result['saved_path'] = filepath
                
                results.append(result)
                
                # 進度報告
                if i % 3 == 0:
                    success_count = sum(1 for r in results if r['status'] == 'success')
                    self.logger.info(f"進度: {i}/{end_chapter} ({success_count} 成功)")
                
                # 人類化延遲
                if i < end_chapter:
                    self.human_like_delay(3, 6)
            
            # 統計結果
            success_count = sum(1 for r in results if r['status'] == 'success')
            self.logger.info(f"完成！總共 {len(selected_chapters)} 章，成功 {success_count} 章")
            
            return results
            
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("瀏覽器已關閉")

# 使用範例
if __name__ == "__main__":
    # 創建Selenium爬蟲實例
    scraper = SeleniumNovelScraper('czbooks_1.csv', 'selenium_output')
    
    # 測試前5章
    print("使用Selenium測試前5章...")
    scraper.scrape_all(start_chapter=1, end_chapter=5)
    
    print("爬取完成！請檢查 'selenium_output' 目錄中的結果。")
    print("如果成功，可以修改end_chapter參數來爬取更多章節。")
