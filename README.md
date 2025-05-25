# Selenium爬蟲安裝指南

## 前置要求

### 1. 安裝Python依賴

```bash
pip install selenium beautifulsoup4 requests undetected-chromedriver pyautogui
```

### 2. 安裝Chrome瀏覽器

確保你的系統已安裝最新版本的Google Chrome瀏覽器。

### 3. 安裝ChromeDriver

#### 方法一：自動安裝（推薦，適用於基本Selenium爬蟲）

```bash
pip install webdriver-manager
```

然後修改代碼中的driver設置（以 `novel_crawler_selenium.py` 為例）：

```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def setup_driver(headless=False):
    """設置Chrome驅動程序（使用webdriver-manager自動管理ChromeDriver）"""
    chrome_options = Options()
    # ... 其他選項設置 ...

    # 自動下載並使用匹配版本的ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver
```

#### 方法二：手動安裝

1. 查看Chrome版本：在Chrome中訪問 `chrome://version/`
2. 下載對應版本的ChromeDriver：https://chromedriver.chromium.org/
3. 將ChromeDriver放入系統PATH中，或指定路徑

## 使用方法

### 基本使用

```bash
python3 novel_crawler_selenium.py --csv m1.csv --output wen_novel
```

### 無頭模式（不顯示瀏覽器窗口）

```bash
python3 novel_crawler_selenium.py --csv m1.csv --output wen_novel --headless
```

### 測試模式（只爬取第一個URL）

```bash
python3 novel_crawler_selenium.py --csv m1.csv --test --verbose
```

### 指定範圍爬取

```bash
# 爬取第10到20章
python3 novel_crawler_selenium.py --csv m1.csv --start 9 --end 20
```

### 調整延遲時間

```bash
# 設置5秒延遲
python3 novel_crawler_selenium.py --csv m1.csv --delay 5
```

### 隱身模式爬蟲（Stealth 反檢測模式）

無需手動安裝ChromeDriver，使用 `undetected-chromedriver` 自動匹配驅動版本。

```bash
python3 novel_crawler_stealth.py --csv m1.csv --output wen_novel_stealth --test --headless
```

### 進階隱身模式爬蟲（Advanced Stealth 繞過多種反爬技術）

```bash
python3 novel_crawler_advanced_stealth.py --csv m1.csv --output wen_novel_advanced --test
```

## 常見問題

### 1. ChromeDriver版本不匹配

錯誤信息：`selenium.common.exceptions.SessionNotCreatedException: Message: session not created: This version of ChromeDriver only supports Chrome version XX`

解決方法：下載與Chrome瀏覽器版本匹配的ChromeDriver。

### 2. 無法找到ChromeDriver

錯誤信息：`selenium.common.exceptions.WebDriverException: Message: 'chromedriver' executable needs to be in PATH`

解決方法：
- 將ChromeDriver添加到系統PATH
- 或使用webdriver-manager自動管理
- 或在代碼中指定ChromeDriver的完整路徑

### 3. 內容仍然無法解密

如果Selenium方案仍無法獲取內容，可能需要：

1. **增加等待時間**：某些網站的JavaScript解密需要更長時間
2. **模擬用戶行為**：添加滾動、點擊等動作
3. **使用其他瀏覽器**：嘗試Firefox或Edge
4. **分析網站的解密邏輯**：使用瀏覽器的開發者工具

### 4. 被網站檢測為機器人

解決方法：
- 使用隨機User-Agent
- 添加隨機延遲
- 使用代理IP
- 模擬真實用戶行為（鼠標移動、隨機點擊等）

## 調試技巧

### 1. 保存截圖

在爬取失敗時保存截圖：

```python
driver.save_screenshot('debug_screenshot.png')
```

### 2. 保存頁面源碼

```python
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
```

### 3. 使用瀏覽器開發者工具

1. 不使用無頭模式運行
2. 在程序暫停時手動檢查頁面
3. 使用F12查看網絡請求和JavaScript執行

## 進階優化

### 1. 使用多線程

```python
from concurrent.futures import ThreadPoolExecutor

def crawl_with_thread(url):
    driver = setup_driver(headless=True)
    try:
        content = crawl_novel_content_selenium(driver, url)
        return content
    finally:
        driver.quit()

# 使用線程池
with ThreadPoolExecutor(max_workers=3) as executor:
    results = executor.map(crawl_with_thread, urls)
```

### 2. 添加重試機制

```python
def crawl_with_retry(driver, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            content = crawl_novel_content_selenium(driver, url)
            if content:
                return content
        except Exception as e:
            print(f"嘗試 {attempt+1} 失敗: {e}")
            time.sleep(5)
    return None
```

### 3. 保存進度

```python
import json

def save_progress(completed_urls, progress_file='progress.json'):
    with open(progress_file, 'w') as f:
        json.dump(completed_urls, f)

def load_progress(progress_file='progress.json'):
    try:
        with open(progress_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
```

## 移動端小說內容抓取模式

針對移動端站點（如 m.zashuwu.com）使用 `initTxt(...)` 動態加載內容的頁面，本專案已新增自動提取並下載純文本的功能，無需等待頁面渲染。

### 使用 stealth 版

```bash
python3 novel_crawler_stealth.py --csv m1.csv --output wen_novel_stealth --test --headless
```

### 使用 advanced stealth 版

```bash
python3 novel_crawler_advanced_stealth.py --csv m1.csv --output wen_novel_advanced --test --headless
```

## 冒煙測試腳本

項目根目錄提供 `smoke_test_mobile_fetch.py`，用於快速對比兩種爬蟲在移動端的抓取效果：

```bash
python3 smoke_test_mobile_fetch.py \
  --url https://m.zashuwu.com/wen/2vFm/1.html \
  --timeout 30
```

## 測試腳本

本專案包含多個測試腳本，可用於檢測網站反爬機制和內容結構：

```bash
# 測試普通Selenium和undetected-chromedriver的檢測效果
python3 test_detection.py

# 檢查頁面結構以定位內容容器
python3 test_url_structure.py

# 深入測試 zashuwu.com 的內容加載邏輯
python3 test_zashuwu_advanced.py
```

## 法律聲明

請確保遵守網站的使用條款和robots.txt文件。僅用於個人學習和研究目的。