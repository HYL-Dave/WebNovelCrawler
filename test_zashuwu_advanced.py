import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import re


def test_zashuwu_content(url="https://m.zashuwu.com/wen/2vFm/1.html"):
    """深入測試zashuwu.com的內容獲取"""

    # 設置Chrome選項
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # 啟用網絡日誌
    chrome_options.set_capability('goog:loggingPrefs', {
        'browser': 'ALL',
        'network': 'ALL',
        'performance': 'ALL'
    })

    driver = webdriver.Chrome(options=chrome_options)

    try:
        print(f"測試URL: {url}")
        driver.get(url)

        # 階段1：初始加載
        print("\n=== 階段1：初始頁面加載 ===")
        time.sleep(3)

        # 檢查是否有initTxt函數
        init_txt_info = driver.execute_script("""
            if (typeof initTxt === 'function') {
                return {
                    exists: true,
                    toString: initTxt.toString()
                };
            }
            return { exists: false };
        """)
        print(f"initTxt函數存在: {init_txt_info['exists']}")

        # 查找包含initTxt調用的script
        txt_url = None
        scripts = driver.find_elements(By.TAG_NAME, 'script')
        for script in scripts:
            content = script.get_attribute('innerHTML')
            if content and 'initTxt' in content:
                match = re.search(r'initTxt\("([^"]+)"', content)
                if match:
                    txt_url = match.group(1)
                    if not txt_url.startswith('http'):
                        txt_url = 'https:' + txt_url
                    print(f"找到內容URL: {txt_url}")
                    break

        # 階段2：等待內容加載
        print("\n=== 階段2：等待內容加載 ===")

        # 監控txtContent元素的變化
        for i in range(15):  # 最多等待15秒
            time.sleep(1)

            txt_content = driver.execute_script("""
                var el = document.getElementById('txtContent');
                if (el) {
                    return {
                        exists: true,
                        innerHTML: el.innerHTML.substring(0, 200),
                        innerText: el.innerText.substring(0, 200),
                        childNodes: el.childNodes.length,
                        textLength: (el.innerText || '').length
                    };
                }
                return { exists: false };
            """)

            print(f"\n第{i + 1}秒檢查:")
            print(f"  txtContent存在: {txt_content['exists']}")
            if txt_content['exists']:
                print(f"  子節點數: {txt_content['childNodes']}")
                print(f"  文本長度: {txt_content['textLength']}")
                print(f"  內容預覽: {txt_content['innerText'][:50]}...")

                # 如果找到實際內容
                if txt_content['textLength'] > 500 and '葉洵' in txt_content['innerText']:
                    print("\n✓ 找到小說內容！")
                    full_content = driver.execute_script("""
                        var el = document.getElementById('txtContent');
                        return el ? el.innerText : '';
                    """)

                    # 保存內容
                    with open('success_content.txt', 'w', encoding='utf-8') as f:
                        f.write(full_content)
                    print("內容已保存到 success_content.txt")
                    return full_content

        # 階段3：嘗試手動觸發內容加載
        print("\n=== 階段3：嘗試手動觸發加載 ===")

        if txt_url:
            # 嘗試手動fetch內容
            fetch_result = driver.execute_script(f"""
                return fetch('{txt_url}')
                    .then(response => response.text())
                    .then(data => {{
                        console.log('Fetched data:', data);

                        // 檢查是否是_txt_call格式
                        if (data.startsWith('_txt_call(')) {{
                            // 嘗試提取內容
                            var match = data.match(/_txt_call\\("(.+)"\\)/);
                            if (match) {{
                                return {{
                                    type: '_txt_call',
                                    rawData: data.substring(0, 500),
                                    extractedData: match[1].substring(0, 500)
                                }};
                            }}
                        }}

                        return {{
                            type: 'unknown',
                            data: data.substring(0, 500)
                        }};
                    }})
                    .catch(error => {{
                        return {{
                            error: true,
                            message: error.toString()
                        }};
                    }});
            """)

            print(f"Fetch結果: {json.dumps(fetch_result, ensure_ascii=False, indent=2)}")

        # 階段4：檢查網絡請求
        print("\n=== 階段4：檢查網絡請求 ===")

        # 獲取性能日誌
        logs = driver.get_log('performance')
        txt_requests = []

        for log in logs:
            message = json.loads(log['message'])
            method = message.get('message', {}).get('method', '')

            if method == 'Network.responseReceived':
                response = message['message']['params']['response']
                url = response.get('url', '')
                if '.txt' in url or 'txt.php' in url:
                    txt_requests.append({
                        'url': url,
                        'status': response.get('status'),
                        'mimeType': response.get('mimeType')
                    })

        if txt_requests:
            print("找到的txt請求:")
            for req in txt_requests:
                print(f"  URL: {req['url']}")
                print(f"  狀態: {req['status']}, 類型: {req['mimeType']}")

        # 階段5：最後的嘗試
        print("\n=== 階段5：最後嘗試 ===")

        # 嘗試不同的等待策略
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        # 再次檢查所有可能的內容容器
        final_check = driver.execute_script("""
            var possibleContainers = [
                document.getElementById('txtContent'),
                document.getElementById('content'),
                document.getElementById('chaptercontent'),
                document.querySelector('.readcontent'),
                document.querySelector('.read-content'),
                document.querySelector('.novel-content')
            ];

            var results = [];
            for (var i = 0; i < possibleContainers.length; i++) {
                var container = possibleContainers[i];
                if (container) {
                    var text = container.innerText || container.textContent || '';
                    results.push({
                        selector: container.id || container.className,
                        textLength: text.length,
                        preview: text.substring(0, 100),
                        hasChineseContent: /[\u4e00-\u9fa5]/.test(text),
                        hasNovelKeywords: /葉洵|秦王|貞武/.test(text)
                    });
                }
            }
            return results;
        """)

        print("最終檢查結果:")
        for result in final_check:
            print(f"\n容器: {result['selector']}")
            print(f"  文本長度: {result['textLength']}")
            print(f"  包含中文: {result['hasChineseContent']}")
            print(f"  包含小說關鍵詞: {result['hasNovelKeywords']}")
            print(f"  預覽: {result['preview']}")

        # 保存完整的調試信息
        driver.save_screenshot('debug_final_screenshot.png')
        with open('debug_final_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)

        print("\n調試信息已保存到:")
        print("  - debug_final_screenshot.png")
        print("  - debug_final_page.html")

        # 獲取控制台日誌
        browser_logs = driver.get_log('browser')
        if browser_logs:
            with open('debug_console_logs.txt', 'w', encoding='utf-8') as f:
                for log in browser_logs:
                    f.write(f"{log['level']}: {log['message']}\n")
            print("  - debug_console_logs.txt")

    except Exception as e:
        print(f"測試過程中出錯: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\n按Enter鍵關閉瀏覽器...")
        driver.quit()


if __name__ == "__main__":
    test_zashuwu_content()