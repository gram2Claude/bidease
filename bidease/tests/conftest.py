"""Общая настройка pytest: sys.path + общий мок HTTP для всех тестов.

Мокается requests.Session.get настоящим requests.Response с байтовым телом и
ISO-8859-1 из заголовков (как реальный HTTPAdapter при Content-Type без charset,
факт API 2026-07-22) — так тесты стерегут форс UTF-8 в _parse_csv.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import requests


def mock_response(body: str) -> requests.Response:
    """Настоящий requests.Response: тело — UTF-8-байты, Content-Type БЕЗ charset (факт API)."""
    resp = requests.Response()
    resp.status_code = 200
    resp._content = body.encode("utf-8")
    resp.headers["Content-Type"] = "text/csv"
    # Как реальный HTTPAdapter.build_response: text/csv без charset → ISO-8859-1.
    # Без этого resp.encoding остаётся None, text декодируется по apparent_encoding
    # и тесты НЕ ловят регрессию форса UTF-8 в _parse_csv.
    resp.encoding = requests.utils.get_encoding_from_headers(resp.headers)
    return resp


@pytest.fixture
def api_env(monkeypatch):
    """API_TOKEN в окружении; установка подмены Session.get.

    Аргумент install(handler): handler — либо строка (одно CSV-тело на все запросы),
    либо callable(params) -> str (диспетчеризация по параметрам запроса).
    Возвращает список перехваченных вызовов [{"url": ..., "params": ...}, ...].
    """
    monkeypatch.setenv("API_TOKEN", "test-token")

    def install(handler):
        calls = []

        def fake_get(self, url, params=None, timeout=None):
            calls.append({"url": url, "params": params})
            body = handler(params) if callable(handler) else handler
            return mock_response(body)

        monkeypatch.setattr(requests.Session, "get", fake_get)
        return calls

    return install
