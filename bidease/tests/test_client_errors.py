"""Unit-тесты обработки ошибок клиента: токен не должен утекать в исключения.

Найдено независимым ревью ТЗ (2026-07-27): requests кладёт ПОЛНЫЙ URL в текст
HTTPError, а токен Bidease передаётся query-параметром `api-token` — значит любое
исключение (401, 400, таймаут) уносило секрет в логи вызывающего.
"""

import pytest
import requests

from bidease import RATE_LIMIT_RETRY_MAX, _redact, get_campaigns_daily_stat

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


def test_retry_after_http_date_does_not_crash(monkeypatch, capsys):
    """429 с Retry-After в формате HTTP-date не должен ронять выгрузку.

    По RFC заголовок бывает и числом секунд, и датой. Эталон читал его только как
    число — на дате падал ValueError вместо backoff (находка ревью 2026-07-27).
    """
    monkeypatch.setenv("API_TOKEN", TOKEN)
    monkeypatch.setattr("bidease.time.sleep", lambda _s: None)   # без реальных пауз

    calls = {"n": 0}
    body = ("conversions,spend,impressions,clicks,day,campaignid\n"
            "0,1.5,10,2,07/21/2026 00:00:00,154369\n")

    def fake_get(self, url, params=None, timeout=None):
        calls["n"] += 1
        resp = requests.Response()
        resp.url = URL_WITH_TOKEN
        if calls["n"] == 1:                       # первый ответ — 429 с датой
            resp.status_code = 429
            resp.reason = "Too Many Requests"
            resp.headers["Retry-After"] = "Wed, 21 Oct 2026 07:28:00 GMT"
            resp._content = b""
        else:                                     # повтор — успех
            resp.status_code = 200
            resp.headers["Content-Type"] = "text/csv"
            resp._content = body.encode("utf-8")
        return resp

    monkeypatch.setattr(requests.Session, "get", fake_get)

    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert calls["n"] == 2                        # был ровно один повтор
    assert len(df) == 1 and df.iloc[0]["costs_usd"] == 1.5


def test_connection_error_does_not_leak_token(monkeypatch):
    """Сетевые ошибки requests тоже несут URL — и тоже должны быть очищены."""
    _install(monkeypatch, exc=requests.ConnectionError(
        f"HTTPSConnectionPool: Max retries exceeded with url: {URL_WITH_TOKEN}"))

    with pytest.raises(requests.RequestException) as ei:
        get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert TOKEN not in str(ei.value)


@pytest.mark.parametrize("header, expected_sleep", [
    ("-1", 0),          # отрицательное: time.sleep(-1) роняет выгрузку
    ("86400", 300),     # сутки: пауза ограничена сверху
    ("2", 2),           # нормальное значение проходит как есть
])
def test_retry_after_is_clamped(monkeypatch, header, expected_sleep):
    """Retry-After — недоверенный ввод: не роняет процесс и не усыпляет его надолго."""
    monkeypatch.setenv("API_TOKEN", TOKEN)
    slept = []
    monkeypatch.setattr("bidease.time.sleep", lambda s: slept.append(s))

    calls = {"n": 0}
    body = ("conversions,spend,impressions,clicks,day,campaignid\n"
            "0,1.5,10,2,07/21/2026 00:00:00,154369\n")

    def fake_get(self, url, params=None, timeout=None):
        calls["n"] += 1
        resp = requests.Response()
        resp.url = URL_WITH_TOKEN
        if calls["n"] == 1:
            resp.status_code = 429
            resp.reason = "Too Many Requests"
            resp.headers["Retry-After"] = header
            resp._content = b""
        else:
            resp.status_code = 200
            resp.headers["Content-Type"] = "text/csv"
            resp._content = body.encode("utf-8")
        return resp

    monkeypatch.setattr(requests.Session, "get", fake_get)

    df = get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert len(df) == 1                      # выгрузка дошла до конца
    assert slept == [expected_sleep]


def test_429_retries_exhausted_does_not_leak_token(monkeypatch):
    """Отдельная ветка: токен маскируется и когда повторы при 429 исчерпаны."""
    monkeypatch.setenv("API_TOKEN", TOKEN)
    monkeypatch.setattr("bidease.time.sleep", lambda _s: None)

    calls = {"n": 0}

    def always_429(self, url, params=None, timeout=None):
        calls["n"] += 1
        resp = requests.Response()
        resp.status_code = 429
        resp.reason = "Too Many Requests"
        resp.url = URL_WITH_TOKEN
        resp._content = b""
        return resp

    monkeypatch.setattr(requests.Session, "get", always_429)

    with pytest.raises(requests.HTTPError) as ei:
        get_campaigns_daily_stat("2026-07-21", "2026-07-22")

    assert TOKEN not in str(ei.value)
    assert calls["n"] == RATE_LIMIT_RETRY_MAX + 1      # исходный вызов + все повторы


@pytest.mark.parametrize("text, expected_absent", [
    (f"for url: https://x/stats?fromdate=2026-07-21&api-token={TOKEN}", TOKEN),   # токен последним
    (f"https://x/stats?api_token={TOKEN}&group=Day", TOKEN),                      # через подчёркивание
    (f"https://x/stats?API-TOKEN={TOKEN}", TOKEN),                                # верхний регистр
    (f'"url": "https://x/stats?api-token={TOKEN}"', TOKEN),                       # в кавычках (JSON-лог)
])
def test_redact_covers_token_forms(text, expected_absent):
    """_redact должен ловить токен в разных формах записи параметра и позициях."""
    out = _redact(text)
    assert expected_absent not in out
    assert "<redacted>" in out
