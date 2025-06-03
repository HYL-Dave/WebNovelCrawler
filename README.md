# WebNovelCrawler 使用指南

## 專案簡介

WebNovelCrawler 是一組用於抓取線上中文小說內容的 **工具腳本集合**，
涵蓋多種反爬取策略與技術棧，方便依需求彈性選擇：

1. **Selenium (Chromium)** – 標準瀏覽器自動化，支援隨機 UA、無頭模式。
2. **Playwright + Stealth** – 更佳的反自動化偵測能力，可繞過 Cloudflare、Canvas 等指紋。
3. **純 HTTP 反向工程** – 直接呼叫 `initTxt()` 等 API，省去瀏覽器開銷。
4. **分頁章節處理** – 自動偵測 `(1/3)`、`第 1 頁 / 共 3 頁` 等格式並合併內容。
5. **精準內容截圖 + GPT-OCR / OpenAI 校對** – 針對文字轉圖片、防複製站點仍可獲取乾淨文字。

> 本專案僅用於學術研究與個人學習，切勿用於任何侵犯著作權或違反網站條款之行為。

---

## 依賴安裝

### 1. Python 套件

```bash
# 建議使用 Python >= 3.10
pip install -r requirements.txt

# 若未提供 requirements.txt，可手動安裝常用套件
pip install selenium webdriver-manager beautifulsoup4 requests \
            playwright playwright-stealth pillow pandas tqdm

# （可選）OCR／OpenAI 功能
pip install easyocr pytesseract openai

# 完成後初次安裝 Playwright 執行以下指令下載瀏覽器：
npx playwright install chromium
```

### 2. 瀏覽器驅動

腳本已透過 **`webdriver-manager`** 自動下載對應版本的 ChromeDriver / GeckoDriver，
無須手動放置，只須確保本機已安裝 **Google Chrome** 或 **Firefox**。

---

## 目錄結構

```
├── selenium_scraper.py           # Chromium 版通用爬蟲
├── paginated_scraper.py          # 具分頁偵測與合併邏輯
├── novel_crawler_playwright.py   # Playwright + stealth 版本
├── http_utils.py                 # 純 HTTP + 代理池 + initTxt 抓取工具
├── precise_content_crawler.py    # 截圖分塊 + GPT-OCR / 校對流程
├── advanced_decoder.py           # 編碼／標點修復輔助
├── *.csv                         # 範例章節 URL 清單
└── proxies.txt                   # （自行建立）代理池列表
```

---

## 快速開始

### 1. Selenium 基本爬蟲

```bash
# 僅抓取前三章驗證流程
python selenium_scraper.py m1.csv --test --headless

# 全量抓取並輸出至資料夾 novels/
python selenium_scraper.py m1.csv --all --output novels

# 指定章節範圍（第 10-20 章，索引由 0 起算）
python selenium_scraper.py m1.csv --start 9 --end 19 --output novels_part
```

### 2. Playwright + Stealth

```bash
python novel_crawler_playwright.py --csv m1.csv \
       --output novels_playwright --headless --proxy-file proxies.txt
```

### 3. 分頁章節網站

```bash
# 自動偵測 (1/3)、(2/3)… 並合併為單檔
python paginated_scraper.py novel543.csv --output novel543_merged
```

### 4. 純 HTTP initTxt 抓取

```bash
python - <<'PY'
from http_utils import extract_init_txt_url_http, fetch_initTxt_content_http

url = "https://m.zashuwu.com/wen/2vFm/1.html"
init_url = extract_init_txt_url_http(url)
content = fetch_initTxt_content_http(init_url, referer=url)
print(content[:300])
PY
```

### 5. 精準截圖 + GPT-OCR

```bash
export OPENAI_API_KEY="你的 API Key"

python precise_content_crawler.py \
       --csv m1.csv \
       --rules content_rules_m.zashuwu.com.json \
       --openai --gptocr --ocr_model o4-mini --proofread_model o4-mini \
       --chunk_height 760 --overlap 20 \
       --output precise_output
```

---

## 通用 CLI 參數

| 參數               | 說明                              |
|--------------------|-----------------------------------|
| `--csv`            | 章節列表 CSV，第一欄標題、第二欄 URL |
| `--output`         | 文字檔輸出資料夾 (預設與腳本同名)   |
| `--headless`       | 啟用無頭模式                       |
| `--test`           | 僅抓取第一筆，快速驗證流程          |
| `--start / --end`  | 章節索引範圍，從 0 起算            |
| `--delay`          | 每章節隨機延遲秒數 (人類化)         |
| `--proxy-file`     | 指定 proxies.txt 隨機抽取代理       |

部分腳本還有進階選項，例如 `--openai-key`、`--use-ocr`、`--chunk_height`…，
可透過 `-h / --help` 查看完整說明。

---

## 代理池 (可選)

在專案根目錄新增 `proxies.txt`，每行一筆，支援帳密與 `#` 註解：

```text
# http 和 https 皆會自動注入
http://user:pass@1.2.3.4:7890
http://98.76.54.32:3128
```

所有支援代理的腳本均可加上 `--proxy-file proxies.txt`，
會自動隨機挑選並注入到瀏覽器啟動參數或 `requests`。若需提前驗證可執行：

```python
from http_utils import load_proxies, validate_proxies
print(validate_proxies(load_proxies()))
```

---

## 除錯與日誌

1. 每個爬蟲腳本都會於輸出資料夾生成 `*.log` 檔，可即時追蹤進度。
2. 失敗時自動保留 `screenshot.png` / `page.html` 方便排查。
3. 建議先在 **非無頭模式** 下跑 `--test`，觀察網頁是否需要額外等待或操作。

---

## 常見問題

### ChromeDriver / GeckoDriver 版本不符

> `SessionNotCreatedException: This version of ChromeDriver only supports Chrome version XX`

執行 `pip install --upgrade webdriver-manager` 即會自動重新下載對應版本。

### 被網站判定為機器人

- 啟用 Playwright + Stealth (`novel_crawler_playwright.py`)
- 隨機 UA / 延遲 (`--delay 5`)
- 使用代理池
- 模擬捲動、隨機點擊 (`selenium_scraper.py` 中可擴充)

### 內容仍為加密 / 圖片

1. 嘗試 `http_utils.py` 直接抓取 `initTxt()` 純文本
2. 啟用 `precise_content_crawler.py` 的 OCR 流程
3. 最後再考慮手動分析 JS 加密邏輯

---

## 法律聲明

本專案程式碼與範例僅供技術研究與教學示範。

使用者應遵守目標網站之 **使用條款 (Terms of Service)** 與 **robots.txt**，
並確認爬取、下載、儲存之內容未侵犯任何著作權或違反當地法律。

作者對任何違法、侵權或造成伺服器負載之行為不負任何責任。
