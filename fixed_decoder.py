"""
修復的解碼器 - 處理JSON中的控制字符
"""
import json
import re


def fix_json_string(json_str):
    """修復JSON字符串中的控制字符"""
    # 移除或替換控制字符
    # 保留換行符 \n 但移除其他控制字符
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)

    # 修復可能的轉義問題
    json_str = json_str.replace('\\n', '\\\\n')
    json_str = json_str.replace('\n', '\\n')

    return json_str


def decode_zashuwu():
    # 讀取文件
    with open('test_http/1.txt', 'r', encoding='utf-8') as f:
        content = f.read().strip()

    print(f"原始內容長度: {len(content)}")
    print(f"前50字符: {repr(content[:50])}")

    # 提取JSON
    if content.startswith('_txt_call('):
        json_str = content[10:-1]
    else:
        json_str = content

    # 修復JSON字符串
    json_str = fix_json_string(json_str)

    try:
        # 解析JSON
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON解析失敗: {e}")
        print(f"錯誤位置附近的內容: {repr(json_str[max(0, e.pos - 20):e.pos + 20])}")

        # 嘗試手動解析
        print("\n嘗試手動解析...")
        return manual_parse(content)

    encoded_content = data.get('content', '')
    replace_rules = data.get('replace', {})

    print(f"編碼內容長度: {len(encoded_content)}")
    print(f"替換規則: {replace_rules}")

    # 解碼內容
    decoded = decode_hex_content(encoded_content)

    # 應用替換規則
    for old, new in replace_rules.items():
        decoded = decoded.replace(old, new)

    # 保存結果
    with open('decoded_result.txt', 'w', encoding='utf-8') as f:
        f.write(decoded)

    print(f"\n解碼完成！")
    print(f"解碼後長度: {len(decoded)}")
    print(f"\n前500字符預覽:")
    print(decoded[:500])

    return decoded


def manual_parse(content):
    """手動解析內容（不依賴JSON）"""
    print("執行手動解析...")

    # 提取content部分
    content_match = re.search(r'"content":"([^"]+)"', content)
    if not content_match:
        print("未找到content部分")
        return None

    encoded_content = content_match.group(1)

    # 提取replace規則
    replace_rules = {}
    replace_match = re.search(r'"replace":\{([^}]+)\}', content)
    if replace_match:
        replace_str = replace_match.group(1)
        # 解析替換規則
        for rule in re.findall(r'"([^"]+)":"([^"]*)"', replace_str):
            replace_rules[rule[0]] = rule[1]

    print(f"手動提取的內容長度: {len(encoded_content)}")
    print(f"手動提取的替換規則: {replace_rules}")

    # 解碼
    decoded = decode_hex_content(encoded_content)

    # 應用替換規則
    for old, new in replace_rules.items():
        decoded = decoded.replace(old, new)

    # 保存結果
    with open('decoded_manual.txt', 'w', encoding='utf-8') as f:
        f.write(decoded)

    print(f"\n手動解碼完成！")
    print(f"解碼後長度: {len(decoded)}")
    print(f"\n前500字符預覽:")
    print(decoded[:500])

    return decoded


def decode_hex_content(hex_str):
    """解碼十六進制內容"""
    result = []

    # 分號分割
    parts = hex_str.split(';')

    for part in parts:
        if not part.strip():
            continue

        # 移除非十六進制字符
        hex_only = re.sub(r'[^0-9a-fA-F]', '', part)

        # 每4位轉換一個字符
        for i in range(0, len(hex_only), 4):
            if i + 4 <= len(hex_only):
                hex_code = hex_only[i:i + 4]
                try:
                    # 轉換為Unicode字符
                    char = chr(int(hex_code, 16))
                    result.append(char)
                except ValueError:
                    # 如果轉換失敗，保留原始值
                    result.append(f'[{hex_code}]')

    return ''.join(result)


if __name__ == "__main__":
    decode_zashuwu()