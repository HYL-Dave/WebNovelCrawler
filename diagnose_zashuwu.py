"""
診斷 zashuwu.com 網站的反爬蟲機制
"""
import requests
import re
import time
import json
from urllib.parse import urljoin, urlparse
import subprocess
import sys


def test_basic_request(url):
    """測試基本的 HTTP 請求"""
    print(f"\n{'=' * 60}")
    print("1. 測試基本 HTTP 請求")
    print(f"{'=' * 60}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        print(f"狀態碼: {response.status_code}")
        print(f"是否重定向: {'是' if response.status_code in [301, 302, 303, 307, 308] else '否'}")

        if response.status_code in [301, 302, 303, 307, 308]:
            print(f"重定向到: {response.headers.get('Location', 'N/A')}")

        print(f"響應大小: {len(response.content)} bytes")

        # 檢查是否有反爬蟲標記
        content = response.text.lower()
        anti_bot_signs = ['captcha', 'verify', 'robot', '驗證', '機器人', 'forbidden', '403']
        detected_signs = [sign for sign in anti_bot_signs if sign in content]

        if detected_signs:
            print(f"⚠️  檢測到反爬蟲標記: {detected_signs}")
        else:
            print("✓ 未檢測到明顯的反爬蟲標記")

        return response

    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return None


def extract_init_txt_url(html):
    """從 HTML 中提取 initTxt URL"""
    print(f"\n{'=' * 60}")
    print("2. 提取 initTxt URL")
    print(f"{'=' * 60}")

    # 多種匹配模式
    patterns = [
        r'initTxt\s*\(\s*["\']([^"\']+)["\']\s*\)',
        r'initTxt\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        r'loadTxt\s*\(\s*["\']([^"\']+)["\']\s*\)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"✓ 找到匹配: {pattern}")
            if isinstance(matches[0], tuple):
                txt_url = matches[0][0]
            else:
                txt_url = matches[0]

            # 處理相對 URL
            if txt_url.startswith('//'):
                txt_url = 'https:' + txt_url
            elif txt_url.startswith('/'):
                txt_url = 'https://m.zashuwu.com' + txt_url

            print(f"提取的 URL: {txt_url}")
            return txt_url

    print("❌ 未找到 initTxt URL")

    # 顯示所有 script 標籤的內容摘要
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"\n找到 {len(scripts)} 個 script 標籤")

    for i, script in enumerate(scripts[:5]):  # 只顯示前5個
        if 'txt' in script.lower() or 'init' in script.lower():
            print(f"\nScript {i + 1} (包含 txt/init 關鍵字):")
            print(script[:200] + "..." if len(script) > 200 else script)

    return None


def test_txt_api(txt_url, referer):
    """測試 txt API"""
    print(f"\n{'=' * 60}")
    print("3. 測試 TXT API")
    print(f"{'=' * 60}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': referer,
        'Accept': '*/*',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br'
    }

    try:
        response = requests.get(txt_url, headers=headers, timeout=10)
        print(f"狀態碼: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"響應大小: {len(response.content)} bytes")

        content = response.text
        print(f"\n響應內容前200字符:")
        print(content[:200])

        # 檢查內容格式
        if content.startswith('_txt_call('):
            print("\n✓ 檢測到 _txt_call 格式")

            # 嘗試提取內容
            match = re.match(r'_txt_call\("(.*)"\)', content, re.DOTALL)
            if match:
                inner_content = match.group(1)
                print(f"內部內容長度: {len(inner_content)}")
                print(f"內部內容前100字符: {inner_content[:100]}")

                # 分析編碼
                if '\\u' in inner_content[:100]:
                    print("✓ 檢測到 Unicode 轉義")
                    try:
                        decoded = inner_content.encode().decode('unicode_escape')
                        print(f"解碼後前200字符: {decoded[:200]}")
                        return decoded
                    except Exception as e:
                        print(f"Unicode 解碼失敗: {e}")

                return inner_content
        else:
            print("✗ 不是 _txt_call 格式")
            return content

    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return None


def test_with_session(url):
    """使用會話測試"""
    print(f"\n{'=' * 60}")
    print("4. 使用會話測試")
    print(f"{'=' * 60}")

    session = requests.Session()

    # 設置通用 headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    })

    # 先訪問主頁建立會話
    print("訪問主頁建立會話...")
    try:
        homepage = session.get('https://m.zashuwu.com/', timeout=10)
        print(f"主頁狀態碼: {homepage.status_code}")
        print(f"Cookies: {dict(session.cookies)}")
    except Exception as e:
        print(f"訪問主頁失敗: {e}")

    # 訪問章節頁面
    print(f"\n訪問章節頁面: {url}")
    try:
        response = session.get(url, timeout=10)
        print(f"狀態碼: {response.status_code}")

        # 提取 initTxt URL
        txt_url = extract_init_txt_url(response.text)

        if txt_url:
            # 使用同一會話獲取內容
            print(f"\n使用會話獲取內容...")
            txt_response = session.get(txt_url, timeout=10)
            print(f"TXT API 狀態碼: {txt_response.status_code}")
            return txt_response.text

    except Exception as e:
        print(f"請求失敗: {e}")

    return None


def test_with_real_browser_headers(url):
    """使用真實瀏覽器的完整請求頭"""
    print(f"\n{'=' * 60}")
    print("5. 使用真實瀏覽器請求頭")
    print(f"{'=' * 60}")

    # 從真實瀏覽器複製的完整請求頭
    headers = {
        'Host': 'm.zashuwu.com',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8,ja;q=0.7'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"狀態碼: {response.status_code}")
        print(f"響應大小: {len(response.content)} bytes")

        # 檢查響應內容
        if '葉洵' in response.text or '秦王' in response.text:
            print("✓ 檢測到小說內容關鍵詞")
        else:
            print("✗ 未檢測到小說內容關鍵詞")

        return response

    except Exception as e:
        print(f"請求失敗: {e}")
        return None


def diagnose(url):
    """執行完整診斷"""
    print(f"診斷 URL: {url}")
    print(f"時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 基本請求測試
    response = test_basic_request(url)

    if response and response.status_code == 200:
        # 2. 提取 initTxt URL
        txt_url = extract_init_txt_url(response.text)

        if txt_url:
            # 3. 測試 txt API
            content = test_txt_api(txt_url, url)

            if content:
                # 保存結果
                with open('diagnosis_result.txt', 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"\n✓ 內容已保存到 diagnosis_result.txt")

    # 4. 使用會話測試
    session_content = test_with_session(url)

    # 5. 使用真實瀏覽器頭測試
    browser_response = test_with_real_browser_headers(url)

    # 總結
    print(f"\n{'=' * 60}")
    print("診斷總結")
    print(f"{'=' * 60}")

    print("\n可能的解決方案:")
    print("1. 使用代理池避免 IP 限制")
    print("2. 降低請求頻率")
    print("3. 使用真實瀏覽器 User-Agent 和完整請求頭")
    print("4. 維持會話並使用 cookies")
    print("5. 分析 JavaScript 解密算法")
    print("6. 考慮使用付費 API 或與網站合作")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://m.zashuwu.com/wen/2vFm/1.html"

    diagnose(url)