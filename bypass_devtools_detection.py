"""
繞過開發者工具檢測的爬蟲
"""
import undetected_chromedriver as uc
import time
import requests
import json
import re
from selenium.webdriver.common.by import By


def setup_anti_detection_driver():
    """設置反檢測瀏覽器"""
    options = uc.ChromeOptions()

    # 關鍵：禁用開發者工具相關功能
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # 禁用開發者工具檢測
    options.add_argument('--disable-dev-tools')

    # 其他設置
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')

    driver = uc.Chrome(options=options)

    # 注入反檢測腳本
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            // 覆蓋開發者工具檢測
            let devtools = {open: false, orientation: null};

            // 禁用 console.log 檢測
            const oldLog = console.log;
            console.log = function() {
                if (arguments[0] !== 'devtools') {
                    oldLog.apply(console, arguments);
                }
            };

            // 禁用 debugger 語句
            const noop = () => {};
            const oldDebugger = window.debugger;
            Object.defineProperty(window, 'debugger', {
                get: noop,
                set: noop
            });

            // 禁用性能檢測
            const oldNow = performance.now;
            performance.now = function() {
                return oldNow.call(performance);
            };

            // 覆蓋 toString 檢測
            const oldToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === window.console.log) {
                    return 'function log() { [native code] }';
                }
                return oldToString.call(this);
            };
        '''
    })

    return driver


def get_content_directly(url):
    """直接獲取內容（不打開瀏覽器界面）"""
    print("使用直接請求方式...")

    # 第一步：獲取頁面
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    session = requests.Session()

    # 訪問主頁獲取 cookies
    try:
        session.get('https://m.zashuwu.com/', headers=headers, timeout=10)
    except:
        pass

    # 獲取章節頁面
    response = session.get(url, headers=headers, timeout=10)

    # 提取 initTxt URL
    match = re.search(r'initTxt\("([^"]+)"', response.text)
    if not match:
        print("未找到 initTxt URL")
        return None

    txt_url = match.group(1)
    if txt_url.startswith('//'):
        txt_url = 'https:' + txt_url

    print(f"找到內容 URL: {txt_url}")

    # 獲取加密內容
    headers['Referer'] = url
    txt_response = session.get(txt_url, headers=headers, timeout=10)

    return txt_response.text


def decode_txt_content(txt_data):
    """解碼內容"""
    # 移除 _txt_call 包裝
    if txt_data.startswith('_txt_call(') and txt_data.endswith(')'):
        json_str = txt_data[10:-1]
    else:
        json_str = txt_data

    try:
        data = json.loads(json_str)
        content = data.get('content', '')
        replace_rules = data.get('replace', {})

        # 解碼十六進制內容
        decoded = decode_hex_string(content)

        # 應用替換規則
        for old, new in replace_rules.items():
            decoded = decoded.replace(old, new)

        return decoded

    except Exception as e:
        print(f"解碼失敗: {e}")
        return None


def decode_hex_string(hex_str):
    """解碼十六進制字符串"""
    # 分割並解碼
    parts = hex_str.split(';')
    result = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 提取4位十六進制
        hex_values = re.findall(r'[0-9a-fA-F]{4}', part)

        for hex_val in hex_values:
            try:
                # 轉換為 Unicode 字符
                char = chr(int(hex_val, 16))
                result.append(char)
            except:
                # 如果失敗，嘗試其他編碼
                try:
                    # 可能是 UTF-16
                    bytes_val = bytes.fromhex(hex_val)
                    char = bytes_val.decode('utf-16-be', errors='ignore')
                    result.append(char)
                except:
                    result.append(f'[{hex_val}]')

    return ''.join(result)


def get_content_with_browser(url):
    """使用瀏覽器獲取內容（避免開發者工具檢測）"""
    driver = setup_anti_detection_driver()

    try:
        print("訪問頁面...")
        driver.get(url)

        # 等待頁面加載
        time.sleep(5)

        # 檢查是否被重定向
        current_url = driver.current_url
        if current_url != url:
            print(f"被重定向到: {current_url}")

        # 嘗試獲取內容
        content = driver.execute_script("""
            // 獲取 txtContent
            const txtContent = document.getElementById('txtContent');
            if (txtContent) {
                return txtContent.innerText || txtContent.textContent;
            }

            // 查找其他可能的內容容器
            const selectors = ['#content', '#chaptercontent', '.readcontent'];
            for (const selector of selectors) {
                const el = document.querySelector(selector);
                if (el && el.innerText && el.innerText.length > 100) {
                    return el.innerText;
                }
            }

            return null;
        """)

        if content:
            print(f"獲取到內容，長度: {len(content)}")
            return content

        # 如果沒有內容，嘗試提取 initTxt URL
        init_url = driver.execute_script("""
            const scripts = document.getElementsByTagName('script');
            for (const script of scripts) {
                const content = script.innerHTML;
                const match = content.match(/initTxt\\("([^"]+)"/);
                if (match) {
                    return match[1];
                }
            }
            return null;
        """)

        if init_url:
            print(f"找到 initTxt URL: {init_url}")
            # 使用 requests 獲取內容
            if not init_url.startswith('http'):
                init_url = 'https:' + init_url

            response = requests.get(init_url, headers={
                'User-Agent': driver.execute_script("return navigator.userAgent"),
                'Referer': url
            })

            return decode_txt_content(response.text)

    finally:
        driver.quit()


def main():
    url = "https://m.zashuwu.com/wen/2vFm/1.html"

    print("=== 方法1: 直接HTTP請求 ===")
    txt_data = get_content_directly(url)
    if txt_data:
        content = decode_txt_content(txt_data)
        if content:
            print(f"\n解碼後內容前500字符:\n{content[:500]}")
            with open('decoded_content.txt', 'w', encoding='utf-8') as f:
                f.write(content)
            print("\n內容已保存到 decoded_content.txt")

    # 如果方法1失敗，嘗試方法2
    if not txt_data or not content:
        print("\n=== 方法2: 使用反檢測瀏覽器 ===")
        content = get_content_with_browser(url)
        if content:
            print(f"\n內容前500字符:\n{content[:500]}")
            with open('browser_content.txt', 'w', encoding='utf-8') as f:
                f.write(content)


if __name__ == "__main__":
    main()