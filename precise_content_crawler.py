#!/usr/bin/env python3
"""
精準內容爬蟲
只爬取和處理真正的內容區域，支持 OCR、OpenAI 與 GPT 影像分塊 OCR 校對流程

python precise_content_crawler.py \
      --csv urls.csv \
      --rules content_rules.json \
      --openai --openai-key YOUR_KEY \
      --gptocr \
      --chunk_height 760 \
      --overlap 20 \
      --min_overlap_chars 20 \
      --ocr_model o4-mini \
      --proofread_model o4-mini \
      --output precise_output_v2

这样，爬虫会先截图并保存 {序号}_chapter.png，随后按 GPT‑OCR 流程生成并保存 {序号}_chapter_gptocr.txt，即为分块 OCR 合并并校对后的最终文本，完全集成于一个脚本中。
"""

import os
import json
import time
import csv
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO
import base64
import openai
from difflib import SequenceMatcher


def split_image(image_path: str, max_height: int, overlap: int) -> list[str]:
    """Split the input image into vertically overlapping chunks."""
    img = Image.open(image_path)
    width, height = img.size
    base, _ = os.path.splitext(image_path)
    if overlap >= max_height:
        raise ValueError("overlap must be smaller than chunk_height")
    step = max_height - overlap

    chunks: list[str] = []
    top = 0
    idx = 0
    while top < height:
        bottom = min(top + max_height, height)
        tile = img.crop((0, top, width, bottom))
        chunk_path = f"{base}_chunk_{idx}.png"
        tile.save(chunk_path)
        chunks.append(chunk_path)
        idx += 1
        if bottom >= height:
            break
        top += step
    return chunks


def ocr_chunk(image_path: str, model: str) -> str:
    """Call GPT model to OCR the given image chunk via Base64 data URI (openai>=1.x)."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"
    parts = [
        {"type": "text",      "text": "请识别以下图片中的文字，并仅返回纯文本，不要额外说明："},
        {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
    ]
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": parts}],
    )
    return resp.choices[0].message.content.strip()


def merge_texts(chunks: list[str], min_overlap_chars: int) -> str:
    """Merge OCR outputs from overlapping chunks, removing duplicated overlaps."""
    merged = chunks[0]
    for text in chunks[1:]:
        sm = SequenceMatcher(None, merged, text)
        match = sm.find_longest_match(0, len(merged), 0, len(text))
        if (
            match.size >= min_overlap_chars
            and match.a + match.size == len(merged)
            and match.b == 0
        ):
            text = text[match.size:]
        merged += text
    return merged.strip()


def proofread_text(text: str, model: str = "o4-mini") -> str:
    """Use GPT to proofread OCR result, correcting typos/omissions and returning clean text."""
    prompt = (
        "你是中文文本校对助手。\n"
        "下面是一段OCR识别的中文文本，请你纠正其中的错字、漏字或标点，并仅输出校对后的正文：\n\n"
        + text
    )
    resp = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


class PreciseContentCrawler:
    def __init__(self, rules_file=None, use_ocr=False, use_openai=False, openai_key=None):
        self.rules = self._load_rules(rules_file) if rules_file else {}
        self.use_ocr = use_ocr
        self.use_openai = use_openai
        self.openai_key = openai_key
        self.driver = None

        self._setup()

    def _load_rules(self, rules_file):
        """加載內容定位規則"""
        if os.path.exists(rules_file):
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _setup(self):
        """初始化"""
        # 設置瀏覽器
        options = Options()

        # 無頭模式
        options.add_argument('-headless')

        # 設置窗口大小以確保內容完整顯示
        options.add_argument('--width=1200')
        options.add_argument('--height=800')

        # 修正: geckodriver 對 snap 包裝腳本會拋 "binary is not a Firefox executable"
        firefox_bin_env = os.getenv('FIREFOX_BINARY')
        candidate_bins = [
            firefox_bin_env,
            '/snap/firefox/current/usr/lib/firefox/firefox',
            '/usr/lib/firefox/firefox',
            '/usr/lib64/firefox/firefox',
        ]

        for bin_path in candidate_bins:
            if bin_path and os.path.isfile(bin_path) and os.access(bin_path, os.X_OK):
                options.binary_location = bin_path
                break

        self.driver = webdriver.Firefox(options=options)

        # 設置 OCR
        if self.use_ocr:
            try:
                import easyocr
                self.ocr_reader = easyocr.Reader(['ch_sim', 'en'])
                print("✓ OCR 已啟用")
            except:
                print("✗ OCR 初始化失敗")
                self.use_ocr = False

        # 設置 OpenAI
        if self.use_openai and self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
                print("✓ OpenAI 已啟用")
            except:
                print("✗ OpenAI 初始化失敗")
                self.use_openai = False

    def get_content_selector(self, url):
        """獲取內容選擇器"""
        domain = urlparse(url).netloc

        # 檢查是否有預定義規則
        if domain in self.rules:
            return self.rules[domain].get('content_selector')

        # 動態檢測內容區域
        return self._detect_content_area(url)

    def _detect_content_area(self, url):
        """動態檢測內容區域"""
        self.driver.get(url)
        time.sleep(2)

        # 候選選擇器及其優先級
        selectors = [
            # 精確ID選擇器
            "#content", "#chaptercontent", "#chapter-content",
            "#article-content", "#text-content", "#novel-content",

            # 精確類選擇器
            ".content", ".chapter-content", ".chaptercontent",
            ".article-content", ".text-content", ".novel-content",
            ".read-content", ".readcontent",

            # 屬性選擇器
            "[class*='content'][class*='chapter']",
            "[class*='content'][class*='text']",
            "[id*='content'][id*='chapter']",

            # 語義標籤
            "article", "main",

            # 組合選擇器
            "div.content > div", "div#content > div",
            "div[class*='read'] div[class*='content']"
        ]

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    # 檢查元素是否合適
                    text = elem.text
                    if not text or len(text) < 100:
                        continue

                    # 檢查中文比例
                    chinese_ratio = sum(1 for c in text if '\u4e00' <= c <= '\u9fff') / len(text)
                    if chinese_ratio > 0.3:  # 至少30%中文
                        rect = elem.rect
                        if rect['width'] > 300 and rect['height'] > 200:
                            print(f"  自動檢測到內容區域: {selector}")
                            return selector
            except:
                continue

        # 如果都失敗，返回body
        print("  警告：未找到特定內容區域，將使用整個頁面")
        return "body"

    def capture_content_only(self, url):
        """只截圖內容區域"""
        print(f"\n處理: {url}")

        # 訪問頁面
        self.driver.get(url)

        # 獲取內容選擇器
        selector = self.get_content_selector(url)

        # 等待內容加載
        try:
            wait = WebDriverWait(self.driver, 10)
            content_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except:
            print("  錯誤：內容加載超時")
            return None, None

        # 滾動到內容區域
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", content_elem)
        time.sleep(1)

        # 獲取內容
        content_text = content_elem.text

        # 截圖內容區域
        try:
            # 方法1：直接截圖元素
            content_screenshot = content_elem.screenshot_as_png
            content_image = Image.open(BytesIO(content_screenshot))

            print(f"  內容區域大小: {content_image.size}")

        except:
            # 方法2：截取指定區域
            rect = content_elem.rect
            full_screenshot = self.driver.get_screenshot_as_png()
            full_image = Image.open(BytesIO(full_screenshot))

            # 裁剪內容區域
            left = max(0, rect['x'])
            top = max(0, rect['y'])
            right = min(full_image.width, rect['x'] + rect['width'])
            bottom = min(full_image.height, rect['y'] + rect['height'])

            content_image = full_image.crop((left, top, right, bottom))

        return content_text, content_image

    def process_with_ocr(self, image):
        """使用 OCR 處理圖片"""
        if not self.use_ocr or not self.ocr_reader:
            return ""

        try:
            # 轉換為numpy數組
            import numpy as np
            img_array = np.array(image)

            # OCR識別
            results = self.ocr_reader.readtext(img_array)

            # 按位置排序（從上到下，從左到右）
            results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))

            # 組合文本
            lines = []
            current_line = []
            last_y = -1

            for bbox, text, conf in results:
                if conf < 0.5:  # 置信度過低
                    continue

                y = bbox[0][1]

                # 判斷是否換行
                if last_y != -1 and abs(y - last_y) > 20:
                    if current_line:
                        lines.append(''.join(current_line))
                    current_line = [text]
                else:
                    current_line.append(text)

                last_y = y

            if current_line:
                lines.append(''.join(current_line))

            return '\n'.join(lines)

        except Exception as e:
            print(f"  OCR處理失敗: {e}")
            return ""

    def process_with_openai(self, image, text_preview=""):
        """使用 OpenAI 處理內容"""
        if not self.use_openai or not self.openai_client:
            return None

        try:
            # 優化圖片大小
            if image.width > 1600:
                ratio = 1600 / image.width
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # 轉為base64
            buffered = BytesIO()
            image.save(buffered, format="PNG", optimize=True)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            # 構建請求
            messages = [
                {
                    "role": "system",
                    "content": """你是一個小說文本提取專家。請：
1. 識別並提取圖片中的所有小說正文內容
2. 如果有些文字是圖片形式，請識別並轉為文字
3. 保持原有的段落格式
4. 忽略頁面上的廣告、導航等無關內容
5. 只輸出小說正文，不要任何解釋
6. 不需要的目錄和其他小說的連結直接忽略
7. 如果OCR後發現有缺字可以補字成完整的詞"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"請提取以下小說頁面的正文內容。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]

            # 如果有文本預覽，添加參考
            if text_preview:
                messages[1]["content"][0]["text"] += f"\n\n參考：頁面上的部分文字為：\n{text_preview[:500]}..."

            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                max_tokens=32768,
                temperature=0.3
            )
            # response = self.openai_client.chat.completions.create(
            #     model="o4-mini",
            #     messages=messages,
            # )

            return response.choices[0].message.content

        except Exception as e:
            print(f"  OpenAI處理失敗: {e}")
            return None

    def crawl_page(self, url):
        """爬取單個頁面，返回 (正文文本, 內容區域截圖)"""
        try:
            # 獲取內容區域的文本和截圖
            content_text, content_image = self.capture_content_only(url)

            if not content_image:
                return None, None

            # 統計原始文本
            original_chinese = sum(1 for c in content_text if '\u4e00' <= c <= '\u9fff') if content_text else 0
            print(f"  原始文本: {len(content_text) if content_text else 0} 字符, {original_chinese} 中文")

            # 決定處理方式
            final_content = content_text

            # 如果原始文本太少，可能有圖片文字
            if original_chinese < 500:
                print("  檢測到文字可能被圖片化")

                # 優先使用 OpenAI
                if self.use_openai:
                    print("  使用 OpenAI 提取...")
                    ai_content = self.process_with_openai(content_image, content_text)
                    if ai_content:
                        final_content = ai_content

                # 否則使用 OCR
                elif self.use_ocr:
                    print("  使用 OCR 識別...")
                    ocr_content = self.process_with_ocr(content_image)
                    if ocr_content:
                        # 合併原始文本和OCR結果
                        final_content = self._merge_contents(content_text, ocr_content)

            # 清理內容
            final_content = self._clean_content(final_content)

            # 統計最終結果
            final_chinese = sum(1 for c in final_content if '\u4e00' <= c <= '\u9fff')
            print(f"  最終內容: {len(final_content)} 字符, {final_chinese} 中文")

            return final_content, content_image

        except Exception as e:
            print(f"  處理失敗: {e}")
            return None, None

    def _merge_contents(self, text1, text2):
        """智能合併兩段內容"""
        if not text1:
            return text2
        if not text2:
            return text1

        # 簡單合併策略：如果text2包含text1中沒有的大量中文，則合併
        chinese1 = set(c for c in text1 if '\u4e00' <= c <= '\u9fff')
        chinese2 = set(c for c in text2 if '\u4e00' <= c <= '\u9fff')

        if len(chinese2 - chinese1) > 50:  # text2有超過50個text1沒有的中文字
            return text1 + "\n\n" + text2
        else:
            return text1

    def _clean_content(self, text):
        """清理內容"""
        if not text:
            return ""

        # 去除推薦作品、更多相關作品、章節報錯及其後續內容
        import re
        markers_pattern = r'\[推荐作品\]|\[更多相关作品\]|\[章节报错\]'
        # 只保留標記前的內容
        text = re.split(markers_pattern, text)[0]

        # 移除頭部非正文内容：只保留從「第X章」開始
        m = re.search(r'(^第[0-9零一二三四五六七八九十百千万]+[章回].*)', text, flags=re.MULTILINE)
        if m:
            text = text[m.start(1):]

        # 移除常見廣告語（僅針對單行，不跨多行）
        ad_patterns = [
            r'本章未完[^\n]*?點擊[^\n]*?下一頁',
            r'請記住[^\n]*?域名',
            r'手機[^\n]*?閱讀',
            r'最新網址',
            r'無彈窗',
            r'更新最快',
            r'本站[^\n]*?域名',

            # 新增 – 針對 m.zashuwu.com 常見插入行
            r'海量小说[^\n]*',
            r'【[^\n]*?阅读度】',
            r'记邮件[^\n]*?@[^\n]*',
            r'最新网址发邮件[^\n]*',
            r'发邮件取最新域名[^\n]*',
            r'记住[：:][^\n]*?ZASHUWU\.COM',
            r'杂书屋[：:][^\n]*',
            r'注册会员可关闭广告[^\n]*',
            r'您当前阅读进度[^\n]*',
            r'剩\s*\d+\s*章待阅[^\n]*',
            r'阅读历史[^\n]*?搜书',
        ]

        for pattern in ad_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 清理多餘空行
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        return text.strip()

    def crawl_urls(self, urls, output_dir="precise_output"):
        """批量爬取"""
        os.makedirs(output_dir, exist_ok=True)

        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n進度: {i}/{len(urls)}")

            content, image = self.crawl_page(url)

            if content and len(content) > 100:
                # 保存內容
                filename = f"{i:04d}_chapter.txt"
                filepath = os.path.join(output_dir, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                # 保存原始圖片
                image_filename = f"{i:04d}_chapter.png"
                image_path = os.path.join(output_dir, image_filename)
                image.save(image_path)

                # GPT-OCR pipeline: split image into chunks, OCR, merge and optional proofreading
                gptocr_file = None
                if getattr(self, 'gptocr', False):
                    print(f"  [GPT-OCR] processing: {image_path}")
                    chunks = split_image(image_path, self.gptocr_chunk_height, self.gptocr_overlap)
                    ocr_texts = []
                    for idx2, chunk in enumerate(chunks, 1):
                        print(f"    chunk {idx2}/{len(chunks)}: {chunk}")
                        ocr_texts.append(ocr_chunk(chunk, self.gptocr_ocr_model))
                    merged = merge_texts(ocr_texts, self.gptocr_min_overlap_chars)
                    if self.gptocr_proofread_model:
                        print(f"  [GPT-OCR] proofreading merged text with {self.gptocr_proofread_model}...")
                        merged = proofread_text(merged, self.gptocr_proofread_model)
                    merged = self._clean_content(merged)
                    gptocr_file = os.path.join(output_dir, f"{i:04d}_chapter_gptocr.txt")
                    with open(gptocr_file, 'w', encoding='utf-8') as gf:
                        gf.write(merged)
                    print(f"  ✓ GPT-OCR proofread saved to {gptocr_file}")

                results.append({
                    'index': i,
                    'url': url,
                    'status': 'success',
                    'file': filepath,
                    'image_file': image_path,
                    'gptocr_file': gptocr_file,
                    'length': len(content)
                })
                print(f"  ✓ 已保存")
            else:
                results.append({
                    'index': i,
                    'url': url,
                    'status': 'failed',
                    'reason': 'content too short'
                })
                print(f"  ✗ 內容不足")

        return results

    def __del__(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='精準內容爬蟲')
    parser.add_argument('--csv', required=True, help='URL列表CSV文件')
    parser.add_argument('--rules', help='內容定位規則文件')
    parser.add_argument('--ocr', action='store_true', help='啟用OCR')
    parser.add_argument('--openai', action='store_true', help='啟用OpenAI')
    parser.add_argument('--openai-key', help='OpenAI API Key')
    parser.add_argument('--output', default='precise_output', help='輸出目錄')
    parser.add_argument('--test', action='store_true', help='測試模式')
    parser.add_argument('--gptocr', action='store_true', help='啟用 GPT 影像分塊 OCR 與校對流程')
    parser.add_argument('--chunk_height', type=int, default=760, help='GPT OCR 圖像塊最大高度（px）')
    parser.add_argument('--overlap', type=int, default=20, help='GPT OCR 圖像塊垂直重疊（px）')
    parser.add_argument('--min_overlap_chars', type=int, default=20, help='GPT OCR 合併時最少重疊字符數量')
    parser.add_argument('--ocr_model', default='o4-mini', help='GPT OCR 模型名稱')
    parser.add_argument('--proofread_model', default='o4-mini', help='GPT 校對模型名稱（留空跳過校對）')

    args = parser.parse_args()

    # 讀取URLs
    urls = []
    with open(args.csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳過標題
        for row in reader:
            if len(row) > 1 and row[1].startswith('http'):
                urls.append(row[1].strip())

    if args.test:
        urls = urls[:3]

    print(f"準備處理 {len(urls)} 個URL")

    # 創建爬蟲
    crawler = PreciseContentCrawler(
        rules_file=args.rules,
        use_ocr=args.ocr,
        use_openai=args.openai,
        openai_key=args.openai_key
    )
    # GPT-OCR pipeline settings
    crawler.gptocr = args.gptocr
    crawler.gptocr_chunk_height = args.chunk_height
    crawler.gptocr_overlap = args.overlap
    crawler.gptocr_min_overlap_chars = args.min_overlap_chars
    crawler.gptocr_ocr_model = args.ocr_model
    crawler.gptocr_proofread_model = args.proofread_model

    # 開始爬取
    results = crawler.crawl_urls(urls, args.output)

    # 保存結果摘要
    summary_file = os.path.join(args.output, 'crawl_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n完成！結果保存在: {args.output}")


if __name__ == "__main__":
    main()