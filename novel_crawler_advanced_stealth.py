"""
進階反檢測爬蟲 - 包含多種繞過技術
需要安裝：
pip install undetected-chromedriver selenium pyautogui
"""

import undetected_chromedriver as uc
import time
import csv
import os
import re
import random
import json
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pyautogui


class StealthCrawler:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.setup_driver()

    def setup_driver(self):
        """設置超級隱身模式的瀏覽器"""
        options = uc.ChromeOptions()

        # 不使用無頭模式以避免檢測
        if self.headless:
            print("警告：無頭模式更容易被檢測，建議使用有界面模式")
            options.add_argument('--headless')

        # 設置真實的瀏覽器配置
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_settings.popups': 0,
            'profile.managed_default_content_settings.images': 1,
            'profile.content_settings.plugin_whitelist.adobe-flash-player': 1,
            'profile.content_settings.exceptions.plugins.*,*.per_resource.adobe-flash-player': 1,
            'profile.default_content_setting_values.cookies': 1,
            'profile.block_third_party_cookies': False
        }
        options.add_experimental_option('prefs', prefs)

        # 使用真實的用戶配置目錄
        import tempfile
        user_data_dir = tempfile.mkdtemp()
        options.add_argument(f'--user-data-dir={user_data_dir}')

        # 其他選項
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-gpu')

        # 設置窗口位置和大小（模擬真實用戶）
        options.add_argument('--window-position=100,50')
        options.add_argument('--window-size=1366,768')

        # 創建驅動
        self.driver = uc.Chrome(options=options, version_main=None)

        # 注入更多的反檢測JavaScript
        self.inject_stealth_js()

    def inject_stealth_js(self):
        """注入高級反檢測JavaScript"""
        stealth_js = """
        // 完整的反檢測腳本

        // 1. 覆蓋webdriver檢測
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });

        // 2. 修改navigator屬性
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });

        Object.defineProperty(navigator, 'vendor', {
            get: () => 'Google Inc.'
        });

        Object.defineProperty(navigator, 'appVersion', {
            get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        });

        // 3. 修改chrome對象
        if (!window.chrome) {
            window.chrome = {};
        }

        window.chrome.runtime = {
            connect: () => {},
            sendMessage: () => {}
        };

        window.chrome.app = {
            isInstalled: false,
            getDetails: () => {}
        };

        // 4. 覆蓋權限API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // 5. 修改插件數組
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                return [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: ""},
                        description: "",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ];
            }
        });

        // 6. 修改語言
        Object.defineProperty(navigator, 'language', {
            get: () => 'zh-TW'
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-TW', 'zh', 'en-US', 'en']
        });

        // 7. 修改屏幕屬性
        Object.defineProperty(screen, 'availWidth', {
            get: () => 1366
        });

        Object.defineProperty(screen, 'availHeight', {
            get: () => 728
        });

        // 8. 覆蓋WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter(parameter);
        };

        // 9. 修改電池API
        if (navigator.getBattery) {
            navigator.getBattery = () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1
            });
        }

        // 10. 隱藏自動化擴展
        const originalGetOwnPropertyDescriptors = Object.getOwnPropertyDescriptors;
        Object.getOwnPropertyDescriptors = function(...args) {
            const result = originalGetOwnPropertyDescriptors.apply(this, args);
            delete result.webdriver;
            return result;
        };
        """

        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': stealth_js
        })

    def simulate_real_user(self):
        """模擬真實用戶行為"""
        # 隨機滾動
        scroll_height = self.driver.execute_script("return document.body.scrollHeight")
        current_position = 0

        while current_position < scroll_height / 2:
            scroll_distance = random.randint(100, 300)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance})")
            current_position += scroll_distance
            time.sleep(random.uniform(0.5, 1.5))

        # 隨機移動鼠標（使用pyautogui）
        try:
            window_size = self.driver.get_window_size()
            window_position = self.driver.get_window_position()

            for _ in range(random.randint(2, 4)):
                x = window_position['x'] + random.randint(100, window_size['width'] - 100)
                y = window_position['y'] + random.randint(100, window_size['height'] - 100)
                pyautogui.moveTo(x, y, duration=random.uniform(0.5, 1.5))
                time.sleep(random.uniform(0.1, 0.3))
        except:
            pass  # 如果pyautogui失敗，繼續執行

    def check_and_handle_detection(self):
        """檢查並處理反爬蟲檢測"""
        current_url = self.driver.current_url
        page_title = self.driver.title

        # 檢查常見的反爬蟲頁面特徵
        detection_signs = [
            'robot', 'bot', 'captcha', 'verify', 'forbidden',
            '403', '機器人', '驗證', '禁止訪問'
        ]

        page_source_lower = self.driver.page_source.lower()

        for sign in detection_signs:
            if sign in current_url.lower() or sign in page_title.lower() or sign in page_source_lower:
                print(f"檢測到反爬蟲頁面，特徵: {sign}")
                return True

        return False

    def get_with_retry(self, url, max_retries=3):
        """帶重試機制的頁面訪問"""
        for attempt in range(max_retries):
            try:
                # 清除cookies重新開始
                if attempt > 0:
                    self.driver.delete_all_cookies()
                    time.sleep(2)

                # 訪問頁面
                self.driver.get(url)

                # 等待頁面加載
                time.sleep(random.uniform(2, 4))

                # 檢查是否被檢測
                if self.check_and_handle_detection():
                    print(f"第{attempt + 1}次嘗試被檢測為機器人")
                    if attempt < max_retries - 1:
                        print("等待30秒後重試...")
                        time.sleep(30)
                        continue
                else:
                    return True

            except Exception as e:
                print(f"訪問出錯: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)

        return False

    def extract_novel_content(self):
        """提取小說內容"""
        # 模擬用戶行為
        self.simulate_real_user()

        # 等待內容加載
        time.sleep(random.uniform(5, 8))

        # 嘗試多次獲取內容
        for _ in range(3):
            content = self.driver.execute_script("""
                // 查找txtContent
                var txtContent = document.getElementById('txtContent');
                if (txtContent) {
                    var text = txtContent.innerText || txtContent.textContent || '';
                    if (text.length > 100 && !text.includes('This content is encoded')) {
                        return text;
                    }
                }

                // 查找其他可能的容器
                var containers = document.querySelectorAll('#content, #chaptercontent, .readcontent, .read-content');
                for (var i = 0; i < containers.length; i++) {
                    var text = containers[i].innerText || containers[i].textContent || '';
                    if (text.length > 500) {
                        return text;
                    }
                }

                return '';
            """)

            if content:
                return content

            # 等待更長時間
            time.sleep(3)

        return None

    def save_session(self, filepath='session.json'):
        """保存session信息"""
        cookies = self.driver.get_cookies()
        with open(filepath, 'w') as f:
            json.dump(cookies, f)

    def load_session(self, filepath='session.json'):
        """加載session信息"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)

    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()


def clean_content(text):
    """清理廣告內容"""
    if not text:
        return ""

    ad_patterns = [
        r'.*雜書屋.*', r'.*杂书屋.*', r'.*zashuwu\.com.*',
        r'.*記郵件找地址.*', r'.*dz@.*', r'.*請記住.*',
        r'.*手機閱讀.*', r'.*最新章節.*', r'.*http[s]?://.*\.com.*'
    ]

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_ad = any(re.search(pattern, line, re.IGNORECASE) for pattern in ad_patterns)
        if not is_ad:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def main():
    parser = argparse.ArgumentParser(description='進階反檢測爬蟲')
    parser.add_argument('--csv', type=str, default='m1.csv')
    parser.add_argument('--output', type=str, default='wen_novel')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=None)

    args = parser.parse_args()

    # 創建輸出目錄
    os.makedirs(args.output, exist_ok=True)

    # 讀取URLs
    urls = []
    with open(args.csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) > 1:
                urls.append(row[1].strip('"'))

    if args.test:
        urls = urls[:1]
    else:
        end = args.end or len(urls)
        urls = urls[args.start:end]

    print(f"準備爬取 {len(urls)} 個URL")

    # 創建爬蟲實例
    crawler = StealthCrawler(headless=False)

    try:
        for i, url in enumerate(urls):
            print(f"\n{'=' * 60}")
            print(f"爬取 {i + 1}/{len(urls)}: {url}")

            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(i + 1)

            # 訪問頁面
            if crawler.get_with_retry(url):
                # 提取內容
                content = crawler.extract_novel_content()

                if content:
                    # 清理並保存
                    cleaned_content = clean_content(content)

                    filename = os.path.join(args.output, f'chapter_{chapter_num}.txt')
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)

                    print(f"✓ 成功保存: {filename}")
                    print(f"內容預覽: {cleaned_content[:100]}...")

                    # 保存session
                    if i == 0:
                        crawler.save_session()
                else:
                    print("✗ 無法獲取內容")
            else:
                print("✗ 無法訪問頁面")

            # 隨機延遲
            if i < len(urls) - 1:
                delay = random.uniform(10, 20)
                print(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)

    finally:
        crawler.close()

    print("\n爬取完成！")


if __name__ == "__main__":
    main()