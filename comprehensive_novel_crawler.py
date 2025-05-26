"""
綜合版小說爬蟲
結合Firefox、改進解碼器、OCR等多種技術
"""

import csv
import os
import re
import time
import json
import argparse
import random
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.firefox import GeckoDriverManager

# 導入我們的模塊
try:
    from improved_decoder import ImprovedDecoder

    DECODER_AVAILABLE = True
except ImportError:
    ImprovedDecoder = None
    DECODER_AVAILABLE = False

try:
    from ocr_image_extractor import OCRImageExtractor, enhanced_content_extraction

    OCR_AVAILABLE = True
except ImportError:
    OCRImageExtractor = None
    enhanced_content_extraction = None
    OCR_AVAILABLE = False


class ComprehensiveNovelCrawler:
    def __init__(self, headless=False, proxy=None, use_ocr=False, use_decoder=True):
        self.headless = headless
        self.proxy = proxy
        self.use_ocr = use_ocr and OCR_AVAILABLE
        self.use_decoder = use_decoder and DECODER_AVAILABLE
        self.driver = None
        self.decoder = ImprovedDecoder() if DECODER_AVAILABLE else None
        self.ocr_extractor = OCRImageExtractor() if OCR_AVAILABLE and use_ocr else None

        print(f"功能狀態:")
        print(f"  Firefox: ✓")
        print(f"  解碼器: {'✓' if self.use_decoder else '✗'}")
        print(f"  OCR: {'✓' if self.use_ocr else '✗'}")

    def setup_driver(self):
        """設置Firefox驅動程序"""
        firefox_options = Options()

        if self.headless:
            firefox_options.add_argument('--headless')

        # 反檢測設置
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference('useAutomationExtension', False)
        firefox_options.set_preference("general.useragent.override",
                                       "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")

        # 優化設置
        firefox_options.set_preference('permissions.default.image', 1)  # 允許圖片加載（OCR需要）
        firefox_options.set_preference('javascript.enabled', True)  # 啟用JavaScript（解密需要）

        # 設置代理
        if self.proxy:
            self.setup_proxy(firefox_options)

        try:
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            self.driver.set_window_size(1920, 1080)

            # 移除webdriver屬性
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print("✓ Firefox驅動程序設置成功")
            return self.driver

        except Exception as e:
            print(f"✗ Firefox驅動程序設置失敗: {e}")
            return None

    def setup_proxy(self, firefox_options):
        """設置代理"""
        try:
            proxy_url = self.proxy.replace('http://', '').replace('https://', '')

            if '@' in proxy_url:
                # 有認證的代理
                auth, host_port = proxy_url.split('@')
                host, port = host_port.split(':')
            else:
                # 無認證代理
                host, port = proxy_url.split(':')

            firefox_options.set_preference('network.proxy.type', 1)
            firefox_options.set_preference('network.proxy.http', host)
            firefox_options.set_preference('network.proxy.http_port', int(port))
            firefox_options.set_preference('network.proxy.ssl', host)
            firefox_options.set_preference('network.proxy.ssl_port', int(port))

            print(f"設置代理: {host}:{port}")

        except Exception as e:
            print(f"代理設置失敗: {e}")

    def extract_content_comprehensive(self, url):
        """綜合內容提取方法"""
        try:
            print(f"訪問: {url}")
            self.driver.get(url)

            # 等待頁面加載
            time.sleep(5)

            # 模擬人類行為
            self.simulate_human_behavior()

            content_methods = [
                self.extract_via_javascript_decoding,
                self.extract_via_direct_text,
                self.extract_via_ocr,
                self.extract_via_raw_source
            ]

            for method in content_methods:
                try:
                    print(f"嘗試方法: {method.__name__}")
                    content = method()

                    if content and len(content.strip()) > 100:
                        print(f"✓ {method.__name__} 成功，內容長度: {len(content)}")
                        return self.clean_and_format_content(content)
                    else:
                        print(f"✗ {method.__name__} 失敗或內容太短")

                except Exception as e:
                    print(f"✗ {method.__name__} 出錯: {e}")

            print("✗ 所有方法都失敗了")
            self.save_debug_info(url)
            return None

        except Exception as e:
            print(f"✗ 綜合提取失敗: {e}")
            return None

    def extract_via_javascript_decoding(self):
        """通過JavaScript解密提取內容"""
        print("  嘗試JavaScript解密...")

        # 等待JavaScript執行
        time.sleep(10)

        # 檢查是否有txtContent
        try:
            element = self.driver.find_element(By.ID, "txtContent")
            content = element.text

            if content and len(content) > 100:
                return content
        except:
            pass

        # 檢查頁面源碼中的加密內容
        page_source = self.driver.page_source

        # 查找_txt_call函數調用
        txt_call_match = re.search(r'_txt_call\(({.*?})\)', page_source, re.DOTALL)
        if txt_call_match and self.use_decoder:
            try:
                print("  發現加密內容，嘗試解碼...")
                json_str = txt_call_match.group(1)
                # 保存到臨時文件並解碼
                temp_file = f'temp_decode_{int(time.time())}.txt'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(f'_txt_call({json_str})')

                decoded_content = self.decoder.decode_file(temp_file)

                # 清理臨時文件
                try:
                    os.remove(temp_file)
                except:
                    pass

                if decoded_content:
                    return decoded_content

            except Exception as e:
                print(f"  解碼失敗: {e}")

        return None

    def extract_via_direct_text(self):
        """直接文字提取"""
        print("  嘗試直接文字提取...")

        selectors = [
            '#txtContent', '#content', '#chaptercontent', '#chapter-content',
            '#BookText', '.readcontent', '.read-content', '.novel-content',
            '.content', 'article', 'main'
        ]

        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text
                if text and len(text) > 100:
                    return text
            except:
                continue

        # 嘗試最大文本塊
        return self.find_largest_text_block()

    def extract_via_ocr(self):
        """OCR文字提取"""
        if not self.use_ocr or not self.ocr_extractor:
            return None

        print("  嘗試OCR文字提取...")

        try:
            # 使用OCR提取圖片文字
            image_text = self.ocr_extractor.extract_text_from_page_images(self.driver)
            canvas_text = self.ocr_extractor.extract_canvas_text(self.driver)

            ocr_content = []
            if image_text:
                ocr_content.append(image_text)
            if canvas_text:
                ocr_content.append(canvas_text)

            if ocr_content:
                return '\n'.join(ocr_content)

        except Exception as e:
            print(f"  OCR失敗: {e}")

        return None

    def extract_via_raw_source(self):
        """從原始源碼提取"""
        print("  嘗試原始源碼分析...")

        page_source = self.driver.page_source

        # 查找可能的內容模式
        patterns = [
            r'<div[^>]*id[^>]*txtContent[^>]*>(.*?)</div>',
            r'<div[^>]*class[^>]*content[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, page_source, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # 移除HTML標籤
                text = re.sub(r'<[^>]+>', '', match)
                text = text.strip()
                if len(text) > 100:
                    return text

        return None

    def find_largest_text_block(self):
        """查找最大的文本塊"""
        try:
            divs = self.driver.find_elements(By.TAG_NAME, "div")
            max_length = 0
            max_text = ""

            for div in divs:
                try:
                    text = div.text.strip()
                    if (len(text) > max_length and
                            len(text) > 200 and
                            not any(ad in text for ad in ['雜書屋', '最新章節', '記郵件'])):
                        max_length = len(text)
                        max_text = text
                except:
                    continue

            return max_text if max_length > 200 else None

        except Exception as e:
            print(f"查找最大文本塊失敗: {e}")
            return None

    def simulate_human_behavior(self):
        """模擬人類行為"""
        try:
            # 隨機滾動
            for _ in range(3):
                scroll_y = random.randint(100, 800)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_y})")
                time.sleep(random.uniform(0.5, 1.5))

            # 回到頂部
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(1)

        except Exception as e:
            print(f"模擬人類行為失敗: {e}")

    def clean_and_format_content(self, content):
        """清理和格式化內容"""
        if not content:
            return ""

        # 移除廣告
        ad_patterns = [
            r'.*雜書屋.*', r'.*杂书屋.*', r'.*zashuwu\.com.*',
            r'.*記郵件找地址.*', r'.*请记住.*', r'.*手機閱讀.*',
            r'.*最新章節.*', r'.*加入書簽.*'
        ]

        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 檢查廣告
            is_ad = any(re.search(pattern, line, re.IGNORECASE) for pattern in ad_patterns)

            if not is_ad and len(line) > 2:
                cleaned_lines.append(line)

        # 重新組合並格式化
        cleaned_content = '\n'.join(cleaned_lines)

        # 基本格式化
        cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)  # 移除多餘空行
        cleaned_content = re.sub(r'[ \t]+', ' ', cleaned_content)  # 標準化空格

        return cleaned_content

    def save_debug_info(self, url):
        """保存調試信息"""
        try:
            timestamp = int(time.time())
            debug_dir = 'debug_comprehensive'
            os.makedirs(debug_dir, exist_ok=True)

            # 截圖
            screenshot_file = os.path.join(debug_dir, f'screenshot_{timestamp}.png')
            self.driver.save_screenshot(screenshot_file)

            # 頁面源碼
            html_file = os.path.join(debug_dir, f'source_{timestamp}.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)

            # 信息摘要
            info_file = os.path.join(debug_dir, f'info_{timestamp}.txt')
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"頁面標題: {self.driver.title}\n")
                f.write(f"當前URL: {self.driver.current_url}\n")
                f.write(f"頁面大小: {len(self.driver.page_source)} 字符\n")

                # JavaScript檢查
                has_txt_call = '_txt_call' in self.driver.page_source
                f.write(f"包含_txt_call: {has_txt_call}\n")

                # 元素檢查
                try:
                    txt_content = self.driver.find_element(By.ID, "txtContent")
                    f.write(f"txtContent元素存在: True\n")
                    f.write(f"txtContent文字長度: {len(txt_content.text)}\n")
                except:
                    f.write(f"txtContent元素存在: False\n")

            print(f"調試信息保存到: {debug_dir}")

        except Exception as e:
            print(f"保存調試信息失敗: {e}")

    def quit(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()


def read_urls_from_csv(csv_file):
    """從CSV文件讀取URL"""
    urls = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳過表頭
        for row in reader:
            if len(row) > 1 and row[1].startswith(('https://', '"https://')):
                url = row[1].strip('"')
                urls.append(url)
    return urls


def load_proxies(proxy_file):
    """加載代理列表"""
    proxies = []
    try:
        with open(proxy_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
    except FileNotFoundError:
        print(f"代理文件 {proxy_file} 不存在")
    return proxies


def main():
    parser = argparse.ArgumentParser(description='綜合版小說爬蟲')
    parser.add_argument('--csv', type=str, default='m1.csv', help='CSV文件路徑')
    parser.add_argument('--output', type=str, default='wen_novel_comprehensive', help='輸出目錄')
    parser.add_argument('--delay', type=float, default=5.0, help='請求間延遲')
    parser.add_argument('--test', action='store_true', help='測試模式')
    parser.add_argument('--headless', action='store_true', help='無頭模式')
    parser.add_argument('--start', type=int, default=0, help='開始索引')
    parser.add_argument('--end', type=int, default=None, help='結束索引')
    parser.add_argument('--proxy-file', type=str, default=None, help='代理文件路徑')
    parser.add_argument('--use-ocr', action='store_true', help='啟用OCR圖片文字識別')
    parser.add_argument('--no-decoder', action='store_true', help='禁用解碼器')

    args = parser.parse_args()

    # 檢查依賴
    if args.use_ocr and not OCR_AVAILABLE:
        print("警告: 未安裝OCR依賴，將跳過OCR功能")

    if not args.no_decoder and not DECODER_AVAILABLE:
        print("警告: 未找到解碼器模塊，將跳過解碼功能")

    # 加載代理
    proxies = []
    if args.proxy_file:
        proxies = load_proxies(args.proxy_file)

    # 創建輸出目錄
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # 讀取URL
    urls = read_urls_from_csv(args.csv)
    print(f"找到 {len(urls)} 個URL")

    # 應用範圍限制
    if args.test:
        urls = urls[:1]
        print("測試模式：只爬取第一個URL")
    else:
        end = args.end if args.end is not None else len(urls)
        urls = urls[args.start:end]

    # 選擇代理
    proxy = random.choice(proxies) if proxies else None

    # 創建爬蟲實例
    crawler = ComprehensiveNovelCrawler(
        headless=args.headless,
        proxy=proxy,
        use_ocr=args.use_ocr,
        use_decoder=not args.no_decoder
    )

    try:
        # 設置驅動程序
        if not crawler.setup_driver():
            print("無法設置Firefox驅動程序，退出")
            return

        success_count = 0

        # 爬取每個URL
        for i, url in enumerate(urls):
            current_index = i + args.start
            print(f"\n{'=' * 60}")
            print(f"爬取 {current_index + 1}/{len(urls) + args.start}: {url}")
            print(f"{'=' * 60}")

            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(current_index + 1)

            # 爬取內容
            content = crawler.extract_content_comprehensive(url)

            if content:
                success_count += 1

                # 保存內容
                filename = os.path.join(args.output, f'chapter_{chapter_num}.txt')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ 保存到 {filename}")

                # 顯示預覽
                preview = content[:300] + '...' if len(content) > 300 else content
                print(f"預覽: {preview}")

                # 保存成功的URL記錄
                success_file = os.path.join(args.output, 'success.log')
                with open(success_file, 'a', encoding='utf-8') as f:
                    f.write(f"{chapter_num}\t{url}\t{len(content)}\n")

            else:
                print(f"✗ 無法獲取內容")

                # 保存失敗記錄
                error_file = os.path.join(args.output, 'errors.log')
                with open(error_file, 'a', encoding='utf-8') as f:
                    f.write(f"{chapter_num}\t{url}\t失敗\n")

            # 延遲
            if i < len(urls) - 1:
                delay_time = args.delay + random.uniform(-1, 1)
                print(f"等待 {delay_time:.1f} 秒...")
                time.sleep(max(1, delay_time))

        print(f"\n{'=' * 60}")
        print(f"爬取完成！成功: {success_count}/{len(urls)}")
        print(f"{'=' * 60}")

    finally:
        crawler.quit()


if __name__ == "__main__":
    main()