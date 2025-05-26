# 綜合小說爬蟲使用指南

## 功能特點

這個綜合版爬蟲結合了多種技術來解決不同的反爬機制：

1. **Firefox瀏覽器** - 避免Chromium檢測
2. **改進解碼器** - 修復標點符號和換行問題
3. **OCR文字識別** - 提取圖片中的文字
4. **多重提取策略** - 綜合多種方法確保成功率

## 安裝依賴

### 基本依賴
```bash
pip install selenium webdriver-manager beautifulsoup4 requests Pillow
```

### OCR依賴（可選）
```bash
# 選項1：EasyOCR（推薦，精度更高）
pip install easyocr

# 選項2：Tesseract
pip install pytesseract
# Windows: 下載安裝包 https://github.com/UB-Mannheim/tesseract/wiki
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-chi-tra
# macOS: brew install tesseract
```

## 使用方法

### 1. 基本使用

```bash
# 測試模式（只爬第一個URL）
python comprehensive_novel_crawler.py --csv m1.csv --test

# 正常模式
python comprehensive_novel_crawler.py --csv m1.csv --output novel_output

# 無頭模式
python comprehensive_novel_crawler.py --csv m1.csv --headless
```

### 2. 啟用OCR功能

```bash
# 啟用OCR識別圖片文字
python comprehensive_novel_crawler.py --csv m1.csv --use-ocr --test

# OCR + 無頭模式
python comprehensive_novel_crawler.py --csv m1.csv --use-ocr --headless
```

### 3. 使用代理

```bash
# 創建代理文件 proxies.txt
echo "http://127.0.0.1:8080" > proxies.txt
echo "http://user:pass@proxy.example.com:3128" >> proxies.txt

# 使用代理
python comprehensive_novel_crawler.py --csv m1.csv --proxy-file proxies.txt
```

### 4. 指定範圍

```bash
# 爬取第10-20章
python comprehensive_novel_crawler.py --csv m1.csv --start 9 --end 20

# 調整延遲時間
python comprehensive_novel_crawler.py --csv m1.csv --delay 8
```

### 5. 單獨使用解碼器

```bash
# 解碼已下載的加密文件
python improved_decoder.py
```

### 6. 單獨使用Firefox爬蟲

```bash
# 只使用Firefox，不使用OCR和解碼器
python novel_crawler_firefox.py --csv m1.csv --test
```

## 功能對比

| 功能 | Chromium版 | Firefox版 | 綜合版 |
|------|------------|-----------|--------|
| 反檢測 | 一般 | 較好 | 最好 |
| JavaScript解密 | 支持 | 支持 | 支持 |
| 圖片文字OCR | 不支持 | 不支持 | 支持 |
| 改進解碼器 | 不支持 | 不支持 | 支持 |
| 多重策略 | 否 | 否 | 是 |

## 常見問題和解決方案

### 1. 標點符號丟失問題

**問題**: 解碼後的文本缺少標點符號

**解決**: 使用改進的解碼器，它包含了完整的標點符號映射：

```python
# 改進的標點符號映射
punctuation_map = {
    'ff0c': '，',    # 中文逗號
    '3002': '。',    # 中文句號  
    'ff1f': '？',    # 中文問號
    'ff01': '！',    # 中文感嘆號
    # ... 更多映射
}
```

### 2. 換行問題

**問題**: 文本換行混亂

**解決**: 使用智能換行修復：

```python
def fix_line_breaks(self, text):
    # 檢測章節標題
    # 處理句子結束
    # 合併不完整的句子
```

### 3. 瀏覽器檢測問題

**問題**: 網站檢測到自動化瀏覽器

**解決方案**:
- 使用Firefox而不是Chromium
- 設置反檢測選項
- 模擬人類行為（滾動、隨機延遲）
- 使用代理IP

### 4. 圖片文字問題

**問題**: 網頁中的文字是圖片形式

**解決方案**:
- 啟用OCR功能 `--use-ocr`
- 使用EasyOCR或Tesseract
- 自動檢測和下載圖片
- 提取Canvas內容

### 5. 內容提取失敗

**解決策略** (按優先級):
1. JavaScript解密提取
2. 直接文字提取  
3. OCR圖片提取
4. 原始源碼分析

### 6. 性能優化

```bash
# 減少圖片加載
firefox_options.set_preference('permissions.default.image', 2)

# 使用多線程（小心不要過度並發）
# 設置合適的延遲時間
--delay 5

# 使用無頭模式提高速度
--headless
```

## 調試技巧

### 1. 啟用調試模式

```bash
# 不使用無頭模式，可以看到瀏覽器操作
python comprehensive_novel_crawler.py --csv m1.csv --test

# 檢查生成的調試文件
ls debug_comprehensive/
```

### 2. 檢查調試輸出

失敗時會自動生成：
- `screenshot_*.png` - 頁面截圖
- `source_*.html` - 頁面源碼  
- `info_*.txt` - 詳細信息

### 3. 測試單個URL

```python
# 創建測試CSV文件
echo "章節,鏈接" > test.csv
echo "1,https://example.com/1.html" >> test.csv

# 測試
python comprehensive_novel_crawler.py --csv test.csv --test --use-ocr
```

## 進階配置

### 1. 自定義User-Agent

```python
firefox_options.set_preference("general.useragent.override", 
    "自定義User-Agent字符串")
```

### 2. 自定義標點符號映射

編輯 `improved_decoder.py` 中的 `punctuation_map`

### 3. 自定義廣告過濾

編輯清理函數中的 `ad_patterns`

### 4. 配置OCR語言

```python
# EasyOCR
reader = easyocr.Reader(['ch_tra', 'ch_sim', 'en', 'ja'])

# Tesseract  
text = pytesseract.image_to_string(image, lang='chi_tra+chi_sim+eng+jpn')
```

## 最佳實踐

1. **先測試單個URL**: 使用 `--test` 參數
2. **逐步啟用功能**: 先測試基本功能，再啟用OCR
3. **合理設置延遲**: 避免過快被檢測
4. **使用代理**: 對於有IP限制的網站
5. **保存進度**: 檢查 `success.log` 和 `errors.log`
6. **定期清理**: 刪除調試文件節省空間

## 故障排除

### 1. Firefox啟動失敗

```bash
# 更新GeckoDriver
pip install --upgrade webdriver-manager

# 檢查Firefox版本
firefox --version
```

### 2. OCR識別效果差

- 嘗試不同的OCR引擎（EasyOCR vs Tesseract）
- 調整圖片預處理參數
- 檢查圖片質量和分辨率

### 3. 解碼結果不正確

- 檢查原始數據格式
- 驗證替換規則
- 手動測試部分內容

### 4. 內存使用過高

- 使用無頭模式
- 減少並發數量
- 定期重啟瀏覽器進程

## 法律聲明

請確保：
- 遵守網站的robots.txt和使用條款
- 僅用於個人學習和研究
- 尊重版權和知識產權
- 不要對服務器造成過大負載