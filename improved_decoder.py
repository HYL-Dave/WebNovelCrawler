"""
改進的解碼器 - 修復標點符號和換行問題
"""
import re
import json
import unicodedata


class ImprovedDecoder:
    def __init__(self):
        # 常見的標點符號映射
        self.punctuation_map = {
            'ff0c': '，',  # 中文逗號
            '3002': '。',  # 中文句號
            'ff1a': '：',  # 中文冒號
            'ff1b': '；',  # 中文分號
            'ff1f': '？',  # 中文問號
            'ff01': '！',  # 中文感嘆號
            '201c': '"',  # 左雙引號
            '201d': '"',  # 右雙引號
            '2018': ''',     # 左單引號
            '2019': ''',  # 右單引號
            '3001': '、',  # 頓號
            'ff08': '（',  # 左括號
            'ff09': '）',  # 右括號
            '300a': '《',  # 左書名號
            '300b': '》',  # 右書名號
            '3008': '〈',  # 左角括號
            '3009': '〉',  # 右角括號
            'ff0d': '－',  # 中文破折號
            '2026': '…',  # 省略號
            '000a': '\n',  # 換行符
            '000d': '\r',  # 回車符
            '0020': ' ',  # 空格
            '3000': '　',  # 中文空格
        }

        # 常見的換行標誌
        self.line_break_patterns = [
            r'第[一二三四五六七八九十\d]+章',  # 章節標題
            r'第[一二三四五六七八九十\d]+節',  # 節標題
            r'第[一二三四五六七八九十\d]+回',  # 回標題
        ]

    def decode_hex_content(self, encoded_content):
        """解碼十六進制內容"""
        print(f"開始解碼，內容長度: {len(encoded_content)}")

        # 分號分割
        parts = encoded_content.split(';') if ';' in encoded_content else [encoded_content]
        print(f"發現 {len(parts)} 個部分")

        decoded_chars = []

        for part_idx, part in enumerate(parts):
            if not part.strip():
                continue

            print(f"處理第 {part_idx + 1} 部分: {part[:50]}...")

            # 清理：只保留十六進制字符
            hex_only = re.sub(r'[^0-9a-fA-F]', '', part)

            # 每4位解碼一個字符
            for i in range(0, len(hex_only), 4):
                if i + 4 <= len(hex_only):
                    hex_code = hex_only[i:i + 4]
                    try:
                        code_point = int(hex_code, 16)

                        # 跳過代理區字符（0xD800-0xDFFF）
                        if 0xD800 <= code_point <= 0xDFFF:
                            continue

                        # 跳過無效字符
                        if code_point > 0x10FFFF:
                            continue

                        # 檢查是否為控制字符，但保留換行和回車
                        if code_point < 32 and code_point not in [9, 10, 13]:  # 保留tab, LF, CR
                            continue

                        char = chr(code_point)
                        decoded_chars.append(char)

                    except Exception as e:
                        print(f"解碼失敗: {hex_code} - {e}")

        return ''.join(decoded_chars)

    def apply_replacements(self, text, replace_rules=None):
        """應用替換規則"""
        print("應用替換規則...")

        # 首先應用內建的標點符號映射
        for hex_code, replacement in self.punctuation_map.items():
            if hex_code in text:
                print(f"替換標點: {hex_code} -> {replacement}")
                text = text.replace(hex_code, replacement)

        # 應用自定義替換規則
        if replace_rules:
            for old, new in replace_rules.items():
                if old in text and old not in ['&#x', ';&#x', ';&#', ';\n']:
                    print(f"自定義替換: {old} -> {new}")
                    text = text.replace(old, new)

        return text

    def fix_line_breaks(self, text):
        """修復換行問題"""
        print("修復換行...")

        lines = text.split('\n')
        fixed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 檢查是否為章節標題
            is_chapter = False
            for pattern in self.line_break_patterns:
                if re.search(pattern, line):
                    is_chapter = True
                    break

            if is_chapter:
                # 章節標題前後加空行
                if fixed_lines and fixed_lines[-1]:  # 前面有內容且不是空行
                    fixed_lines.append('')
                fixed_lines.append(line)
                fixed_lines.append('')
            else:
                # 普通內容
                if line.endswith(('。', '！', '？', '"', '》')):
                    # 句子結束，可能需要換行
                    fixed_lines.append(line)
                else:
                    # 句子未結束，可能需要與下一行合併
                    if fixed_lines and not fixed_lines[-1].endswith(('。', '！', '？', '"', '》')):
                        # 與上一行合併
                        fixed_lines[-1] += line
                    else:
                        fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def clean_content(self, text):
        """清理內容"""
        print("清理廣告和無效內容...")

        ad_keywords = [
            '雜書屋', '杂书屋', 'zashuwu.com', 'ZASHUWU.COM',
            '記郵件找地址', '记邮件找地址', 'dz@',
            '請記住', '请记住', '手機閱讀', '手机阅读',
            '加入書簽', '加入书签', '最新章節', '最新章节',
            'http://', 'https://'
        ]

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 檢查是否包含廣告
            is_ad = any(keyword in line for keyword in ad_keywords)

            # 檢查是否為過短的行（可能是碎片）
            if len(line) < 3 and not re.search(r'[第\d章節回]', line):
                continue

            if not is_ad:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def decode_file(self, input_file, output_file=None):
        """解碼文件"""
        print(f"讀取文件: {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取content部分
        content_match = re.search(r'"content"\s*:\s*"([^"]+)"', content, re.DOTALL)
        if not content_match:
            print("無法找到content部分")
            return None

        encoded_content = content_match.group(1)
        print(f"找到編碼內容，長度: {len(encoded_content)}")

        # 提取替換規則
        replace_rules = {}
        replace_match = re.search(r'"replace"\s*:\s*\{([^}]+)\}', content, re.DOTALL)
        if replace_match:
            replace_text = replace_match.group(1)
            for match in re.finditer(r'"([^"]+)"\s*:\s*"([^"]*)"', replace_text):
                key = match.group(1)
                value = match.group(2)
                replace_rules[key] = value

        print(f"找到替換規則: {replace_rules}")

        # 開始解碼
        decoded_text = self.decode_hex_content(encoded_content)
        print(f"初步解碼完成，長度: {len(decoded_text)}")

        # 應用替換規則
        decoded_text = self.apply_replacements(decoded_text, replace_rules)

        # 修復換行
        decoded_text = self.fix_line_breaks(decoded_text)

        # 清理內容
        decoded_text = self.clean_content(decoded_text)

        # 保存結果
        if output_file is None:
            output_file = 'improved_decoded.txt'

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(decoded_text)
            print(f"成功保存到: {output_file}")
        except Exception as e:
            print(f"保存失敗: {e}")

        print(f"\n解碼完成！")
        print(f"最終文本長度: {len(decoded_text)}")
        print(f"\n前500字符預覽:")
        print(decoded_text[:500])

        # 統計信息
        line_count = len(decoded_text.split('\n'))
        char_count = len(decoded_text)
        print(f"\n統計信息:")
        print(f"總行數: {line_count}")
        print(f"總字符數: {char_count}")

        return decoded_text


def main():
    """主函數"""
    decoder = ImprovedDecoder()

    # 解碼1.txt文件
    result = decoder.decode_file('1.txt', 'improved_decoded.txt')

    if result and ('葉洵' in result or '叶洵' in result):
        print("\n✓ 確認解碼成功，包含預期內容！")
    else:
        print("\n✗ 解碼可能有問題，請檢查結果")


if __name__ == "__main__":
    main()