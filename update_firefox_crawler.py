#!/usr/bin/env python3
import os
import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_firefox_driver(headless=True):
    """設置 Firefox 驅動，包含完整的錯誤處理"""
    
    print("正在設置 Firefox 驅動...")
    
    # 方法1: 嘗試使用 webdriver-manager 自動管理
    try:
        from webdriver_manager.firefox import GeckoDriverManager
        print("使用 webdriver-manager 自動下載 geckodriver...")
        
        options = Options()
        if headless:
            options.add_argument('--headless')
        
        # 添加更多選項以避免檢測
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference("general.useragent.override", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")
        
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        print("✓ Firefox 驅動設置成功（使用 webdriver-manager）")
        return driver
        
    except Exception as e:
        print(f"webdriver-manager 方法失敗: {e}")
        print("嘗試其他方法...")
    
    # 方法2: 嘗試直接使用系統的 geckodriver
    try:
        import subprocess
        # 檢查 geckodriver 是否在 PATH 中
        result = subprocess.run(['which', 'geckodriver'], capture_output=True, text=True)
        if result.returncode == 0:
            geckodriver_path = result.stdout.strip()
            print(f"找到系統 geckodriver: {geckodriver_path}")
            
            options = Options()
            if headless:
                options.add_argument('--headless')
            
            service = Service(geckodriver_path)
            driver = webdriver.Firefox(service=service, options=options)
            print("✓ Firefox 驅動設置成功（使用系統 geckodriver）")
            return driver
    except Exception as e:
        print(f"系統 geckodriver 方法失敗: {e}")
    
    # 方法3: 檢查常見位置
    common_paths = [
        '/usr/local/bin/geckodriver',
        '/usr/bin/geckodriver',
        os.path.expanduser('~/bin/geckodriver'),
        './geckodriver',
        '../geckodriver'
    ]
    
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            print(f"在 {path} 找到 geckodriver")
            try:
                options = Options()
                if headless:
                    options.add_argument('--headless')
                
                service = Service(path)
                driver = webdriver.Firefox(service=service, options=options)
                print("✓ Firefox 驅動設置成功")
                return driver
            except Exception as e:
                print(f"使用 {path} 失敗: {e}")
    
    # 如果所有方法都失敗
    print("\n✗ 無法設置 Firefox 驅動")
    print("\n請確保：")
    print("1. Firefox 瀏覽器已安裝")
    print("2. geckodriver 已下載並在 PATH 中")
    print("\n安裝步驟：")
    print("1. 安裝 webdriver-manager: uv pip install webdriver-manager")
    print("2. 或手動下載 geckodriver: https://github.com/mozilla/geckodriver/releases")
    
    return None

# 測試函數
if __name__ == "__main__":
    driver = setup_firefox_driver(headless=False)
    if driver:
        try:
            print("測試訪問網頁...")
            driver.get("https://www.google.com")
            print(f"成功訪問: {driver.title}")
        finally:
            driver.quit()
    else:
        print("驅動設置失敗")
        sys.exit(1)
