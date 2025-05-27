#!/usr/bin/env python3
"""
智能內容區域定位工具
幫助精確定位小說網站的內容區域
"""

import os
import json
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64


class ContentLocator:
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.content_rules = {}
        self._setup_driver()

    def _setup_driver(self):
        """設置瀏覽器"""
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        self.driver = webdriver.Firefox(options=options)

    def analyze_page(self, url):
        """分析頁面結構"""
        print(f"\n分析頁面: {url}")
        self.driver.get(url)
        time.sleep(3)

        # 收集所有可能的內容區域
        candidates = []

        # 1. 通過類名和ID查找
        selectors = [
            # 常見的內容選擇器
            ("div[class*='content']", "class-content"),
            ("div[id*='content']", "id-content"),
            ("div[class*='chapter']", "class-chapter"),
            ("div[class*='article']", "class-article"),
            ("div[class*='text']", "class-text"),
            ("div[class*='read']", "class-read"),
            ("div[class*='novel']", "class-novel"),
            ("article", "tag-article"),
            ("main", "tag-main"),

            # 中文網站常見
            ("div[class*='正文']", "class-正文"),
            ("div[class*='内容']", "class-内容"),
            ("div[class*='章节']", "class-章节"),
        ]

        for selector, name in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for idx, elem in enumerate(elements):
                try:
                    # 獲取元素信息
                    rect = elem.rect
                    text = elem.text[:200] if elem.text else ""
                    html = elem.get_attribute('outerHTML')[:500]

                    # 計算文字密度
                    text_length = len(elem.text) if elem.text else 0
                    chinese_chars = sum(1 for c in elem.text if '\u4e00' <= c <= '\u9fff') if elem.text else 0

                    if rect['width'] > 200 and rect['height'] > 100 and text_length > 50:
                        candidates.append({
                            'selector': f"{selector}:nth-of-type({idx + 1})" if len(elements) > 1 else selector,
                            'name': name,
                            'rect': rect,
                            'text_length': text_length,
                            'chinese_chars': chinese_chars,
                            'density': chinese_chars / text_length if text_length > 0 else 0,
                            'preview': text,
                            'element': elem
                        })
                except:
                    continue

        # 2. 通過文本特徵查找
        all_divs = self.driver.find_elements(By.TAG_NAME, "div")
        for div in all_divs:
            try:
                text = div.text
                if not text or len(text) < 100:
                    continue

                # 檢查是否包含小說特徵
                chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                density = chinese_chars / len(text)

                # 高中文密度且包含標點符號
                if density > 0.5 and any(p in text for p in ['。', '！', '？', '，']):
                    rect = div.rect
                    if rect['width'] > 300 and rect['height'] > 200:
                        # 獲取唯一選擇器
                        class_name = div.get_attribute('class')
                        id_name = div.get_attribute('id')

                        selector = None
                        if id_name:
                            selector = f"#{id_name}"
                        elif class_name:
                            selector = f"div.{class_name.split()[0]}"

                        if selector and not any(c['selector'] == selector for c in candidates):
                            candidates.append({
                                'selector': selector,
                                'name': 'text-feature',
                                'rect': rect,
                                'text_length': len(text),
                                'chinese_chars': chinese_chars,
                                'density': density,
                                'preview': text[:200],
                                'element': div
                            })
            except:
                continue

        # 排序候選區域
        candidates.sort(key=lambda x: x['chinese_chars'], reverse=True)

        return candidates[:10]  # 返回前10個候選

    def visualize_candidates(self, url, candidates):
        """可視化候選區域"""
        # 截取整頁
        screenshot = self.driver.get_screenshot_as_png()
        img = Image.open(BytesIO(screenshot))
        draw = ImageDraw.Draw(img)

        # 標記每個候選區域
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'cyan', 'magenta', 'lime']

        for idx, candidate in enumerate(candidates):
            rect = candidate['rect']
            color = colors[idx % len(colors)]

            # 畫框
            draw.rectangle(
                [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']],
                outline=color,
                width=3
            )

            # 標註編號
            draw.text(
                (rect['x'] + 5, rect['y'] + 5),
                f"#{idx + 1}",
                fill=color
            )

        # 保存標記後的圖片
        output_path = f"content_analysis_{urlparse(url).netloc}.png"
        img.save(output_path)
        print(f"\n已保存分析圖片: {output_path}")

        return output_path

    def interactive_select(self, candidates):
        """互動式選擇最佳內容區域"""
        print("\n=== 候選內容區域 ===")
        for idx, candidate in enumerate(candidates):
            print(f"\n[{idx + 1}] {candidate['name']}")
            print(f"   選擇器: {candidate['selector']}")
            print(f"   尺寸: {candidate['rect']['width']}x{candidate['rect']['height']}")
            print(f"   文字數: {candidate['text_length']} (中文: {candidate['chinese_chars']})")
            print(f"   中文密度: {candidate['density']:.2%}")
            print(f"   預覽: {candidate['preview'][:100]}...")

        # 自動推薦
        if candidates:
            best = max(candidates, key=lambda x: x['chinese_chars'] * x['density'])
            best_idx = candidates.index(best)
            print(f"\n推薦選擇: [{best_idx + 1}] (中文字數最多且密度最高)")

        # 用戶選擇
        while True:
            choice = input("\n請選擇最佳內容區域 (輸入編號，或 'a' 自動選擇，'s' 截圖查看): ").strip()

            if choice.lower() == 'a':
                return best_idx
            elif choice.lower() == 's':
                # 截圖當前選中的區域
                self.screenshot_candidates(candidates)
            elif choice.isdigit() and 1 <= int(choice) <= len(candidates):
                return int(choice) - 1
            else:
                print("無效輸入，請重試")

    def screenshot_candidates(self, candidates):
        """截圖各個候選區域"""
        output_dir = "candidate_screenshots"
        os.makedirs(output_dir, exist_ok=True)

        for idx, candidate in enumerate(candidates):
            try:
                elem = candidate['element']
                screenshot = elem.screenshot_as_png
                img = Image.open(BytesIO(screenshot))

                filename = f"{output_dir}/candidate_{idx + 1}_{candidate['name']}.png"
                img.save(filename)
                print(f"已保存: {filename}")
            except:
                print(f"無法截圖候選 {idx + 1}")

    def test_selector(self, url, selector):
        """測試選擇器效果"""
        self.driver.get(url)
        time.sleep(2)

        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, selector)

            # 截圖
            screenshot = elem.screenshot_as_png
            img = Image.open(BytesIO(screenshot))

            # 獲取文本
            text = elem.text

            chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

            print("\n選擇器測試成功！")
            print(f"內容預覽: {text[:500]}...")
            print(f"總字數: {len(text)}")
            print(f"中文字數: {chinese_count}")

            # 保存截圖
            test_path = f"selector_test_{urlparse(url).netloc}.png"
            img.save(test_path)
            print(f"截圖已保存: {test_path}")

            return True

        except Exception as e:
            print(f"\n選擇器測試失敗: {e}")
            return False

    def generate_rules(self, url, selector):
        """生成爬取規則"""
        domain = urlparse(url).netloc

        rules = {
            'domain': domain,
            'content_selector': selector,
            'wait_time': 3,
            'encoding': 'auto',
            'javascript_render': True,
            'created_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # 保存規則
        rules_file = f"content_rules_{domain}.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        print(f"\n規則已保存: {rules_file}")

        return rules

    def create_targeted_crawler(self, rules_file):
        """生成針對性的爬蟲代碼"""
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = json.load(f)

        crawler_code = f'''#!/usr/bin/env python3
"""
針對 {rules['domain']} 的定制爬蟲
自動生成於: {rules['created_time']}
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

def crawl_content(url, headless=True):
    """爬取指定URL的內容"""
    options = Options()
    if headless:
        options.add_argument('--headless')

    driver = webdriver.Firefox(options=options)

    try:
        driver.get(url)
        time.sleep({rules['wait_time']})

        # 使用定制的選擇器
        content_elem = driver.find_element(By.CSS_SELECTOR, "{rules['content_selector']}")

        # 獲取文本
        content = content_elem.text

        # 截圖（可選）
        screenshot = content_elem.screenshot_as_png

        return content, screenshot

    finally:
        driver.quit()

# 使用示例
if __name__ == "__main__":
    url = "YOUR_URL_HERE"
    content, screenshot = crawl_content(url)
    print(f"獲取內容: {{len(content)}} 字")
'''

        output_file = f"crawler_{rules['domain']}.py"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(crawler_code)

        print(f"定制爬蟲已生成: {output_file}")

        return output_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description='內容區域定位工具')
    parser.add_argument('--url', required=True, help='要分析的網頁URL')
    parser.add_argument('--test-selector', help='測試指定的CSS選擇器')
    parser.add_argument('--auto', action='store_true', help='自動選擇最佳區域')
    parser.add_argument('--headless', action='store_true', help='無頭模式')

    args = parser.parse_args()

    # 創建定位器
    locator = ContentLocator(headless=args.headless)

    try:
        if args.test_selector:
            # 測試模式
            locator.test_selector(args.url, args.test_selector)
        else:
            # 分析模式
            print("正在分析頁面結構...")
            candidates = locator.analyze_page(args.url)

            if not candidates:
                print("未找到合適的內容區域")
                return

            # 可視化
            locator.visualize_candidates(args.url, candidates)

            # 選擇最佳區域
            if args.auto:
                best_idx = 0  # 自動選擇第一個
            else:
                best_idx = locator.interactive_select(candidates)

            best_selector = candidates[best_idx]['selector']
            print(f"\n已選擇: {best_selector}")

            # 測試選擇器
            if locator.test_selector(args.url, best_selector):
                # 生成規則
                rules = locator.generate_rules(args.url, best_selector)

                # 生成爬蟲
                locator.create_targeted_crawler(f"content_rules_{rules['domain']}.json")

                print("\n=== 下一步 ===")
                print(f"1. 使用生成的選擇器: {best_selector}")
                print(f"2. 或使用生成的爬蟲: crawler_{rules['domain']}.py")

    finally:
        locator.driver.quit()


if __name__ == "__main__":
    main()