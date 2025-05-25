"""
簡單解碼 1.txt 的內容
"""
import json
import re


def decode_zashuwu():
    # 讀取文件
    with open('test_http/1.txt', 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # 提取JSON
    if content.startswith('_txt_call('):
        json_str = content[10:-1]
    else:
        json_str = content

    # 解析JSON
    data = json.loads(json_str)
    encoded_content = data['content']
    replace_rules = data['replace']

    print("開始解碼...")
    print(f"編碼內容長度: {len(encoded_content)}")
    print(f"替換規則: {replace_rules}")

    # 分析編碼格式
    # 內容格式: 300a98ce6d417687...
    # 看起來是4位十六進制的Unicode編碼

    # 方法1: 直接轉換十六進制到Unicode
    result = []

    # 用分號分割
    parts = encoded_content.split(';')

    for part_idx, part in enumerate(parts):
        if not part.strip():
            continue

        # 移除非十六進制字符
        hex_only = re.sub(r'[^0-9a-fA-F]', '', part)

        # 每4位轉換一個字符
        chars = []
        for i in range(0, len(hex_only), 4):
            if i + 4 <= len(hex_only):
                hex_code = hex_only[i:i + 4]
                try:
                    # 轉換為Unicode字符
                    char = chr(int(hex_code, 16))
                    chars.append(char)
                except ValueError:
                    chars.append(f'[{hex_code}]')

        result.append(''.join(chars))

    # 合併結果
    decoded = ''.join(result)

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
    print(f"\n完整內容已保存到: decoded_result.txt")

    # 額外處理：檢查是否有特殊字符需要處理
    if '&#' in decoded:
        print("\n檢測到HTML實體，進行額外處理...")
        import html
        decoded_html = html.unescape(decoded)
        with open('decoded_result_clean.txt', 'w', encoding='utf-8') as f:
            f.write(decoded_html)
        print("清理後的內容已保存到: decoded_result_clean.txt")


if __name__ == "__main__":
    decode_zashuwu()