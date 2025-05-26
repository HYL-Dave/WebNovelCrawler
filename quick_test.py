#!/usr/bin/env python3
"""
快速測試腳本 - 比較不同爬取方法的效果
"""

import os
import sys
import time
import subprocess
import argparse
from datetime import datetime


class QuickTester:
    def __init__(self):
        self.test_url = "https://m.zashuwu.com/wen/2vFm/1.html"  # 示例URL
        self.test_csv = "test_quick.csv"
        self.results = {}

    def setup_test_csv(self, url=None):
        """創建測試用的CSV文件"""
        if url is None:
            url = self.test_url

        with open(self.test_csv, 'w', encoding='utf-8') as f:
            f.write("章節,鏈接\n")
            f.write(f"1,{url}\n")

        print(f"✓ 創建測試CSV: {self.test_csv}")

    def run_crawler(self, script_name, extra_args=None, timeout=120):
        """運行爬蟲腳本"""
        print(f"\n{'=' * 50}")
        print(f"測試: {script_name}")
        print(f"{'=' * 50}")

        cmd = [
            sys.executable, script_name,
            '--csv', self.test_csv,
            '--test',
            '--output', f'test_output_{script_name.replace(".py", "")}'
        ]

        if extra_args:
            cmd.extend(extra_args)

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )

            end_time = time.time()
            duration = end_time - start_time

            success = result.returncode == 0
            output = result.stdout
            error = result.stderr

            # 檢查是否有輸出文件
            output_dir = f'test_output_{script_name.replace(".py", "")}'
            output_files = []
            content_length = 0

            if os.path.exists(output_dir):
                output_files = os.listdir(output_dir)
                # 檢查第一個txt文件的內容長度
                for file in output_files:
                    if file.endswith('.txt') and not file.startswith('error'):
                        try:
                            with open(os.path.join(output_dir, file), 'r', encoding='utf-8') as f:
                                content = f.read()
                                content_length = len(content)
                                break
                        except:
                            pass

            self.results[script_name] = {
                'success': success,
                'duration': duration,
                'output_files': len(output_files),
                'content_length': content_length,
                'stdout': output[:500] + '...' if len(output) > 500 else output,
                'stderr': error[:500] + '...' if len(error) > 500 else error,
                'extra_args': extra_args or []
            }

            print(f"✓ 完成: {duration:.1f}秒")
            print(f"  成功: {success}")
            print(f"  輸出文件: {len(output_files)}")
            print(f"  內容長度: {content_length}")

            if not success:
                print(f"  錯誤: {error[:200]}")

            return success

        except subprocess.TimeoutExpired:
            print(f"✗ 超時 ({timeout}秒)")
            self.results[script_name] = {
                'success': False,
                'duration': timeout,
                'output_files': 0,
                'content_length': 0,
                'stdout': '超時',
                'stderr': '執行超時',
                'extra_args': extra_args or []
            }
            return False

        except Exception as e:
            print(f"✗ 執行失敗: {e}")
            self.results[script_name] = {
                'success': False,
                'duration': 0,
                'output_files': 0,
                'content_length': 0,
                'stdout': '',
                'stderr': str(e),
                'extra_args': extra_args or []
            }
            return False

    def test_decoder_only(self):
        """測試純解碼器"""
        print(f"\n{'=' * 50}")
        print(f"測試: 純解碼器")
        print(f"{'=' * 50}")

        # 檢查是否有1.txt文件
        if not os.path.exists('1.txt'):
            print("✗ 未找到1.txt文件，跳過解碼器測試")
            return False

        try:
            # 導入並運行解碼器
            from improved_decoder import ImprovedDecoder

            decoder = ImprovedDecoder()
            start_time = time.time()

            result = decoder.decode_file('1.txt', 'test_decoder_output.txt')

            end_time = time.time()
            duration = end_time - start_time

            success = result is not None and len(result) > 100
            content_length = len(result) if result else 0

            self.results['decoder_only'] = {
                'success': success,
                'duration': duration,
                'output_files': 1 if success else 0,
                'content_length': content_length,
                'stdout': f'解碼成功，長度: {content_length}' if success else '解碼失敗',
                'stderr': '',
                'extra_args': []
            }

            print(f"✓ 完成: {duration:.1f}秒")
            print(f"  成功: {success}")
            print(f"  內容長度: {content_length}")

            return success

        except Exception as e:
            print(f"✗ 解碼器測試失敗: {e}")
            self.results['decoder_only'] = {
                'success': False,
                'duration': 0,
                'output_files': 0,
                'content_length': 0,
                'stdout': '',
                'stderr': str(e),
                'extra_args': []
            }
            return False

    def run_all_tests(self, url=None):
        """運行所有測試"""
        print(f"開始快速測試 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 設置測試環境
        self.setup_test_csv(url)

        # 測試配置
        test_configs = [
            # 基本測試
            ('novel_crawler_firefox.py', None),
            ('comprehensive_novel_crawler.py', None),

            # 帶OCR的測試
            ('comprehensive_novel_crawler.py', ['--use-ocr']),

            # 無頭模式測試
            ('comprehensive_novel_crawler.py', ['--headless']),

            # Playwright測試（如果存在）
            ('novel_crawler_playwright.py', None),
        ]

        # 運行測試
        for script, args in test_configs:
            if os.path.exists(script):
                self.run_crawler(script, args)
            else:
                print(f"跳過 {script} (文件不存在)")

        # 測試純解碼器
        self.test_decoder_only()

        # 生成報告
        self.generate_report()

    def generate_report(self):
        """生成測試報告"""
        print(f"\n{'=' * 80}")
        print(f"測試報告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 80}")

        print(f"{'方法':<30} {'成功':<6} {'時間':<8} {'內容長度':<10} {'備註'}")
        print(f"{'-' * 80}")

        for name, result in self.results.items():
            success_str = "✓" if result['success'] else "✗"
            duration_str = f"{result['duration']:.1f}s"
            content_str = str(result['content_length'])

            extra_info = ""
            if result['extra_args']:
                extra_info = f"({' '.join(result['extra_args'])})"

            display_name = name.replace('.py', '') + extra_info

            print(f"{display_name:<30} {success_str:<6} {duration_str:<8} {content_str:<10}")

        # 成功率統計
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r['success'])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n成功率: {successful_tests}/{total_tests} ({success_rate:.1f}%)")

        # 推薦方法
        best_method = None
        best_score = 0

        for name, result in self.results.items():
            if result['success']:
                # 計算得分：成功+內容長度+速度
                score = (result['content_length'] / 1000) + (60 / max(result['duration'], 1))
                if score > best_score:
                    best_score = score
                    best_method = name

        if best_method:
            print(f"\n推薦方法: {best_method}")
            print(f"  內容長度: {self.results[best_method]['content_length']}")
            print(f"  執行時間: {self.results[best_method]['duration']:.1f}秒")

        # 保存詳細報告
        self.save_detailed_report()

    def save_detailed_report(self):
        """保存詳細報告"""
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"快速測試詳細報告\n")
            f.write(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"測試URL: {self.test_url}\n\n")

            for name, result in self.results.items():
                f.write(f"{'=' * 50}\n")
                f.write(f"方法: {name}\n")
                f.write(f"{'=' * 50}\n")
                f.write(f"成功: {'是' if result['success'] else '否'}\n")
                f.write(f"執行時間: {result['duration']:.1f}秒\n")
                f.write(f"輸出文件數: {result['output_files']}\n")
                f.write(f"內容長度: {result['content_length']}\n")
                f.write(f"額外參數: {' '.join(result['extra_args'])}\n")
                f.write(f"\n標準輸出:\n{result['stdout']}\n")
                if result['stderr']:
                    f.write(f"\n錯誤輸出:\n{result['stderr']}\n")
                f.write(f"\n")

        print(f"\n詳細報告保存到: {report_file}")

    def cleanup(self):
        """清理測試文件"""
        print("\n清理測試文件...")

        # 清理CSV文件
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

        # 清理輸出目錄
        import shutil
        for item in os.listdir('.'):
            if item.startswith('test_output_'):
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    print(f"  刪除目錄: {item}")

        # 清理其他測試文件
        test_files = ['test_decoder_output.txt', 'improved_decoded.txt']
        for file in test_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"  刪除文件: {file}")


def main():
    parser = argparse.ArgumentParser(description='快速測試不同爬蟲方法')
    parser.add_argument('--url', type=str, default=None, help='測試URL（默認使用內建URL）')
    parser.add_argument('--no-cleanup', action='store_true', help='不清理測試文件')

    args = parser.parse_args()

    tester = QuickTester()

    try:
        tester.run_all_tests(args.url)
    finally:
        if not args.no_cleanup:
            tester.cleanup()


if __name__ == "__main__":
    main()