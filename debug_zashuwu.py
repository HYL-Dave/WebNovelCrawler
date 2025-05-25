import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json
import re


def setup_debug_driver():
    """設置調試用的瀏覽器驅動"""
    chrome_options = Options()
    # 不使用無頭模式，方便觀察
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def analyze_zashuwu_structure(url):
    """分析zashuwu.com的網頁結構"""
    driver = setup_debug_driver()

    try:
        print(f"訪問URL: {url}")
        driver.get(url)

        # 等待頁面加載
        print("等待頁面加載...")
        time.sleep(5)

        # 1. 檢查所有的script標籤
        print("\n=== 分析Script標籤 ===")
        scripts = driver.find_elements(By.TAG_NAME, 'script')
        for i, script in enumerate(scripts):
            src = script.get_attribute('src')
            content = script.get_attribute('innerHTML')

            if src:
                print(f"\nScript {i + 1} - 外部腳本: {src}")
            elif content:
                print(f"\nScript {i + 1} - 內嵌腳本:")
                # 查找關鍵函數
                if 'initTxt' in content:
                    print("  發現 initTxt 函數！")
                    # 提取URL
                    match = re.search(r'initTxt\("([^"]+)"', content)
                    if match:
                        txt_url = match.group(1)
                        print(f"  內容URL: {txt_url}")

                if '_txt_call' in content:
                    print("  發現 _txt_call 函數！")

                if 'decrypt' in content.lower() or 'decode' in content.lower():
                    print("  可能包含解密函數")

                # 顯示前200個字符
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"  預覽: {preview}")

        # 2. 嘗試執行JavaScript獲取全局變量
        print("\n=== 檢查JavaScript全局變量 ===")
        try:
            # 獲取window對象的所有屬性
            window_props = driver.execute_script("""
                var props = [];
                for (var prop in window) {
                    if (window.hasOwnProperty(prop)) {
                        var type = typeof window[prop];
                        if (type === 'string' || type === 'number' || type === 'boolean') {
                            props.push({name: prop, type: type, value: window[prop]});
                        } else if (type === 'function') {
                            props.push({name: prop, type: type, value: 'function'});
                        }
                    }
                }
                return props;
            """)

            # 查找可能相關的變量
            interesting_props = []
            keywords = ['txt', 'content', 'novel', 'chapter', 'decrypt', 'decode', 'data']

            for prop in window_props:
                name_lower = prop['name'].lower()
                if any(keyword in name_lower for keyword in keywords):
                    interesting_props.append(prop)

            if interesting_props:
                print("發現可能相關的變量:")
                for prop in interesting_props[:10]:  # 只顯示前10個
                    print(f"  {prop['name']} ({prop['type']}): {str(prop['value'])[:100]}")

        except Exception as e:
            print(f"獲取全局變量失敗: {e}")

        # 3. 查找頁面上的文本內容
        print("\n=== 查找頁面文本內容 ===")

        # 嘗試各種可能的內容容器
        selectors = [
            '#content', '#chaptercontent', '#txtContent', '#BookText',
            '.content', '.readcontent', '.read-content', '.chapter-content',
            'article', '[class*="content"]', '[id*="content"]',
            '[class*="chapter"]', '[id*="chapter"]', '[class*="txt"]'
        ]

        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 50:  # 有實質內容
                            print(f"\n找到內容在 {selector}:")
                            print(f"  文本長度: {len(text)} 字符")
                            print(f"  預覽: {text[:100]}...")

                            # 檢查是否包含小說內容
                            if any(keyword in text for keyword in ['葉洵', '秦王', '第', '章']):
                                print("  ✓ 可能是小說內容！")
            except:
                pass

        # 4. 嘗試攔截網絡請求
        print("\n=== 執行JavaScript獲取動態內容 ===")

        # 嘗試觸發內容加載
        try:
            # 執行可能的初始化函數
            init_result = driver.execute_script("""
                // 嘗試查找並執行初始化函數
                if (typeof initTxt === 'function') {
                    console.log('Found initTxt function');
                    return 'initTxt function exists';
                }
                if (typeof loadContent === 'function') {
                    console.log('Found loadContent function');
                    return 'loadContent function exists';
                }

                // 查找所有可能的內容容器
                var containers = document.querySelectorAll('[id*="content"], [class*="content"]');
                var maxLength = 0;
                var maxContent = '';

                for (var i = 0; i < containers.length; i++) {
                    var text = containers[i].innerText || containers[i].textContent || '';
                    if (text.length > maxLength) {
                        maxLength = text.length;
                        maxContent = text;
                    }
                }

                return {
                    contentLength: maxLength,
                    contentPreview: maxContent.substring(0, 200)
                };
            """)

            print(f"JavaScript執行結果: {init_result}")

        except Exception as e:
            print(f"JavaScript執行失敗: {e}")

        # 5. 保存頁面快照
        print("\n=== 保存調試信息 ===")

        # 保存截圖
        driver.save_screenshot('debug_screenshot.png')
        print("截圖已保存到 debug_screenshot.png")

        # 保存頁面源碼
        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("頁面源碼已保存到 debug_page_source.html")

        # 保存控制台日誌
        logs = driver.get_log('browser')
        if logs:
            with open('debug_console_logs.txt', 'w', encoding='utf-8') as f:
                for log in logs:
                    f.write(f"{log['level']}: {log['message']}\n")
            print("控制台日誌已保存到 debug_console_logs.txt")

        # 6. 嘗試獲取_txt_call的內容
        print("\n=== 嘗試獲取加密內容 ===")
        try:
            # 查找所有的script標籤，尋找initTxt調用
            script_content = driver.execute_script("""
                var scripts = document.getElementsByTagName('script');
                for (var i = 0; i < scripts.length; i++) {
                    var content = scripts[i].innerHTML;
                    if (content.includes('initTxt')) {
                        return content;
                    }
                }
                return null;
            """)

            if script_content:
                # 提取URL
                match = re.search(r'initTxt\("([^"]+)"', script_content)
                if match:
                    txt_url = match.group(1)
                    if not txt_url.startswith('http'):
                        txt_url = 'https:' + txt_url

                    print(f"找到內容URL: {txt_url}")

                    # 嘗試fetch這個URL
                    fetch_result = driver.execute_script(f"""
                        return fetch('{txt_url}')
                            .then(response => response.text())
                            .then(data => {{
                                console.log('Fetched data:', data.substring(0, 100));
                                return {{
                                    success: true,
                                    data: data.substring(0, 500),
                                    length: data.length
                                }};
                            }})
                            .catch(error => {{
                                return {{
                                    success: false,
                                    error: error.toString()
                                }};
                            }});
                    """)

                    # 等待Promise解析
                    time.sleep(2)

                    print(f"Fetch結果: {fetch_result}")

        except Exception as e:
            print(f"獲取加密內容失敗: {e}")

        # 讓用戶有時間查看瀏覽器
        input("\n按Enter鍵繼續...")

    except Exception as e:
        print(f"分析過程出錯: {e}")

    finally:
        driver.quit()


def compare_with_without_js(url):
    """比較有無JavaScript的頁面差異"""
    print("\n=== 比較有無JavaScript的差異 ===")

    # 1. 無JavaScript
    print("\n1. 禁用JavaScript訪問:")
    chrome_options = Options()
    prefs = {'profile.managed_default_content_settings.javascript': 2}
    chrome_options.add_experimental_option('prefs', prefs)
    driver_no_js = webdriver.Chrome(options=chrome_options)

    try:
        driver_no_js.get(url)
        time.sleep(2)
        no_js_content = driver_no_js.find_element(By.TAG_NAME, 'body').text
        print(f"無JS內容長度: {len(no_js_content)} 字符")

        with open('debug_no_js.txt', 'w', encoding='utf-8') as f:
            f.write(no_js_content)
        print("無JS內容已保存到 debug_no_js.txt")

    finally:
        driver_no_js.quit()

    # 2. 啟用JavaScript
    print("\n2. 啟用JavaScript訪問:")
    driver_with_js = webdriver.Chrome()

    try:
        driver_with_js.get(url)
        time.sleep(5)  # 給JS更多時間執行
        with_js_content = driver_with_js.find_element(By.TAG_NAME, 'body').text
        print(f"有JS內容長度: {len(with_js_content)} 字符")

        with open('debug_with_js.txt', 'w', encoding='utf-8') as f:
            f.write(with_js_content)
        print("有JS內容已保存到 debug_with_js.txt")

    finally:
        driver_with_js.quit()

    print("\n差異分析完成！請比較 debug_no_js.txt 和 debug_with_js.txt")


if __name__ == "__main__":
    # 測試URL
    test_url = "https://m.zashuwu.com/wen/2vFm/1.html"

    print("開始分析網站結構...")
    analyze_zashuwu_structure(test_url)

    # 可選：比較有無JavaScript的差異
    # compare_with_without_js(test_url)