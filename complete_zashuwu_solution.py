"""
完整的 zashuwu.com 小說爬蟲解決方案
包含下載和解碼功能

python complete_zashuwu_solution.py --test
python complete_zashuwu_solution.py --csv m1.csv --output 風流皇太子 --delay 5
# 第1-20章
python complete_zashuwu_solution.py --start 0 --end 20 --delay 5

# 第21-40章
python complete_zashuwu_solution.py --start 20 --end 40 --delay 5

# 以此類推...
"""
import requests
import csv
import os
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


class ZashuwuCrawler:
    def __init__(self):
        self.session = requests.Session()
        # 使用移動端 User-Agent（更少限制）
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })

    def decode_hex_content(self, hex_str):
        """解碼十六進制內容"""
        result = []
        parts = hex_str.split(';') if ';' in hex_str else [hex_str]

        for part in parts:
            if not part.strip():
                continue

            # 只保留十六進制字符
            hex_only = re.sub(r'[^0-9a-fA-F]', '', part)

            # 每4位解碼一個字符
            for i in range(0, len(hex_only), 4):
                if i + 4 <= len(hex_only):
                    hex_code = hex_only[i:i + 4]
                    try:
                        code_point = int(hex_code, 16)

                        # 跳過無效的Unicode字符
                        if 0xD800 <= code_point <= 0xDFFF:  # 代理區
                            continue
                        if code_point > 0x10FFFF:  # 超出Unicode範圍
                            continue

                        char = chr(code_point)
                        # 再次檢查字符是否可以編碼
                        try:
                            char.encode('utf-8')
                            result.append(char)
                        except:
                            pass

                    except Exception:
                        pass

        return ''.join(result)

    def clean_content(self, text):
        """清理內容"""
        if not text:
            return ""

        # 清理廣告
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
            r'.*域名.*',
            r'.*手機閱讀.*',
            r'.*手机阅读.*',
        ]

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

    def get_chapter(self, url):
        """獲取單個章節"""
        try:
            # 步驟1：獲取章節頁面
            response = self.session.get(url, timeout=15, allow_redirects=True)

            # 檢查是否被重定向到反爬蟲頁面
            if 'FROM=bjs' in response.url:
                print(f"被檢測為機器人，等待後重試...")
                time.sleep(random.uniform(5, 10))
                response = self.session.get(url, timeout=15, allow_redirects=True)

            # 步驟2：提取 initTxt URL
            init_match = re.search(r'initTxt\s*\(\s*["\']([^"\']+)["\']\s*(?:,\s*["\'][^"\']+["\']\s*)?\)',
                                   response.text)

            if not init_match:
                return None, "未找到 initTxt URL"

            init_url = init_match.group(1)

            # 處理相對URL
            if init_url.startswith('//'):
                init_url = 'https:' + init_url
            elif init_url.startswith('/'):
                init_url = 'https://m.zashuwu.com' + init_url

            # 步驟3：獲取加密內容
            headers = self.session.headers.copy()
            headers['Referer'] = url

            txt_response = self.session.get(init_url, headers=headers, timeout=15)

            # 步驟4：解碼內容
            if txt_response.text.startswith('_txt_call('):
                # 提取內容（不使用json.loads以避免編碼問題）
                content_match = re.search(r'"content"\s*:\s*"([^"]+)"', txt_response.text, re.DOTALL)

                if not content_match:
                    return None, "無法提取加密內容"

                encoded_content = content_match.group(1)

                # 解碼
                decoded = self.decode_hex_content(encoded_content)

                # 清理
                cleaned = self.clean_content(decoded)

                return cleaned, None

            else:
                # 可能是純文本
                return txt_response.text, None

        except Exception as e:
            return None, str(e)

    def crawl_novel(self, csv_file, output_dir, start=0, end=None, delay=3):
        """爬取整本小說"""
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

        # 建立會話（訪問主頁）
        try:
            self.session.get('https://m.zashuwu.com/', timeout=10)
            print("已建立會話")
        except:
            pass

        # 逐個爬取
        for i, url in enumerate(urls):
            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(start + i + 1)

            print(f"\n[{i + 1}/{len(urls)}] 爬取章節 {chapter_num}: {url}")

            # 獲取內容
            content, error = self.get_chapter(url)

            if content:
                # 保存內容
                output_file = os.path.join(output_dir, f'chapter_{chapter_num}.txt')

                try:
                    with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(content)
                    print(f"✓ 成功保存到: {output_file}")
                    print(f"  內容預覽: {content[:100]}...")
                    success_count += 1
                except Exception as e:
                    print(f"✗ 保存失敗: {e}")
                    fail_count += 1
            else:
                print(f"✗ 獲取失敗: {error}")
                fail_count += 1

                # 保存錯誤信息
                error_file = os.path.join(output_dir, f'error_chapter_{chapter_num}.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"爬取失敗\nURL: {url}\n錯誤: {error}")

            # 延遲（避免被封）
            if i < len(urls) - 1:
                delay_time = random.uniform(delay, delay + 2)
                print(f"等待 {delay_time:.1f} 秒...")
                time.sleep(delay_time)

        # 生成統計
        print(f"\n{'=' * 50}")
        print(f"爬取完成！")
        print(f"成功: {success_count} 章")
        print(f"失敗: {fail_count} 章")

        # 合併所有章節為一個文件
        if success_count > 0:
            print("\n合併章節...")
            combined_file = os.path.join(output_dir, 'complete_novel.txt')

            with open(combined_file, 'w', encoding='utf-8', errors='ignore') as outfile:
                outfile.write(f"《風流皇太子》\n")
                outfile.write(f"作者：煙十叁\n")
                outfile.write(f"共 {success_count} 章\n\n")

                for i in range(1, 1000):  # 假設最多1000章
                    chapter_file = os.path.join(output_dir, f'chapter_{i}.txt')
                    if os.path.exists(chapter_file):
                        with open(chapter_file, 'r', encoding='utf-8', errors='ignore') as infile:
                            content = infile.read()
                            outfile.write(f"\n{'=' * 50}\n")
                            outfile.write(f"第 {i} 章\n")
                            outfile.write(f"{'=' * 50}\n\n")
                            outfile.write(content)
                            outfile.write('\n\n')

            print(f"✓ 完整小說已保存到: {combined_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='zashuwu.com 小說爬蟲')
    parser.add_argument('--csv', type=str, default='m1.csv', help='CSV文件路徑')
    parser.add_argument('--output', type=str, default='風流皇太子', help='輸出目錄')
    parser.add_argument('--start', type=int, default=0, help='開始索引')
    parser.add_argument('--end', type=int, default=None, help='結束索引')
    parser.add_argument('--delay', type=float, default=3, help='請求間延遲（秒）')
    parser.add_argument('--test', action='store_true', help='測試模式（只爬取前3章）')

    args = parser.parse_args()

    # 創建爬蟲實例
    crawler = ZashuwuCrawler()

    if args.test:
        # 測試模式
        print("測試模式：只爬取前3章")
        crawler.crawl_novel(args.csv, args.output, 0, 3, args.delay)
    else:
        # 正常模式
        crawler.crawl_novel(args.csv, args.output, args.start, args.end, args.delay)


if __name__ == "__main__":
    main()