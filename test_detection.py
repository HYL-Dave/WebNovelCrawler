"""
測試網站的反爬蟲檢測機制
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc


def test_normal_selenium():
    """測試普通Selenium"""
    print("=== 測試普通Selenium ===")

    options = Options()
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    try:
        url = "https://m.zashuwu.com/wen/2vFm/1.html"
        print(f"訪問: {url}")
        driver.get(url)

        time.sleep(5)

        current_url = driver.current_url
        print(f"當前URL: {current_url}")
        print(f"頁面標題: {driver.title}")

        # 檢查是否被重定向
        if current_url != url:
            print("❌ 檢測到重定向！可能被識別為機器人")
        else:
            print("✓ 沒有重定向")

        # 檢查webdriver屬性
        is_webdriver = driver.execute_script("return navigator.webdriver")
        print(f"navigator.webdriver = {is_webdriver}")

        # 檢查內容
        content = driver.execute_script("""
            var txt = document.getElementById('txtContent');
            if (txt) {
                return {
                    exists: true,
                    length: txt.innerText.length,
                    preview: txt.innerText.substring(0, 100)
                };
            }
            return { exists: false };
        """)

        print(f"txtContent存在: {content['exists']}")
        if content['exists']:
            print(f"內容長度: {content['length']}")
            print(f"內容預覽: {content.get('preview', 'N/A')}")

        # 保存截圖
        driver.save_screenshot("test_normal_selenium.png")
        print("截圖已保存: test_normal_selenium.png")

    finally:
        driver.quit()
        print()


def test_undetected_chrome():
    """測試undetected-chromedriver"""
    print("=== 測試Undetected Chrome ===")

    options = uc.ChromeOptions()
    options.add_argument('--window-size=1920,1080')

    driver = uc.Chrome(options=options)

    try:
        url = "https://m.zashuwu.com/wen/2vFm/1.html"
        print(f"訪問: {url}")
        driver.get(url)

        time.sleep(5)

        current_url = driver.current_url
        print(f"當前URL: {current_url}")
        print(f"頁面標題: {driver.title}")

        if current_url != url:
            print("❌ 檢測到重定向！")
        else:
            print("✓ 沒有重定向")

        # 檢查webdriver屬性
        is_webdriver = driver.execute_script("return navigator.webdriver")
        print(f"navigator.webdriver = {is_webdriver}")

        # 等待更長時間
        print("等待10秒讓內容加載...")
        time.sleep(10)

        # 檢查內容
        content = driver.execute_script("""
            var txt = document.getElementById('txtContent');
            if (txt) {
                return {
                    exists: true,
                    length: txt.innerText.length,
                    preview: txt.innerText.substring(0, 100)
                };
            }
            return { exists: false };
        """)

        print(f"txtContent存在: {content['exists']}")
        if content['exists']:
            print(f"內容長度: {content['length']}")
            print(f"內容預覽: {content.get('preview', 'N/A')}")

        # 保存截圖
        driver.save_screenshot("test_undetected_chrome.png")
        print("截圖已保存: test_undetected_chrome.png")

    finally:
        driver.quit()
        print()


def test_manual_comparison():
    """手動比較測試"""
    print("=== 手動比較測試 ===")
    print("請手動在瀏覽器中打開以下URL:")
    print("https://m.zashuwu.com/wen/2vFm/1.html")
    print("\n觀察以下內容:")
    print("1. 頁面是否正常顯示小說內容？")
    print("2. URL是否保持不變？")
    print("3. 是否看到《風流皇太子》的章節內容？")
    print("\n如果手動打開正常，但自動化工具不正常，")
    print("說明網站確實有反爬蟲檢測。")


def check_detection_methods():
    """檢查網站可能使用的檢測方法"""
    print("\n=== 網站可能的檢測方法 ===")

    options = Options()
    driver = webdriver.Chrome(options=options)

    try:
        # 檢查各種自動化特徵
        detection_results = driver.execute_script("""
            return {
                webdriver: navigator.webdriver,
                chrome: window.chrome ? 'exists' : 'not exists',
                chromeDriver: window.chrome && window.chrome.runtime ? 'runtime exists' : 'no runtime',
                permissions: navigator.permissions ? 'exists' : 'not exists',
                plugins: navigator.plugins.length,
                languages: navigator.languages,
                platform: navigator.platform,
                userAgent: navigator.userAgent,
                vendor: navigator.vendor
            };
        """)

        print("瀏覽器特徵:")
        for key, value in detection_results.items():
            print(f"  {key}: {value}")

    finally:
        driver.quit()


if __name__ == "__main__":
    print("開始測試網站反爬蟲檢測...\n")

    # 測試普通Selenium
    test_normal_selenium()

    # 測試undetected-chromedriver
    try:
        test_undetected_chrome()
    except Exception as e:
        print(f"Undetected Chrome測試失敗: {e}")
        print("請確保已安裝: pip install undetected-chromedriver")

    # 檢查檢測方法
    check_detection_methods()

    # 手動比較提示
    test_manual_comparison()

    print("\n測試完成！請查看生成的截圖文件。")