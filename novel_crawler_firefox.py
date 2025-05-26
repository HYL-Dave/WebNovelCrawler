"""
使用Firefox的小說爬蟲 - 避免Chromium檢測
安裝: pip install selenium webdriver-manager
"""

import csv
import os
import re
import time
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


class FirefoxNovelCrawler:
    def __init__(self, headless=False, proxy=None):
        self.headless = headless
        self.proxy = proxy
        self.driver = None

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

        # 禁用圖片加載以提高速度
        firefox_options.set_preference('permissions.default.image', 2)

        # 禁用CSS和JavaScript（可選，但可能影響內容加載）
        # firefox_options.set_preference('javascript.enabled', False)

        # 設置代理
        if self.proxy:
            proxy_parts = self.proxy.replace('http://', '').replace('https://', '').split('@')
            if len(proxy_parts) == 2:
                # 有用戶名密碼的代理
                auth, proxy_host = proxy_parts
                username, password = auth.split(':')
                host, port = proxy_host.split(':')

                firefox_options.set_preference('network.proxy.type', 1)
                firefox_options.set_preference('network.proxy.http', host)
                firefox_options.set_preference('network.proxy.http_port', int(port))
                firefox_options.set_preference('network.proxy.ssl', host)
                firefox_options.set_preference('network.proxy.ssl_port', int(port))

                # Firefox需要額外的擴展來處理認證代理
                print(f"警告: Firefox代理認證需要額外配置")
            else:
                # 無認證代理
                host, port = self.proxy.replace('http://', '').replace('https://', '').split(':')
                firefox_options.set_preference('network.proxy.type', 1)
                firefox_options.set_preference('network.proxy.http', host)
                firefox_options.set_preference('network.proxy.http_port', int(port))
                firefox_options.set_preference('network.proxy.ssl', host)
                firefox_options.set_preference('network.proxy.ssl_port', int(port))

        try:
            # 自動下載並使用匹配版本的GeckoDriver
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)

            # 設置窗口大小
            self.driver.set_window_size(1920, 1080)

            # 移除webdriver屬性
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print("✓ Firefox驅動程序設置成功")
            return self.driver

        except Exception as e:
            print(f"✗ Firefox驅動程序設置失敗: {e}")
            return None

    def wait_for_content_load(self, timeout=20):
        """等待內容加載完成"""
        try:
            # 等待txtContent元素出現
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "txtContent"))
            )

            # 等待內容實際加載
            WebDriverWait(self.driver, timeout).until(
                lambda driver: len(driver.find_element(By.ID, "txtContent").text) > 100
            )

            print("✓ 內容加載完成")
            return True

        except TimeoutException:
            print("✗ 內容加載超時")
            return False

    def simulate_human_behavior(self):
        """模擬人類行為"""
        try:
            # 隨機滾動
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(3):
                scroll_position = random.randint(0, scroll_height)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position})")
                time.sleep(random.uniform(0.5, 1.5))

            # 滾動到頂部
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(1)

            # 模擬鼠標移動（通過JavaScript）
            self.driver.execute_script("""
                var event = new MouseEvent('mousemove', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': Math.random() * window.innerWidth,
                    'clientY': Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)

        except Exception as e:
            print(f"模擬人類行為時出錯: {e}")

    def extract_content(self, url):
        """提取小說內容"""
        try:
            print(f"訪問: {url}")

            # 訪問頁面
            self.driver.get(url)

            # 等待初始頁面加載
            time.sleep(3)

            # 模擬人類行為
            self.simulate_human_behavior()

            # 等待內容加載
            if not self.wait_for_content_load():
                print("嘗試等待更長時間...")
                time.sleep(10)

            # 嘗試多種方法獲取內容
            content = self.try_multiple_extractors()

            if content:
                print(f"✓ 成功獲取內容，長度: {len(content)}")
                return self.clean_content(content)
            else:
                print("✗ 無法獲取內容")
                self.save_debug_info(url)
                return None

        except Exception as e:
            print(f"✗ 提取內容失敗: {e}")
            return None

    def try_multiple_extractors(self):
        """嘗試多種內容提取方法"""
        extractors = [
            self.extract_from_txtcontent,
            self.extract_from_common_selectors,
            self.extract_from_largest_text_block,
            self.extract_from_paragraph_tags
        ]

        for extractor in extractors:
            try:
                content = extractor()
                if content and len(content) > 100:
                    print(f"✓ {extractor.__name__} 成功")
                    return content
            except Exception as e:
                print(f"✗ {extractor.__name__} 失敗: {e}")

        return None

    def extract_from_txtcontent(self):
        """從txtContent元素提取"""
        element = self.driver.find_element(By.ID, "txtContent")
        return element.text

    def extract_from_common_selectors(self):
        """從常見選擇器提取"""
        selectors = [
            '#content', '#chaptercontent', '#chapter-content', '#BookText',
            '.readcontent', '.read-content', '.novel-content', '.content'
        ]

        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text
                if len(text) > 100:
                    return text
            except:
                continue

        return None

    def extract_from_largest_text_block(self):
        """提取最大的文本塊"""
        divs = self.driver.find_elements(By.TAG_NAME, "div")
        max_length = 0
        max_text = ""

        for div in divs:
            try:
                text = div.text
                if (len(text) > max_length and
                        len(text) > 500 and
                        '[都市小说]' not in text and
                        '最新章节' not in text):
                    max_length = len(text)
                    max_text = text
            except:
                continue

        return max_text if max_length > 500 else None

    def extract_from_paragraph_tags(self):
        """從段落標籤提取"""
        paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
        content_paragraphs = []

        for p in paragraphs:
            try:
                text = p.text.strip()
                if len(text) > 10:  # 過濾太短的段落
                    content_paragraphs.append(text)
            except:
                continue

        if len(content_paragraphs) > 5:  # 至少有5個段落
            return '\n'.join(content_paragraphs)

        return None

    def clean_content(self, text):
        """清理內容"""
        if not text:
            return ""

        # 移除廣告相關內容
        ad_patterns = [
            r'.*雜書屋.*', r'.*杂书屋.*', r'.*zashuwu\.com.*',
            r'.*記郵件找地址.*', r'.*请记住.*', r'.*手機閱讀.*',
            r'.*最新章節.*', r'.*加入書簽.*', r'.*http[s]?://.*\.com.*'
        ]

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 檢查是否為廣告
            is_ad = any(re.search(pattern, line, re.IGNORECASE) for pattern in ad_patterns)

            if not is_ad and len(line) > 2:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def save_debug_info(self, url):
        """保存調試信息"""
        try:
            timestamp = int(time.time())

            # 保存截圖
            screenshot_file = f'debug_firefox_{timestamp}.png'
            self.driver.save_screenshot(screenshot_file)
            print(f"截圖保存到: {screenshot_file}")

            # 保存頁面源碼
            html_file = f'debug_firefox_{timestamp}.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"頁面源碼保存到: {html_file}")

            # 保存元素信息
            info_file = f'debug_firefox_{timestamp}.txt'
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"頁面標題: {self.driver.title}\n")
                f.write(f"當前URL: {self.driver.current_url}\n\n")

                # 列出所有div元素的信息
                divs = self.driver.find_elements(By.TAG_NAME, "div")
                f.write(f"找到 {len(divs)} 個div元素:\n")

                for i, div in enumerate(divs[:20]):  # 只列出前20個
                    try:
                        div_id = div.get_attribute('id')
                        div_class = div.get_attribute('class')
                        div_text = div.text[:100] if div.text else ''
                        f.write(f"div[{i}]: id='{div_id}', class='{div_class}', text='{div_text}'\n")
                    except:
                        f.write(f"div[{i}]: 無法獲取信息\n")

            print(f"調試信息保存到: {info_file}")

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
    parser = argparse.ArgumentParser(description='使用Firefox爬取小說內容')
    parser.add_argument('--csv', type=str, default='m1.csv', help='CSV文件路徑')
    parser.add_argument('--output', type=str, default='wen_novel_firefox', help='輸出目錄')
    parser.add_argument('--delay', type=float, default=5.0, help='請求間延遲')
    parser.add_argument('--test', action='store_true', help='測試模式')
    parser.add_argument('--headless', action='store_true', help='無頭模式')
    parser.add_argument('--start', type=int, default=0, help='開始索引')
    parser.add_argument('--end', type=int, default=None, help='結束索引')
    parser.add_argument('--proxy-file', type=str, default=None, help='代理文件路徑')

    args = parser.parse_args()

    # 加載代理
    proxies = []
    if args.proxy_file:
        proxies = load_proxies(args.proxy_file)
        if proxies:
            print(f"加載了 {len(proxies)} 個代理")
        else:
            print("未能加載任何代理")

    # 創建輸出目錄
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"創建輸出目錄: {args.output}")

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
    if proxy:
        print(f"使用代理: {proxy}")

    # 創建爬蟲實例
    crawler = FirefoxNovelCrawler(headless=args.headless, proxy=proxy)

    try:
        # 設置驅動程序
        if not crawler.setup_driver():
            print("無法設置Firefox驅動程序，退出")
            return

        # 爬取每個URL
        for i, url in enumerate(urls):
            current_index = i + args.start
            print(f"\n爬取 {current_index + 1}/{len(urls) + args.start}: {url}")

            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(current_index + 1)

            # 爬取內容
            content = crawler.extract_content(url)

            if content:
                # 保存內容
                filename = os.path.join(args.output, f'chapter_{chapter_num}.txt')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ 保存到 {filename}")

                # 顯示預覽
                preview = content[:200] + '...' if len(content) > 200 else content
                print(f"預覽: {preview}")
            else:
                print(f"✗ 無法獲取內容")
                # 保存錯誤信息
                error_file = os.path.join(args.output, f'error_chapter_{chapter_num}.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"無法爬取內容: {url}\n")

            # 延遲
            if i < len(urls) - 1:
                delay_time = args.delay + random.uniform(-1, 1)  # 添加隨機延遲
                print(f"等待 {delay_time:.1f} 秒...")
                time.sleep(delay_time)

    finally:
        crawler.quit()
        print("\n爬取完成！")


if __name__ == "__main__":
    main()