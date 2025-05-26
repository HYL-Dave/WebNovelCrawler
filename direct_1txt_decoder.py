"""
直接解碼 1.txt 文件
"""
import re


def decode_1txt():
    """直接解碼 1.txt 文件，不使用 JSON 解析"""
    print("讀取 1.txt 文件...")

    with open('test_http/1.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"文件大小: {len(content)} 字符")

    # 使用正則表達式提取 content 部分
    # 查找 "content":" 和下一個 " 之間的內容
    content_match = re.search(r'"content"\s*:\s*"([^"]+)"', content, re.DOTALL)

    if not content_match:
        print("無法找到 content 部分")
        return None

    encoded_content = content_match.group(1)
    print(f"找到編碼內容，長度: {len(encoded_content)}")
    print(f"前100字符: {encoded_content[:100]}")

    # 提取替換規則
    replace_rules = {}
    replace_match = re.search(r'"replace"\s*:\s*\{([^}]+)\}', content, re.DOTALL)
    if replace_match:
        replace_text = replace_match.group(1)
        # 提取所有的 "key":"value" 對
        for match in re.finditer(r'"([^"]+)"\s*:\s*"([^"]*)"', replace_text):
            key = match.group(1)
            value = match.group(2)
            replace_rules[key] = value

    print(f"找到替換規則: {replace_rules}")

    # 開始解碼
    print("\n開始解碼...")

    # 分析編碼格式
    # 300a98ce6d417687592a5b50300b4f5c8005ff1a70df534153c165876848ff1a301065e54e073011
    # 看起來是連續的4位十六進制

    # 方法1: 按分號分割
    if ';' in encoded_content:
        parts = encoded_content.split(';')
        print(f"發現 {len(parts)} 個部分（按分號分割）")
    else:
        # 沒有分號，整體處理
        parts = [encoded_content]

    decoded_chars = []

    for part_idx, part in enumerate(parts):
        if not part.strip():
            continue

        # 清理部分：只保留十六進制字符
        hex_only = re.sub(r'[^0-9a-fA-F]', '', part)

        # 每4位解碼一個字符
        for i in range(0, len(hex_only), 4):
            if i + 4 <= len(hex_only):
                hex_code = hex_only[i:i + 4]
                try:
                    # 轉換為整數再轉為字符
                    code_point = int(hex_code, 16)
                    char = chr(code_point)
                    decoded_chars.append(char)
                except Exception as e:
                    # 解碼失敗，跳過
                    print(f"解碼失敗: {hex_code} - {e}")

    # 合併所有字符
    decoded_text = ''.join(decoded_chars)

    print(f"\n初步解碼完成，長度: {len(decoded_text)}")
    print(f"前200字符: {decoded_text[:200]}")

    # 應用替換規則
    print("\n應用替換規則...")
    for old, new in replace_rules.items():
        count = decoded_text.count(old)
        if count > 0:
            print(f"替換 '{old}' -> '{new}' ({count} 次)")
            decoded_text = decoded_text.replace(old, new)

    # 額外的清理
    # 移除常見的廣告文字
    ad_patterns = [
        '雜書屋', '杂书屋', 'zashuwu.com', 'ZASHUWU.COM',
        '記郵件找地址', '记邮件找地址', 'dz@ZASHUWU.COM'
    ]

    lines = decoded_text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 檢查是否包含廣告
        is_ad = False
        for ad in ad_patterns:
            if ad in line:
                is_ad = True
                break

        if not is_ad:
            cleaned_lines.append(line)

    final_text = '\n'.join(cleaned_lines)

    # 保存結果
    with open('decoded_final.txt', 'w', encoding='utf-8') as f:
        f.write(final_text)

    print(f"\n解碼完成！")
    print(f"最終文本長度: {len(final_text)}")
    print(f"\n前500字符預覽:")
    print(final_text[:500])
    print(f"\n完整內容已保存到: decoded_final.txt")

    # 額外檢查：確認是否是小說內容
    if '葉洵' in final_text or '秦王' in final_text or '第' in final_text:
        print("\n✓ 確認是小說內容！")
    else:
        print("\n⚠ 警告：解碼後的內容可能不是預期的小說內容")
        print("嘗試其他編碼方式...")

        # 嘗試其他解碼方式
        alternative_decode(encoded_content, replace_rules)

    return final_text


def alternative_decode(encoded_content, replace_rules):
    """嘗試其他解碼方式"""
    print("\n嘗試替代解碼方式...")

    # 方法2: 將整個內容視為連續的十六進制
    hex_only = re.sub(r'[^0-9a-fA-F]', '', encoded_content)

    # 嘗試不同的解碼方式
    methods = [
        ("UTF-16 BE", lambda h: bytes.fromhex(h).decode('utf-16-be', errors='ignore')),
        ("UTF-16 LE", lambda h: bytes.fromhex(h).decode('utf-16-le', errors='ignore')),
        ("UTF-8", lambda h: bytes.fromhex(h).decode('utf-8', errors='ignore')),
        ("GBK", lambda h: bytes.fromhex(h).decode('gbk', errors='ignore')),
        ("GB18030", lambda h: bytes.fromhex(h).decode('gb18030', errors='ignore')),
    ]

    for method_name, decode_func in methods:
        try:
            print(f"\n嘗試 {method_name} 解碼...")
            # 確保十六進制字符串長度是偶數
            if len(hex_only) % 2 != 0:
                hex_only = hex_only[:-1]

            decoded = decode_func(hex_only)

            # 應用替換規則
            for old, new in replace_rules.items():
                decoded = decoded.replace(old, new)

            # 檢查結果
            if len(decoded) > 100 and ('葉洵' in decoded or '秦王' in decoded or '第' in decoded):
                print(f"✓ {method_name} 解碼成功！")
                print(f"前200字符: {decoded[:200]}")

                with open(f'decoded_{method_name.replace(" ", "_")}.txt', 'w', encoding='utf-8') as f:
                    f.write(decoded)

                return decoded
        except Exception as e:
            print(f"✗ {method_name} 解碼失敗: {e}")

    return None


if __name__ == "__main__":
    decode_1txt()