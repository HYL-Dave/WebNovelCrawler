#!/usr/bin/env python3
"""
進階解碼器 - 支援多種編碼和混淆方式
"""

import re
import base64
import urllib.parse
import html
import json
from typing import Dict, List, Tuple, Optional

class AdvancedDecoder:
    def __init__(self):
        # 常見的中文編碼
        self.chinese_encodings = [
            'utf-8', 'gbk', 'gb2312', 'big5', 'gb18030',
            'utf-16', 'utf-16-le', 'utf-16-be',
            'hz', 'iso-2022-cn', 'shift_jis', 'euc-cn'
        ]
        
        # Unicode 範圍
        self.cjk_ranges = [
            (0x4E00, 0x9FFF),   # CJK Unified Ideographs
            (0x3400, 0x4DBF),   # CJK Extension A
            (0x20000, 0x2A6DF), # CJK Extension B
            (0x2A700, 0x2B73F), # CJK Extension C
            (0x2B740, 0x2B81F), # CJK Extension D
            (0x2B820, 0x2CEAF), # CJK Extension E
            (0x2CEB0, 0x2EBEF), # CJK Extension F
            (0x30000, 0x3134F), # CJK Extension G
        ]
    
    def decode_all(self, text: str) -> Dict[str, str]:
        """嘗試所有解碼方法"""
        results = {}
        
        # 1. HTML 實體解碼
        html_decoded = self.decode_html_entities(text)
        if html_decoded != text:
            results['html_entities'] = html_decoded
        
        # 2. URL 解碼
        url_decoded = self.decode_url(text)
        if url_decoded != text:
            results['url_encoded'] = url_decoded
        
        # 3. Unicode 轉義解碼
        unicode_decoded = self.decode_unicode_escape(text)
        if unicode_decoded != text:
            results['unicode_escape'] = unicode_decoded
        
        # 4. Base64 解碼
        base64_results = self.decode_base64_variants(text)
        results.update(base64_results)
        
        # 5. 數字編碼解碼
        numeric_decoded = self.decode_numeric_entities(text)
        if numeric_decoded != text:
            results['numeric_entities'] = numeric_decoded
        
        # 6. 自定義混淆解碼
        custom_decoded = self.decode_custom_obfuscation(text)
        if custom_decoded != text:
            results['custom_obfuscation'] = custom_decoded
        
        # 7. 多層解碼
        multi_decoded = self.decode_multi_layer(text)
        if multi_decoded != text:
            results['multi_layer'] = multi_decoded
        
        return results
    
    def decode_html_entities(self, text: str) -> str:
        """解碼 HTML 實體"""
        try:
            # 標準 HTML 實體
            decoded = html.unescape(text)
            
            # 數字實體 (&#12345; 或 &#x3039;)
            decoded = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), decoded)
            decoded = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), decoded)
            
            return decoded
        except:
            return text
    
    def decode_url(self, text: str) -> str:
        """URL 解碼"""
        try:
            # 多次解碼（處理多層編碼）
            decoded = text
            for _ in range(3):
                new_decoded = urllib.parse.unquote(decoded)
                if new_decoded == decoded:
                    break
                decoded = new_decoded
            return decoded
        except:
            return text
    
    def decode_unicode_escape(self, text: str) -> str:
        """解碼 Unicode 轉義序列"""
        try:
            # \uXXXX 格式
            decoded = text.encode('utf-8').decode('unicode_escape')
            
            # \UXXXXXXXX 格式
            decoded = re.sub(
                r'\\U([0-9a-fA-F]{8})',
                lambda m: chr(int(m.group(1), 16)),
                decoded
            )
            
            return decoded
        except:
            return text
    
    def decode_base64_variants(self, text: str) -> Dict[str, str]:
        """嘗試各種 Base64 變體"""
        results = {}
        
        # 清理文本（移除空格、換行等）
        cleaned = re.sub(r'\s+', '', text)
        
        # Base64 變體
        variants = [
            ('standard', cleaned),
            ('url_safe', cleaned.replace('-', '+').replace('_', '/')),
            ('no_padding', cleaned + '=' * (4 - len(cleaned) % 4)),
        ]
        
        for name, variant in variants:
            for encoding in self.chinese_encodings:
                try:
                    decoded_bytes = base64.b64decode(variant)
                    decoded_text = decoded_bytes.decode(encoding, errors='ignore')
                    
                    # 檢查是否包含中文
                    if self.contains_chinese(decoded_text):
                        results[f'base64_{name}_{encoding}'] = decoded_text
                except:
                    continue
        
        return results
    
    def decode_numeric_entities(self, text: str) -> str:
        """解碼數字實體（如 Unicode 碼點）"""
        try:
            # 匹配各種數字格式
            patterns = [
                (r'\b(\d{4,5})\b', 10),  # 十進制
                (r'\b0x([0-9a-fA-F]+)\b', 16),  # 十六進制
                (r'\\x([0-9a-fA-F]{2})', 16),  # \xXX
                (r'%([0-9a-fA-F]{2})', 16),  # %XX
            ]
            
            decoded = text
            for pattern, base in patterns:
                def replace_func(m):
                    try:
                        code = int(m.group(1), base)
                        if self.is_cjk_codepoint(code):
                            return chr(code)
                    except:
                        pass
                    return m.group(0)
                
                decoded = re.sub(pattern, replace_func, decoded)
            
            return decoded
        except:
            return text
    
    def decode_custom_obfuscation(self, text: str) -> str:
        """解碼自定義混淆（如字符替換、位移等）"""
        try:
            decoded = text
            
            # 1. 字符替換映射
            # 常見的替換：數字/字母代替中文
            replacements = {
                '0': '零', '1': '一', '2': '二', '3': '三',
                '4': '四', '5': '五', '6': '六', '7': '七',
                '8': '八', '9': '九',
            }
            
            for old, new in replacements.items():
                decoded = decoded.replace(old, new)
            
            # 2. 字符位移（Caesar cipher 變體）
            # 嘗試不同的位移量
            for shift in [1, -1, 13, -13]:
                shifted = self.shift_unicode(decoded, shift)
                if self.contains_chinese(shifted) and shifted != decoded:
                    return shifted
            
            return decoded
        except:
            return text
    
    def decode_multi_layer(self, text: str) -> str:
        """多層解碼（組合多種編碼）"""
        try:
            decoded = text
            
            # 嘗試多種解碼組合
            decode_chain = [
                self.decode_url,
                self.decode_html_entities,
                self.decode_unicode_escape,
                self.decode_numeric_entities,
            ]
            
            # 最多嘗試 5 層
            for _ in range(5):
                changed = False
                for decode_func in decode_chain:
                    new_decoded = decode_func(decoded)
                    if new_decoded != decoded:
                        decoded = new_decoded
                        changed = True
                
                if not changed:
                    break
            
            return decoded
        except:
            return text
    
    def shift_unicode(self, text: str, shift: int) -> str:
        """Unicode 字符位移"""
        result = []
        for char in text:
            code = ord(char)
            new_code = code + shift
            
            # 確保在有效的 Unicode 範圍內
            if 0 <= new_code <= 0x10FFFF:
                result.append(chr(new_code))
            else:
                result.append(char)
        
        return ''.join(result)
    
    def is_cjk_codepoint(self, code: int) -> bool:
        """檢查是否為 CJK 字符碼點"""
        for start, end in self.cjk_ranges:
            if start <= code <= end:
                return True
        return False
    
    def contains_chinese(self, text: str) -> bool:
        """檢查文本是否包含中文"""
        chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\u2ceb0-\u2ebef\u30000-\u3134f]+')
        return bool(chinese_pattern.search(text))
    
    def extract_chinese(self, text: str) -> str:
        """提取所有中文字符"""
        chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u2a700-\u2b73f\u2b740-\u2b81f\u2b820-\u2ceaf\u2ceb0-\u2ebef\u30000-\u3134f]+')
        matches = chinese_pattern.findall(text)
        return ''.join(matches)

def decode_file(input_file: str, output_file: str = None):
    """解碼文件"""
    decoder = AdvancedDecoder()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"原始內容長度: {len(content)}")
    
    # 嘗試所有解碼方法
    results = decoder.decode_all(content)
    
    # 找出最佳結果（包含最多中文的）
    best_result = content
    best_chinese_count = len(decoder.extract_chinese(content))
    
    for method, decoded in results.items():
        chinese_text = decoder.extract_chinese(decoded)
        chinese_count = len(chinese_text)
        
        print(f"\n方法: {method}")
        print(f"中文字符數: {chinese_count}")
        print(f"預覽: {decoded[:200]}...")
        
        if chinese_count > best_chinese_count:
            best_result = decoded
            best_chinese_count = chinese_count
    
    # 保存結果
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(best_result)
        print(f"\n最佳結果已保存到: {output_file}")
        print(f"提取的中文字符數: {best_chinese_count}")
    
    return best_result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python advanced_decoder.py <輸入文件> [輸出文件]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    decode_file(input_file, output_file)
