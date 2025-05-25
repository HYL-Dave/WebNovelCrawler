import pytest

import http_utils


class DummyResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


@pytest.mark.parametrize('quote', ['"', "'"])
def test_extract_init_txt_url_http(monkeypatch, quote):
    # 模擬 HTML 中包含 initTxt 單/雙引號調用
    html = f'<script>initTxt({quote}//k.zashuwu.com/data/1.word{quote})</script>'
    monkeypatch.setattr(
        http_utils.requests, 'get',
        lambda url, headers=None, proxies=None, timeout=None: DummyResponse(html)
    )
    url = http_utils.extract_init_txt_url_http('https://m.zashuwu.com/xxx')
    assert url == 'https://k.zashuwu.com/data/1.word'


def test_extract_init_txt_url_http_not_found(monkeypatch):
    monkeypatch.setattr(
        http_utils.requests, 'get',
        lambda *args, **kwargs: DummyResponse('no init here')
    )
    with pytest.raises(ValueError):
        http_utils.extract_init_txt_url_http('https://example.com')


@pytest.mark.parametrize('data,expected', [
    ('_txt_call("HelloWorld")', 'HelloWorld'),
    ('Plain text data', 'Plain text data'),
])
def test_fetch_initTxt_content_http(monkeypatch, data, expected):
    monkeypatch.setattr(
        http_utils.requests, 'get',
        lambda url, headers=None, proxies=None, timeout=None: DummyResponse(data)
    )
    result = http_utils.fetch_initTxt_content_http('dummy_url', referer='ref', proxies=['p'], timeout=1)
    assert result == expected


def test_fetch_initTxt_content_http_no_proxy(monkeypatch):
    data = 'Test'
    monkeypatch.setattr(
        http_utils.requests, 'get',
        lambda url, headers=None, proxies=None, timeout=None: DummyResponse(data)
    )
    # 不傳 proxies 參數
    result = http_utils.fetch_initTxt_content_http('dummy_url')
    assert result == data


def test_fetch_initTxt_content_http_with_proxy(monkeypatch):
    data = 'X'
    # 模擬隨機選擇代理
    monkeypatch.setattr(http_utils, 'get_random_proxy', lambda proxies: 'proxy1')

    def fake_get(url, headers=None, proxies=None, timeout=None):
        assert proxies == {'http': 'proxy1', 'https': 'proxy1'}
        return DummyResponse(data)

    monkeypatch.setattr(http_utils.requests, 'get', fake_get)
    result = http_utils.fetch_initTxt_content_http('url', proxies=['p1', 'p2'])
    assert result == data