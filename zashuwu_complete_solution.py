"""
zashuwu.com 完整爬蟲解決方案
避免開發者工具檢測，直接獲取並解碼內容
"""
import requests
import json
import re
import time
import os
import csv
from urllib.parse import urljoin


class ZashuwuCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def get_chapter_content(self, url):
        """獲取章節內容"""
        try:
            # 第一步：獲取章節頁面
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            # 提取 initTxt URL
            # 支持多種格式
            patterns = [
                r'initTxt\("([^"]+)"(?:,\s*"[^"]+")?\)',
                r'initTxt\(\'([^\']+)\'(?:,\s*\'[^\']+\')?\)',
                r'loadTxt\("([^"]+)"\)',
                r'loadTxt\(\'([^\']+)\'\)'
            ]

            init_url = None
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    init_url = match.group(1)
                    break

            if not init_url:
                print(f"未找到 initTxt URL: {url}")
                return None

            # 處理相對URL
            if init_url.startswith('//'):
                init_url = 'https:' + init_url
            elif init_url.startswith('/'):
                init_url = urljoin(url, init_url)

            print(f"找到內容URL: {init_url}")

            # 第二步：獲取加密內容
            headers = self.session.headers.copy()
            headers['Referer'] = url

            txt_response = self.session.get(init_url, headers=headers, timeout=15)
            txt_response.raise_for_status()

            # 第三步：解碼內容
            decoded_content = self.decode_content(txt_response.text)

            return decoded_content

        except Exception as e:
            print(f"獲取章節失敗 {url}: {e}")
            return None

    def decode_content(self, txt_data):
        """解碼加密內容"""
        # 移除 _txt_call 包裝
        if txt_data.startswith('_txt_call(') and txt_data.endswith(')'):
            json_str = txt_data[10:-1]
        else:
            json_str = txt_data

        try:
            # 解析JSON
            data = json.loads(json_str)
            encoded_content = data.get('content', '')
            replace_rules = data.get('replace', {})

            # 解碼內容
            decoded = self.decode_hex_content(encoded_content)

            # 應用替換規則
            for old, new in replace_rules.items():
                decoded = decoded.replace(old, new)

            # 清理內容
            decoded = self.clean_content(decoded)

            return decoded

        except json.JSONDecodeError as e:
            print(f"JSON解析失敗: {e}")
            return None

    def decode_hex_content(self, hex_str):
        """解碼十六進制內容"""
        result = []

        # 分號分割
        parts = hex_str.split(';')

        for part in parts:
            if not part.strip():
                continue

            # 提取所有4位十六進制
            hex_values = re.findall(r'[0-9a-fA-F]{4}', part)

            for hex_val in hex_values:
                try:
                    # 轉換為Unicode字符
                    char = chr(int(hex_val, 16))
                    result.append(char)
                except:
                    # 忽略無法轉換的值
                    pass

        return ''.join(result)

    def clean_content(self, text):
        """清理內容"""
        if not text:
            return ""

        # 廣告模式
        ad_patterns = [
            r'.*雜書屋.*',
            r'.*杂书屋.*',
            r'.*zashuwu\.com.*',
            r'.*ZASHUWU\.COM.*',
            r'.*記郵件找地址.*',
            r'.*记邮件找地址.*',
            r'.*dz@.*',
            r'.*請記住.*',
            r'.*请记住.*',
            r'.*手機閱讀.*',
            r'.*手机阅读.*',
            r'.*最新章節.*',
            r'.*最新章节.*',
            r'.*http[s]?://.*\.com.*',
            r'^--$',
            r'^\s*$'
        ]

        # 按行清理
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 檢查是否是廣告
            is_ad = False
            for pattern in ad_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_ad = True
                    break

            if not is_ad:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def crawl_from_csv(self, csv_file, output_dir='output', start=0, end=None, delay=2):
        """從CSV文件批量爬取"""
        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        # 讀取URL列表
        urls = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 跳過表頭
            for row in reader:
                if len(row) > 1:
                    url = row[1].strip('"')
                    urls.append(url)

        # 應用範圍
        if end is None:
            end = len(urls)
        urls = urls[start:end]

        print(f"準備爬取 {len(urls)} 個章節")

        success_count = 0
        fail_count = 0

        for i, url in enumerate(urls):
            print(f"\n[{i + 1}/{len(urls)}] 爬取: {url}")

            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(start + i + 1)

            # 獲取內容
            content = self.get_chapter_content(url)

            if content:
                # 保存內容
                filename = os.path.join(output_dir, f'chapter_{chapter_num}.txt')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ 成功保存到: {filename}")
                print(f"  內容預覽: {content[:100]}...")
                success_count += 1
            else:
                print(f"✗ 爬取失敗")
                fail_count += 1
                # 保存錯誤信息
                error_file = os.path.join(output_dir, f'error_chapter_{chapter_num}.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"爬取失敗: {url}\n")

            # 延遲
            if i < len(urls) - 1:
                print(f"等待 {delay} 秒...")
                time.sleep(delay)

        print(f"\n爬取完成！成功: {success_count}, 失敗: {fail_count}")


def test_single_chapter():
    """測試單個章節"""
    crawler = ZashuwuCrawler()
    url = "https://m.zashuwu.com/wen/2vFm/1.html"

    content = crawler.get_chapter_content(url)
    if content:
        print(f"\n成功獲取內容！")
        print(f"內容長度: {len(content)}")
        print(f"\n前500字符:")
        print(content[:500])

        with open('test_chapter.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n完整內容已保存到: test_chapter.txt")
    else:
        print("獲取內容失敗")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='zashuwu.com 爬蟲')
    parser.add_argument('--test', action='store_true', help='測試模式')
    parser.add_argument('--csv', type=str, default='m1.csv', help='CSV文件路徑')
    parser.add_argument('--output', type=str, default='zashuwu_output', help='輸出目錄')
    parser.add_argument('--start', type=int, default=0, help='開始索引')
    parser.add_argument('--end', type=int, default=None, help='結束索引')
    parser.add_argument('--delay', type=float, default=2, help='延遲秒數')

    args = parser.parse_args()

    if args.test:
        test_single_chapter()
    else:
        crawler = ZashuwuCrawler()
        crawler.crawl_from_csv(
            args.csv,
            args.output,
            args.start,
            args.end,
            args.delay
        )


if __name__ == "__main__":
    main()