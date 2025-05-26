"""
修復Unicode錯誤的解碼器
"""
import re
import unicodedata


def clean_unicode_text(text):
    """清理無效的Unicode字符"""
    # 方法1：移除所有無效字符
    cleaned = []
    for char in text:
        try:
            # 嘗試編碼為UTF-8，如果失敗則跳過
            char.encode('utf-8')
            cleaned.append(char)
        except UnicodeEncodeError:
            # 跳過無效字符
            print(f"跳過無效字符: {repr(char)}")
            pass

    return ''.join(cleaned)


def decode_1txt_fixed():
    """修復版本的解碼器"""
    print("讀取 1.txt 文件...")

    with open('test_http/1.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"文件大小: {len(content)} 字符")

    # 提取 content 部分
    content_match = re.search(r'"content"\s*:\s*"([^"]+)"', content, re.DOTALL)

    if not content_match:
        print("無法找到 content 部分")
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
            # 不使用控制字符作為替換值
            replace_rules[key] = value if value else ''

    print(f"找到替換規則: {replace_rules}")

    # 開始解碼
    print("\n開始解碼...")

    # 分號分割
    parts = encoded_content.split(';') if ';' in encoded_content else [encoded_content]
    print(f"發現 {len(parts)} 個部分")

    decoded_chars = []

    for part_idx, part in enumerate(parts):
        if not part.strip():
            continue

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
                        print(f"跳過代理區字符: {hex_code}")
                        continue

                    # 跳過其他無效字符
                    if code_point > 0x10FFFF:
                        print(f"跳過無效字符: {hex_code}")
                        continue

                    char = chr(code_point)
                    decoded_chars.append(char)

                except Exception as e:
                    print(f"解碼失敗: {hex_code} - {e}")

    # 合併所有字符
    decoded_text = ''.join(decoded_chars)

    print(f"\n初步解碼完成，長度: {len(decoded_text)}")

    # 應用替換規則（改進版）
    print("\n應用替換規則...")

    # 替換規則看起來有問題，我們暫時不使用它們
    # 或者只使用安全的替換
    safe_replacements = {
        'ff0c': '，',  # 中文逗號
        '3002': '。',  # 中文句號
    }

    for old, new in safe_replacements.items():
        if old in decoded_text:
            print(f"替換 '{old}' -> '{new}'")
            decoded_text = decoded_text.replace(old, new)

    # 清理無效Unicode字符
    print("\n清理無效字符...")
    decoded_text = clean_unicode_text(decoded_text)

    # 額外的清理
    lines = decoded_text.split('\n')
    cleaned_lines = []

    # 廣告關鍵詞
    ad_keywords = [
        '雜書屋', '杂书屋', 'zashuwu.com', 'ZASHUWU.COM',
        '記郵件找地址', '记邮件找地址', 'dz@'
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 檢查是否包含廣告
        is_ad = any(keyword in line for keyword in ad_keywords)

        if not is_ad:
            cleaned_lines.append(line)

    final_text = '\n'.join(cleaned_lines)

    # 保存結果（使用錯誤處理）
    try:
        with open('decoded_final.txt', 'w', encoding='utf-8', errors='ignore') as f:
            f.write(final_text)
        print("\n成功保存到: decoded_final.txt")
    except Exception as e:
        print(f"保存失敗: {e}")
        # 嘗試其他編碼
        with open('decoded_final_gbk.txt', 'w', encoding='gbk', errors='ignore') as f:
            f.write(final_text)
        print("保存到: decoded_final_gbk.txt (GBK編碼)")

    print(f"\n解碼完成！")
    print(f"最終文本長度: {len(final_text)}")
    print(f"\n前500字符預覽:")
    print(final_text[:500])

    # 確認內容
    if '葉洵' in final_text or '叶洵' in final_text:
        print("\n✓ 確認是《風流皇太子》的內容！")

    return final_text


def decode_entire_novel(csv_file='m1.csv'):
    """解碼整本小說（如果有多個章節的txt文件）"""
    import glob
    import os

    # 查找所有的 txt 文件
    txt_files = glob.glob('*.txt')
    chapter_files = [f for f in txt_files if re.match(r'\d+\.txt', f)]

    if chapter_files:
        print(f"\n找到 {len(chapter_files)} 個章節文件")

        # 創建輸出目錄
        os.makedirs('decoded_chapters', exist_ok=True)

        # 排序
        chapter_files.sort(key=lambda x: int(re.search(r'(\d+)\.txt', x).group(1)))

        for chapter_file in chapter_files:
            print(f"\n處理: {chapter_file}")

            try:
                with open(chapter_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 使用相同的解碼邏輯
                if content.startswith('_txt_call('):
                    # 提取和解碼
                    content_match = re.search(r'"content"\s*:\s*"([^"]+)"', content)
                    if content_match:
                        encoded = content_match.group(1)
                        decoded = decode_hex_string(encoded)
                        decoded = clean_unicode_text(decoded)

                        # 保存
                        chapter_num = re.search(r'(\d+)\.txt', chapter_file).group(1)
                        output_file = os.path.join('decoded_chapters', f'chapter_{chapter_num}.txt')

                        with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
                            f.write(decoded)

                        print(f"✓ 保存到: {output_file}")

            except Exception as e:
                print(f"✗ 處理失敗: {e}")


def decode_hex_string(hex_str):
    """解碼十六進制字符串（輔助函數）"""
    result = []
    parts = hex_str.split(';') if ';' in hex_str else [hex_str]

    for part in parts:
        if not part.strip():
            continue

        hex_only = re.sub(r'[^0-9a-fA-F]', '', part)

        for i in range(0, len(hex_only), 4):
            if i + 4 <= len(hex_only):
                hex_code = hex_only[i:i + 4]
                try:
                    code_point = int(hex_code, 16)

                    # 跳過無效字符
                    if 0xD800 <= code_point <= 0xDFFF or code_point > 0x10FFFF:
                        continue

                    char = chr(code_point)
                    result.append(char)
                except:
                    pass

    return ''.join(result)


if __name__ == "__main__":
    # 解碼單個文件
    decode_1txt_fixed()

    # 如果有多個章節文件，也可以批量處理
    # decode_entire_novel()