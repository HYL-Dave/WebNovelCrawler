"""
通用 HTTP 工具：代理池管理與純 HTTP 反向 initTxt 抓取流程
"""
import re
import random
from urllib.parse import urlparse

import requests


def load_proxies(proxy_file='proxies.txt'):
    """從文件加載代理，每行一個，可有註釋#"""
    proxies = []
    with open(proxy_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            proxies.append(line)
    return proxies


def get_random_proxy(proxies):
    """隨機選擇一個代理，返回 None 表示不使用代理"""
    return random.choice(proxies) if proxies else None


def validate_proxy(proxy, test_url='http://httpbin.org/ip', timeout=5):
    """檢測單個代理是否可用"""
    if not proxy:
        return False
    try:
        resp = requests.get(test_url, proxies={'http': proxy, 'https': proxy}, timeout=timeout)
        return resp.ok
    except Exception:
        return False


def validate_proxies(proxy_list, test_url='http://httpbin.org/ip', timeout=5):
    """過濾掉不可用的代理"""
    return [p for p in proxy_list if validate_proxy(p, test_url, timeout)]


def extract_init_txt_url_http(page_url, proxies=None, timeout=10):
    """使用純 HTTP 方式解析頁面，提取 initTxt 動態加載的內容 URL"""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }
    proxy = get_random_proxy(proxies) if proxies is not None else None
    proxies_dict = {'http': proxy, 'https': proxy} if proxy else None
    resp = requests.get(page_url, headers=headers, proxies=proxies_dict, timeout=timeout)
    resp.raise_for_status()
    html = resp.text
    match = re.search(r'initTxt\((?:"|\')(.*?)(?:"|\')', html)
    if not match:
        raise ValueError(f"initTxt URL not found in page: {page_url}")
    url = match.group(1)
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        host = urlparse(page_url).netloc
        url = f'https://{host}{url}'
    return url


def fetch_initTxt_content_http(init_url, referer=None, proxies=None, timeout=15):
    """使用純 HTTP 方式下載 initTxt 指向的純文本內容"""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }
    if referer:
        headers['Referer'] = referer
    proxy = get_random_proxy(proxies) if proxies is not None else None
    proxies_dict = {'http': proxy, 'https': proxy} if proxy else None
    resp = requests.get(init_url, headers=headers, proxies=proxies_dict, timeout=timeout)
    resp.raise_for_status()
    data = resp.text
    # 處理 _txt_call 包裹的格式
    if data.startswith('_txt_call("') and data.endswith('")'):
        inner = data.split('_txt_call("', 1)[1].rsplit('")', 1)[0]
        return inner
    return data