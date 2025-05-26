#!/usr/bin/env python3
"""
爬蟲監控和統計腳本
"""

import os
import re
import json
import time
import argparse
from datetime import datetime
from collections import defaultdict


class CrawlerMonitor:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.stats = {
            'total_files': 0,
            'successful_files': 0,
            'empty_files': 0,
            'error_files': 0,
            'total_chars': 0,
            'avg_chars_per_chapter': 0,
            'chapters_with_images': 0,
            'chapters_with_ocr': 0,
            'decode_success_rate': 0,
            'common_errors': defaultdict(int),
            'processing_times': [],
            'chapter_lengths': [],
            'missing_chapters': [],
            'duplicate_chapters': defaultdict(int)
        }

    def analyze_output(self):
        """分析輸出目錄"""
        print(f"分析目錄: {self.output_dir}")

        if not os.path.exists(self.output_dir):
            print(f"錯誤: 目錄 {self.output_dir} 不存在")
            return

        files = os.listdir(self.output_dir)

        # 分析文件
        for filename in files:
            filepath = os.path.join(self.output_dir, filename)

            if filename.endswith('.txt'):
                self.analyze_text_file(filepath, filename)
            elif filename.endswith('.log'):
                self.analyze_log_file(filepath, filename)
            elif filename.endswith('.png'):
                self.stats['chapters_with_images'] += 1

        self.calculate_statistics()
        self.generate_report()

    def analyze_text_file(self, filepath, filename):
        """分析文本文件"""
        self.stats['total_files'] += 1

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                self.stats['empty_files'] += 1
                return

            if filename.startswith('error_'):
                self.stats['error_files'] += 1
                return

            # 成功的文件
            self.stats['successful_files'] += 1
            char_count = len(content)
            self.stats['total_chars'] += char_count
            self.stats['chapter_lengths'].append(char_count)

            # 檢查內容質量
            self.analyze_content_quality(content, filename)

            # 提取章節號
            chapter_match = re.search(r'chapter_(\d+)', filename)
            if chapter_match:
                chapter_num = int(chapter_match.group(1))
                self.stats['duplicate_chapters'][chapter_num] += 1

        except Exception as e:
            print(f"分析文件失敗 {filename}: {e}")
            self.stats['common_errors'][str(e)] += 1

    def analyze_content_quality(self, content, filename):
        """分析內容質量"""
        # 檢查是否包含OCR內容
        if '=== 圖片文字 ===' in content or '=== Canvas文字 ===' in content:
            self.stats['chapters_with_ocr'] += 1

        # 檢查標點符號
        punctuation_count = len(re.findall(r'[，。！？；：]', content))
        if punctuation_count > 0:
            self.stats['decode_success_rate'] += 1

        # 檢查是否有廣告殘留
        ad_indicators = ['雜書屋', 'zashuwu', '記郵件', '最新章節']
        has_ads = any(ad in content for ad in ad_indicators)
        if has_ads:
            self.stats['common_errors']['廣告清理不完整'] += 1

        # 檢查章節完整性
        if len(content) < 500:
            self.stats['common_errors']['內容過短'] += 1
        elif len(content) > 50000:
            self.stats['common_errors']['內容過長'] += 1

    def analyze_log_file(self, filepath, filename):
        """分析日誌文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if '失敗' in line or '錯誤' in line:
                    # 提取錯誤類型
                    if 'timeout' in line.lower():
                        self.stats['common_errors']['超時'] += 1
                    elif 'detection' in line.lower() or '檢測' in line:
                        self.stats['common_errors']['反爬檢測'] += 1
                    elif 'decode' in line.lower() or '解碼' in line:
                        self.stats['common_errors']['解碼失敗'] += 1
                    else:
                        self.stats['common_errors']['其他錯誤'] += 1

        except Exception as e:
            print(f"分析日誌失敗 {filename}: {e}")

    def calculate_statistics(self):
        """計算統計數據"""
        if self.stats['successful_files'] > 0:
            self.stats['avg_chars_per_chapter'] = int(
                self.stats['total_chars'] / self.stats['successful_files']
            )

        if self.stats['total_files'] > 0:
            self.stats['decode_success_rate'] = int(
                (self.stats['decode_success_rate'] / self.stats['total_files']) * 100
            )

        # 找出缺失的章節
        if self.stats['duplicate_chapters']:
            chapter_nums = list(self.stats['duplicate_chapters'].keys())
            min_chapter = min(chapter_nums)
            max_chapter = max(chapter_nums)

            for i in range(min_chapter, max_chapter + 1):
                if i not in self.stats['duplicate_chapters']:
                    self.stats['missing_chapters'].append(i)

    def generate_report(self):
        """生成報告"""
        print(f"\n{'=' * 60}")
        print(f"爬蟲分析報告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")

        # 基本統計
        print(f"\n📊 基本統計:")
        print(f"  總文件數: {self.stats['total_files']}")
        print(f"  成功文件: {self.stats['successful_files']}")
        print(f"  空文件: {self.stats['empty_files']}")
        print(f"  錯誤文件: {self.stats['error_files']}")
        print(f"  成功率: {self.get_success_rate():.1f}%")

        # 內容統計
        print(f"\n📝 內容統計:")
        print(f"  總字符數: {self.stats['total_chars']:,}")
        print(f"  平均每章字符數: {self.stats['avg_chars_per_chapter']:,}")
        print(f"  解碼成功率: {self.stats['decode_success_rate']}%")
        print(f"  包含OCR內容的章節: {self.stats['chapters_with_ocr']}")

        # 質量分析
        if self.stats['chapter_lengths']:
            lengths = self.stats['chapter_lengths']
            print(f"\n📈 章節長度分布:")
            print(f"  最短: {min(lengths):,} 字符")
            print(f"  最長: {max(lengths):,} 字符")
            print(f"  中位數: {self.get_median(lengths):,} 字符")

        # 問題分析
        if self.stats['common_errors']:
            print(f"\n⚠️  常見問題:")
            for error, count in sorted(self.stats['common_errors'].items(),
                                       key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count} 次")

        # 缺失章節
        if self.stats['missing_chapters']:
            print(f"\n❌ 缺失章節: {self.stats['missing_chapters']}")

        # 重複章節
        duplicates = {k: v for k, v in self.stats['duplicate_chapters'].items() if v > 1}
        if duplicates:
            print(f"\n🔄 重複章節: {duplicates}")

        # 建議
        self.generate_recommendations()

        # 保存詳細報告
        self.save_detailed_report()

    def get_success_rate(self):
        """計算成功率"""
        if self.stats['total_files'] == 0:
            return 0
        return (self.stats['successful_files'] / self.stats['total_files']) * 100

    def get_median(self, numbers):
        """計算中位數"""
        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)
        if n % 2 == 0:
            return (sorted_numbers[n // 2 - 1] + sorted_numbers[n // 2]) // 2
        else:
            return sorted_numbers[n // 2]

    def generate_recommendations(self):
        """生成改進建議"""
        print(f"\n💡 改進建議:")

        success_rate = self.get_success_rate()

        if success_rate < 50:
            print("  - 成功率較低，建議檢查網站反爬機制")
            print("  - 考慮增加延遲時間或使用代理")

        if self.stats['decode_success_rate'] < 80:
            print("  - 解碼成功率不理想，檢查解碼器配置")
            print("  - 驗證標點符號映射是否完整")

        if self.stats['common_errors'].get('內容過短', 0) > 5:
            print("  - 多個章節內容過短，可能存在提取問題")
            print("  - 建議啟用OCR功能或檢查選擇器")

        if self.stats['missing_chapters']:
            print(f"  - 有 {len(self.stats['missing_chapters'])} 個章節缺失")
            print("  - 建議重新爬取缺失的章節")

        if self.stats['chapters_with_ocr'] == 0 and self.stats['successful_files'] > 0:
            print("  - 未檢測到OCR內容，如果網站使用圖片文字，建議啟用OCR")

    def save_detailed_report(self):
        """保存詳細報告"""
        report_file = os.path.join(self.output_dir, 'analysis_report.json')

        # 準備可序列化的數據
        serializable_stats = dict(self.stats)
        serializable_stats['common_errors'] = dict(serializable_stats['common_errors'])
        serializable_stats['duplicate_chapters'] = dict(serializable_stats['duplicate_chapters'])
        serializable_stats['analysis_time'] = datetime.now().isoformat()

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_stats, f, indent=2, ensure_ascii=False)
            print(f"\n📄 詳細報告已保存: {report_file}")
        except Exception as e:
            print(f"保存報告失敗: {e}")

    def fix_missing_chapters(self, csv_file):
        """生成修復缺失章節的命令"""
        if not self.stats['missing_chapters']:
            print("沒有缺失的章節需要修復")
            return

        print(f"\n🔧 修復缺失章節的建議命令:")

        for chapter in self.stats['missing_chapters']:
            print(f"  # 修復第 {chapter} 章")
            print(f"  python comprehensive_novel_crawler.py \\")
            print(f"    --csv {csv_file} \\")
            print(f"    --start {chapter - 1} \\")
            print(f"    --end {chapter} \\")
            print(f"    --output {self.output_dir}")
            print()


def main():
    parser = argparse.ArgumentParser(description='爬蟲結果監控和分析')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='要分析的輸出目錄')
    parser.add_argument('--csv', type=str, default='m1.csv',
                        help='原始CSV文件（用於生成修復命令）')
    parser.add_argument('--fix', action='store_true',
                        help='生成修復缺失章節的命令')

    args = parser.parse_args()

    monitor = CrawlerMonitor(args.output_dir)
    monitor.analyze_output()

    if args.fix:
        monitor.fix_missing_chapters(args.csv)


if __name__ == "__main__":
    main()