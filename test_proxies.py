import tempfile
import os
import pytest

import http_utils


def test_load_proxies(tmp_path):
    content = """
# comment line

http://user:pass@proxy1:1234
https://proxy2:5678
# another comment
"""
    file = tmp_path / "proxies.txt"
    file.write_text(content)
    proxies = http_utils.load_proxies(str(file))
    assert proxies == [
        "http://user:pass@proxy1:1234",
        "https://proxy2:5678",
    ]


def test_get_random_proxy_empty():
    assert http_utils.get_random_proxy([]) is None


def test_validate_proxy_invalid():
    # 使用不可達端口，預期返回 False
    assert not http_utils.validate_proxy("http://127.0.0.1:0", timeout=0.1)


def test_validate_proxies(monkeypatch):
    proxies = ["http://p1", "http://p2"]
    # 模擬只有 p2 可用
    monkeypatch.setattr(
        http_utils, 'validate_proxy', lambda p, test_url, timeout: p == "http://p2"
    )
    valid = http_utils.validate_proxies(proxies)
    assert valid == ["http://p2"]