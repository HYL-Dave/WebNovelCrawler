#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分頁章節爬蟲 - 專門處理Novel543等有分頁的小說網站
自動檢測並爬取所有分頁內容，支持多種驗證機制

支持的驗證類型：
- reCAPTCHA (需要手動完成)
- 滑動驗證 (自動處理)
- 按鈕點擊驗證 (自動處理)
- CloudFlare驗證 (自動等待)

使用範例：
    # 基本使用
    python scraper.py input.csv --start 1 --end 10
    
    # 處理有驗證的網站
    python scraper.py input.csv --start 1 --end 10 --verify-timeout 60
    
    # 關閉自動驗證（遇到驗證問題時）
    python scraper.py input.csv --start 1 --end 10 --no-verify
    
    # 無頭模式（不推薦用於有驗證的網站）
    python scraper.py input.csv --start 1 --end 10 --headless --no-verify
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
    def __init__(self, csv_file_path, output_dir="paginated_novels", headless=False, auto_verify=True):
        """
        初始化分頁小說爬蟲
        """
        self.csv_file_path = csv_file_path
        self.output_dir = output_dir
        self.headless = headless
        self.auto_verify = auto_verify
        self.verification_timeout = 30  # 預設驗證超時時間
        self.driver = None
        
        # 分頁檢測的正則表達式
        self.pagination_patterns = [
            r'\((\d+)/(\d+)\)',  # (1/2), (2/3) 等
            r'第(\d+)頁/共(\d+)頁',  # 第1頁/共3頁
            r'(\d+)/(\d+)頁',    # 1/3頁
        ]
        
        # 常見驗證元素的選擇器
        self.verification_selectors = [
            # reCAPTCHA
            'iframe[src*="recaptcha"]',
            '.recaptcha-checkbox',
            '#recaptcha-anchor',
            
            # 常見的"我不是機器人"按鈕
            'button:contains("我不是機器人")',
            'button:contains("I\'m not a robot")',
            'input[value*="我不是機器人"]',
            'input[value*="not a robot"]',
            
            # 通用驗證按鈕
            'button[class*="verify"]',
            'button[id*="verify"]',
            '.verify-button',
            '#verify-btn',
            
            # 點擊確認按鈕
            'button:contains("確認")',
            'button:contains("確定")',
            'button:contains("继续")',
            'button:contains("Continue")',
            'button:contains("Submit")',
            
            # 滑動驗證
            '.slider-verify',
            '.slide-verify',
            '[class*="slider"]',
            
            # CloudFlare驗證
            '#challenge-stage',
            '.challenge-form',
            
            # 自定義驗證
            'button[onclick*="verify"]',
            'div[class*="human-verification"]',
            '.human-check',
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

    def wait_for_page_load(self, timeout=10):
        """等待頁面完全加載"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            self.logger.warning("頁面加載超時")
            return False

    def detect_verification_elements(self):
        """檢測頁面中的驗證元素"""
        verification_elements = []
        
        for selector in self.verification_selectors:
            try:
                # 處理包含文本的選擇器
                if ':contains(' in selector:
                    # 提取文本內容
                    text = selector.split(':contains("')[1].split('")')[0]
                    # 使用XPath查找包含特定文本的元素
                    xpath = f"//*[contains(text(), '{text}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        verification_elements.append({
                            'element': element,
                            'selector': selector,
                            'type': self.classify_verification_type(selector)
                        })
                        
            except Exception as e:
                self.logger.debug(f"檢測驗證元素失敗 {selector}: {e}")
                continue
        
        return verification_elements

    def classify_verification_type(self, selector):
        """分類驗證類型"""
        selector_lower = selector.lower()
        
        if 'recaptcha' in selector_lower:
            return 'recaptcha'
        elif 'slider' in selector_lower or 'slide' in selector_lower:
            return 'slider'
        elif 'challenge' in selector_lower:
            return 'cloudflare'
        elif any(word in selector_lower for word in ['verify', 'human', 'robot']):
            return 'human_verification'
        else:
            return 'button_click'

    def handle_verification(self, max_attempts=3, manual_timeout=None):
        """
        處理頁面驗證
        
        Args:
            max_attempts: 最大嘗試次數
            manual_timeout: 手動驗證超時時間（秒），如果為None則使用self.verification_timeout
        """
        if not self.auto_verify:
            return True
        
        if manual_timeout is None:
            manual_timeout = self.verification_timeout
            
        for attempt in range(max_attempts):
            try:
                # 等待頁面穩定
                time.sleep(2)
                
                # 檢測驗證元素
                verification_elements = self.detect_verification_elements()
                
                if not verification_elements:
                    self.logger.debug("未檢測到驗證元素")
                    return True
                
                self.logger.info(f"🔐 檢測到 {len(verification_elements)} 個驗證元素")
                
                for i, ver_element in enumerate(verification_elements):
                    element = ver_element['element']
                    ver_type = ver_element['type']
                    selector = ver_element['selector']
                    
                    self.logger.info(f"  處理驗證 {i+1}: {ver_type}")
                    
                    if ver_type == 'recaptcha':
                        success = self.handle_recaptcha(element, manual_timeout)
                    elif ver_type == 'slider':
                        success = self.handle_slider_verification(element)
                    elif ver_type == 'cloudflare':
                        success = self.handle_cloudflare(manual_timeout)
                    else:
                        success = self.handle_button_click(element)
                    
                    if success:
                        self.logger.info(f"  ✅ 驗證成功: {ver_type}")
                        # 等待驗證後的頁面變化
                        time.sleep(3)
                        return True
                    else:
                        self.logger.warning(f"  ❌ 驗證失敗: {ver_type}")
                
                # 如果所有驗證都失敗，嘗試下一輪
                if attempt < max_attempts - 1:
                    self.logger.info(f"嘗試 {attempt + 1}/{max_attempts} 失敗，重試...")
                    time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"處理驗證時出錯: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)
        
        self.logger.warning("所有驗證嘗試都失敗了")
        return False

    def handle_button_click(self, element):
        """處理簡單的按鈕點擊驗證"""
        try:
            # 滾動到元素位置
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)
            
            # 點擊元素
            element.click()
            time.sleep(2)
            
            return True
        except Exception as e:
            self.logger.error(f"按鈕點擊失敗: {e}")
            return False

    def handle_recaptcha(self, element, timeout=30):
        """處理reCAPTCHA驗證"""
        try:
            self.logger.info("🤖 檢測到reCAPTCHA，需要手動完成驗證")
            
            if self.headless:
                self.logger.warning("無頭模式下無法處理reCAPTCHA，建議關閉headless模式")
                return False
            
            # 點擊reCAPTCHA複選框
            try:
                element.click()
                time.sleep(2)
            except:
                pass
            
            # 等待用戶手動完成驗證
            self.logger.info(f"⏰ 請在 {timeout} 秒內完成reCAPTCHA驗證...")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # 檢查驗證是否完成
                    if not self.detect_verification_elements():
                        self.logger.info("✅ reCAPTCHA驗證完成")
                        return True
                    time.sleep(2)
                except:
                    pass
            
            self.logger.warning("reCAPTCHA驗證超時")
            return False
            
        except Exception as e:
            self.logger.error(f"處理reCAPTCHA失敗: {e}")
            return False

    def handle_slider_verification(self, element):
        """處理滑動驗證"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            
            self.logger.info("🎯 處理滑動驗證")
            
            # 獲取滑塊的尺寸和位置
            slider_size = element.size
            slider_location = element.location
            
            # 創建動作鏈
            actions = ActionChains(self.driver)
            
            # 點擊並拖拽滑塊
            actions.click_and_hold(element)
            
            # 模擬人類滑動軌跡
            for i in range(10):
                x_offset = (slider_size['width'] * 0.8) / 10
                actions.move_by_offset(x_offset, random.uniform(-2, 2))
                time.sleep(random.uniform(0.1, 0.3))
            
            actions.release().perform()
            time.sleep(3)
            
            return True
            
        except Exception as e:
            self.logger.error(f"滑動驗證失敗: {e}")
            return False

    def handle_cloudflare(self, timeout=30):
        """處理CloudFlare驗證"""
        try:
            self.logger.info("☁️ 檢測到CloudFlare驗證，等待自動完成...")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # 檢查是否還在驗證頁面
                    current_url = self.driver.current_url
                    if 'challenge' not in current_url.lower():
                        self.logger.info("✅ CloudFlare驗證完成")
                        return True
                    time.sleep(2)
                except:
                    pass
            
            self.logger.warning("CloudFlare驗證超時")
            return False
            
        except Exception as e:
            self.logger.error(f"處理CloudFlare失敗: {e}")
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
            
            # 等待頁面加載
            if not self.wait_for_page_load():
                self.logger.warning("頁面加載可能不完整")
            
            # 處理驗證（如果有的話）
            if not self.handle_verification():
                self.logger.warning(f"⚠️ 驗證處理失敗，嘗試繼續: {chapter_title}")
            
            # 額外等待確保頁面穩定
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
                    
                    # 等待頁面加載
                    self.wait_for_page_load(timeout=5)
                    
                    # 處理可能的驗證
                    self.handle_verification(max_attempts=1, manual_timeout=min(10, self.verification_timeout))
                    
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
            safe_title = "".join(c for c in chapter_data['title'] if c.isalnum() or c in (' ', '-', '_', '！', '？')).rstrip()
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
            
            selected_chapters = chapters[start_chapter-1:end_chapter]
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
                progress = f"[{i-start_chapter+1}/{len(selected_chapters)}]"
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
    parser = argparse.ArgumentParser(description='分頁小說爬蟲 - 支持驗證處理')
    parser.add_argument('csv_file', help='CSV檔案路徑')
    parser.add_argument('--start', '-s', type=int, default=1, help='開始章節')
    parser.add_argument('--end', '-e', type=int, default=5, help='結束章節')
    parser.add_argument('--output', '-o', default='paginated_novels', help='輸出目錄')
    parser.add_argument('--delay', '-d', default='3-6', help='延遲時間範圍')
    parser.add_argument('--headless', action='store_true', help='無頭模式')
    parser.add_argument('--test', action='store_true', help='測試模式（前3章）')
    parser.add_argument('--no-verify', action='store_true', help='關閉自動驗證處理')
    parser.add_argument('--verify-timeout', type=int, default=30, help='手動驗證超時時間（秒）')
    parser.add_argument('--custom-verify', help='自定義驗證元素選擇器（CSS選擇器）')
    
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
    print(f"🔐 自動驗證: {'關閉' if args.no_verify else '開啟'}")
    if not args.no_verify:
        print(f"⏰ 驗證超時: {args.verify_timeout}秒")
    
    scraper = PaginatedNovelScraper(
        csv_file_path=args.csv_file,
        output_dir=args.output,
        headless=args.headless,
        auto_verify=not args.no_verify
    )
    
    # 設置驗證超時時間
    scraper.verification_timeout = args.verify_timeout
    
    # 添加自定義驗證選擇器
    if args.custom_verify:
        scraper.verification_selectors.append(args.custom_verify)
        print(f"🔧 添加自定義驗證選擇器: {args.custom_verify}")
    
    results = scraper.scrape_range(start_chapter, end_chapter, delay_range)
    
    if results:
        success_count = sum(1 for r in results if r['status'] in ['success', 'partial_success'])
        total_pages = sum(r.get('pages', 0) for r in results)
        print(f"\n🎉 爬取完成！")
        print(f"   成功章節: {success_count}/{len(results)}")
        print(f"   總頁數: {total_pages}")
        print(f"   輸出目錄: {args.output}")
        
        # 如果有驗證相關的問題，給出建議
        if success_count < len(results) * 0.8:
            print(f"\n💡 成功率較低，建議：")
            print(f"   - 如果遇到驗證問題，可以關閉無頭模式: --no-headless")
            print(f"   - 如果驗證超時，可以增加超時時間: --verify-timeout 60")
            print(f"   - 如果驗證處理有問題，可以關閉自動驗證: --no-verify")

if __name__ == "__main__":
    main()
