"""
反檢測小說爬蟲 - 使用undetected-chromedriver繞過檢測
安裝：pip install undetected-chromedriver selenium
"""

import undetected_chromedriver as uc
import time
import csv
import os
import re
import random
import subprocess
import argparse
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


def setup_stealth_driver(headless=False):
    """設置隱身模式的Chrome驅動"""
    options = uc.ChromeOptions()

    if headless:
        options.add_argument('--headless')

    # 基本設置
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-blink-features=AutomationControlled')

    # 設置窗口大小
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')

    # 設置語言
    options.add_argument('--lang=zh-TW')


    # 設置用戶配置
    options.add_argument('--user-data-dir=/tmp/chrome_profile_' + str(random.randint(1000, 9999)))

    # 創建驅動（undetected-chromedriver會自動處理反檢測）
    # 自動檢測Chrome主版本號以匹配對應的ChromeDriver
    try:
        version_output = subprocess.check_output(["google-chrome", "--version"], stderr=subprocess.STDOUT, text=True)
        match = re.search(r"(\d+)\.", version_output)
        version_main = int(match.group(1)) if match else None
    except Exception:
        version_main = None
    driver = uc.Chrome(options=options, version_main=version_main)

    # 執行額外的反檢測腳本
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            // 覆蓋navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 覆蓋chrome屬性
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // 覆蓋permissions
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });

            // 覆蓋plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 覆蓋語言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-TW', 'zh', 'en']
            });

            // 修改用戶代理
            Object.defineProperty(navigator, 'userAgent', {
                get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            });
        '''
    })

    return driver


def extract_init_txt_url(driver):
    """提取移動端 initTxt 調用的內容 URL"""
    scripts = driver.find_elements(By.TAG_NAME, 'script')
    for script in scripts:
        content = script.get_attribute('innerHTML') or ''
        match = re.search(r"initTxt\((?:\"|')(.*?)(?:\"|')", content)
        if match:
            url = match.group(1)
            if not url.startswith('http'):
                url = 'https:' + url
            return url
    return None


def fetch_initTxt_content(txt_url, referer=None):
    """使用 requests 下載 initTxt 指向的純文本內容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                      ' (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    if referer:
        headers['Referer'] = referer
    resp = requests.get(txt_url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.text
    # 處理 _txt_call 格式
    if data.startswith('_txt_call("') and data.endswith('")'):
        inner = data.split('_txt_call("', 1)[1].rsplit('")', 1)[0]
        return inner
    return data


def simulate_human_behavior(driver, element=None):
    """模擬人類行為"""
    actions = ActionChains(driver)

    # 隨機移動鼠標
    for _ in range(random.randint(2, 4)):
        x_offset = random.randint(-100, 100)
        y_offset = random.randint(-100, 100)
        actions.move_by_offset(x_offset, y_offset)
        actions.pause(random.uniform(0.1, 0.3))

    # 如果有元素，移動到元素上
    if element:
        actions.move_to_element(element)
        actions.pause(random.uniform(0.5, 1.0))

    actions.perform()

    # 隨機滾動
    scroll_distance = random.randint(100, 300)
    driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
    time.sleep(random.uniform(0.5, 1.5))


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


def clean_content(text):
    """清理內容中的廣告"""
    ad_patterns = [
        r'.*雜書屋.*',
        r'.*杂书屋.*',
        r'.*zashuwu\.com.*',
        r'.*ZASHUWU\.COM.*',
        r'.*記郵件找地址.*',
        r'.*记邮件找地址.*',
        r'.*dz@.*',
        r'.*請記住.*',
        r'.*请记住.*',
        r'.*手機閱讀.*',
        r'.*手机阅读.*',
        r'.*最新章節.*',
        r'.*最新章节.*',
        r'.*http[s]?://.*\.com.*',
        r'^--$',
        r'^\s*$'
    ]

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_ad = False
        for pattern in ad_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_ad = True
                break

        if not is_ad:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def crawl_novel_content_stealth(driver, url, max_retries=3):
    """使用反檢測技術爬取小說內容"""
    for attempt in range(max_retries):
        try:
            print(f"嘗試 {attempt + 1}/{max_retries}: {url}")

            # 清除cookies（有時候需要）
            if attempt > 0:
                driver.delete_all_cookies()
                time.sleep(2)

            # 訪問URL
            driver.get(url)

            # 檢查是否被重定向
            current_url = driver.current_url
            if current_url != url:
                print(f"檢測到重定向: {current_url}")
                print("可能被檢測為機器人，嘗試繞過...")

            # 隨機等待
            wait_time = random.uniform(3, 6)
            print(f"等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)

            # 模擬人類行為
            simulate_human_behavior(driver)

            # 嘗試提取 initTxt 動態加載 URL 並使用 requests 下載純文本
            init_url = extract_init_txt_url(driver)
            if init_url:
                print(f"找到 initTxt URL: {init_url}")
                try:
                    txt = fetch_initTxt_content(init_url, referer=url)
                    print(f"通過 requests 獲取純文本，長度: {len(txt)}")
                    return clean_content(txt)
                except Exception as e:
                    print(f"通過 requests 獲取 txt 失敗: {e}")

            # 等待內容加載
            wait = WebDriverWait(driver, 20)

            # 嘗試等待txtContent出現
            try:
                wait.until(EC.presence_of_element_located((By.ID, "txtContent")))
                print("檢測到txtContent元素")
            except:
                print("txtContent元素未出現，繼續嘗試...")

            # 額外等待JavaScript解密
            time.sleep(random.uniform(5, 8))

            # 再次模擬人類行為
            simulate_human_behavior(driver)

            # 嘗試獲取內容
            content_text = driver.execute_script("""
                // 嘗試多種方式獲取內容

                // 方法1：直接獲取txtContent
                var txtContent = document.getElementById('txtContent');
                if (txtContent) {
                    var text = txtContent.innerText || txtContent.textContent || '';
                    if (text.length > 100 && !text.includes('This content is encoded')) {
                        console.log('Found content in txtContent');
                        return text;
                    }
                }

                // 方法2：查找所有可能的容器
                var selectors = ['#content', '#chaptercontent', '#chapter-content', '.readcontent', '.read-content'];
                for (var i = 0; i < selectors.length; i++) {
                    var el = document.querySelector(selectors[i]);
                    if (el) {
                        var text = el.innerText || el.textContent || '';
                        if (text.length > 500 && text.includes('葉洵')) {
                            console.log('Found content in ' + selectors[i]);
                            return text;
                        }
                    }
                }

                // 方法3：查找包含小說內容的最大文本塊
                var divs = document.getElementsByTagName('div');
                var maxLength = 0;
                var maxText = '';

                for (var i = 0; i < divs.length; i++) {
                    var text = divs[i].innerText || divs[i].textContent || '';
                    if (text.length > maxLength &&
                        !text.includes('[都市小说]') &&
                        !text.includes('最新章節') &&
                        text.length > 500) {
                        maxLength = text.length;
                        maxText = text;
                    }
                }

                if (maxText) {
                    console.log('Found content in largest text block');
                    return maxText;
                }

                return '';
            """)

            if content_text and len(content_text) > 100:
                print(f"成功獲取內容，長度: {len(content_text)}")
                return clean_content(content_text)

            # 如果沒有內容，嘗試刷新頁面
            if attempt < max_retries - 1:
                print("未獲取到內容，嘗試刷新頁面...")
                driver.refresh()
                time.sleep(random.uniform(3, 5))

        except Exception as e:
            print(f"嘗試 {attempt + 1} 失敗: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    # 所有嘗試都失敗
    print(f"無法獲取內容: {url}")

    # 保存調試信息
    timestamp = int(time.time())
    driver.save_screenshot(f'debug_stealth_{timestamp}.png')

    with open(f'debug_stealth_{timestamp}.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)

    print(f"調試信息已保存: debug_stealth_{timestamp}.png 和 .html")

    return None


def main():
    parser = argparse.ArgumentParser(description='反檢測小說爬蟲')
    parser.add_argument('--csv', type=str, default='m1.csv', help='CSV文件路徑')
    parser.add_argument('--output', type=str, default='wen_novel', help='輸出目錄')
    parser.add_argument('--delay', type=float, default=5.0, help='請求間延遲')
    parser.add_argument('--test', action='store_true', help='測試模式')
    parser.add_argument('--headless', action='store_true', help='無頭模式（不推薦）')
    parser.add_argument('--start', type=int, default=0, help='開始索引')
    parser.add_argument('--end', type=int, default=None, help='結束索引')

    args = parser.parse_args()

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

    # 設置驅動
    print("初始化隱身模式瀏覽器...")
    driver = setup_stealth_driver(headless=args.headless)

    try:
        success_count = 0
        fail_count = 0

        # 爬取每個URL
        for i, url in enumerate(urls):
            current_index = i + args.start
            print(f"\n{'=' * 50}")
            print(f"爬取 {current_index + 1}/{len(urls) + args.start}: {url}")

            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(current_index + 1)

            # 爬取內容
            content = crawl_novel_content_stealth(driver, url)

            if content:
                # 保存內容
                filename = os.path.join(args.output, f'chapter_{chapter_num}.txt')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ 成功保存到 {filename}")
                success_count += 1

                # 顯示預覽
                preview = content[:150] + '...' if len(content) > 150 else content
                print(f"預覽: {preview}")
            else:
                print(f"✗ 無法獲取內容")
                fail_count += 1

                # 保存錯誤信息
                error_file = os.path.join(args.output, f'error_chapter_{chapter_num}.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"無法爬取內容: {url}\n")
                    f.write("可能被反爬蟲系統檢測\n")

            # 隨機延遲
            if i < len(urls) - 1:
                delay = random.uniform(args.delay, args.delay + 2)
                print(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)

        print(f"\n{'=' * 50}")
        print(f"爬取完成！成功: {success_count}, 失敗: {fail_count}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()