"""Unit-тесты обработки ошибок клиента: токен не должен утекать в исключения.

Найдено независимым ревью ТЗ (2026-07-27): requests кладёт ПОЛНЫЙ URL в текст
HTTPError, а токен Bidease передаётся query-параметром `api-token` — значит любое
исключение (401, 400, таймаут) уносило секрет в логи вызывающего.
"""

import pytest
import requests

from bidease import get_campaigns_daily_stat

TOKEN = "super-secret-token-value"
URL_WITH_TOKEN = (
    "https://ui-api.bidease.com/api/reporting/v1/stats"
    f"?api-token={TOKEN}&fromdate=2026-07-21&todate=2026-07-23"
)


def _install(monkeypatch, *, status: int = None, exc: Exception = None):
    """Подменяет Session.get: либо HTTP-ответ с ошибочным статусом, либо исключение."""
    monkeypatch.setenv("API_TOKEN", TOKEN)

    def fake_get(self, url, params=None, timeout=None):
        if exc is not None:
            raise exc
        resp = requests.Response()
        resp.status_code = status
        resp.url = URL_WITH_TOKEN
        resp.reason = "Unauthorized" if status == 401 else "Bad Request"
        resp._content = b""
        return resp

    monkeypatch.setattr(requests.Session, "get", fake_get)


def test_http_error_does_not_leak_token(monkeypatch):
    """401 от API: токена нет ни в сообщении исключения, ни в его repr."""
    _install(monkeypatch, status=401)

    with pytest.raises(requests.HTTPError) as ei:
        get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert TOKEN not in str(ei.value)
    assert TOKEN not in repr(ei.value)
    assert "api-token=<redacted>" in str(ei.value)   # параметр виден, значение скрыто
    assert "401" in str(ei.value)                     # диагностика не потеряна


def test_http_error_keeps_response(monkeypatch):
    """Санитизация не должна ломать доступ к response (код статуса нужен вызывающему)."""
    _install(monkeypatch, status=400)

    with pytest.raises(requests.HTTPError) as ei:
        get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert ei.value.response is not None
    assert ei.value.response.status_code == 400


def test_connection_error_does_not_leak_token(monkeypatch):
    """Сетевые ошибки requests тоже несут URL — и тоже должны быть очищены."""
    _install(monkeypatch, exc=requests.ConnectionError(
        f"HTTPSConnectionPool: Max retries exceeded with url: {URL_WITH_TOKEN}"))

    with pytest.raises(requests.RequestException) as ei:
        get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert TOKEN not in str(ei.value)
