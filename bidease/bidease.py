"""Bidease Reporting API client.

Публичные функции, возвращающие pandas DataFrame:
- get_campaign_dict()                          — справочник кампаний из группировок отчёта
- get_campaigns_daily_stat(date_from, date_to) — дневная статистика по кампаниям
- get_creatives_daily_stat(date_from, date_to) — дневная статистика по креативам
- get_admin_audit(date_from, date_to)          — сводный аудит по дням (агрегат)

Учётные данные читаются из переменной окружения API_TOKEN
(или передаются явно в BideaseClient).

Сводка API — info/00_api_methods.md (единая точка правды по Bidease Reporting API).
"""

from __future__ import annotations

import io
import logging
import os
import time
from datetime import date, datetime, timedelta
from typing import Any

import sys

import pandas as pd
import requests

# Перенастройка кодировки — обязательно на Windows (cp1251/cp936 по умолчанию).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

# ── Константы ─────────────────────────────────────────────────────────────────

BASE_URL = "https://ui-api.bidease.com"
STATS_PATH = "/api/reporting/v1/stats"

HTTP_TIMEOUT_SEC = 30
RATE_LIMIT_RETRY_MAX = 5        # максимум повторов при 429 (лимиты API не документированы — защита)
RATE_LIMIT_BASE_SEC = 1         # начальная пауза при 429 (удваивается)

PERIOD_MAX_DAYS = 365           # период отчёта — в пределах 1 года от текущей даты (лимит API)
MAX_GROUPS = 7                  # максимум группировок (`group`) в одном запросе (лимит API)

# ⚠️ todate в API — ЭКСКЛЮЗИВНАЯ граница. Публичные функции принимают date_from/date_to
# ВКЛЮЧИТЕЛЬНО; в запрос передаётся todate = date_to + 1 день (см. _todate_exclusive).

# ── Колонки итоговых DataFrame — фиксируют порядок и состав полей ─────────────
# Предварительные наборы по manual_forms/03_ENTITY_FUNCTIONS.md;
# финализируются в спеках функций (Шаг 4).

CAMPAIGN_DICT_COLUMNS = [
    "campaign_id",       # CampaignID (CSV-колонка `campaignid`)
    "campaign_name",     # CampaignName (CSV-колонка `campaignname`)
    "advertiser_id",     # AdvertiserID (CSV-колонка `advertiserid`)
    "account_id",        # константа: 1
    "source_type_id",    # константа: 10 (решение проекта 2026-07-21)
    "product_id",        # ProductID — реальный ID продукта Bidease (не константа, см. спеку)
    "product_name",      # константа: "prod_test"
    "camp_type",         # константа: "camp_test"
    "camp_category",     # константа: "cat_test"
    "id_key_camp",       # вычисляется: "1_" + campaign_id
    "owner_id",          # константа: 1
]

# ⚠️ НДС (решение проекта 2026-07-21): spend в источнике — доллары БЕЗ НДС.
# Поэтому направление расчёта ОБРАТНОЕ avito:
#   costs_without_nds ← spend (float, округление до 2 знаков)
#   costs_nds = costs_without_nds * (1 + ставка_НДС); ставка по году даты строки:
#   год ≥ 2026 → 22% (множитель 1.22), ранее → 20% (множитель 1.20)

CAMPAIGNS_STAT_COLUMNS = [
    "date",                   # Day (CSV-колонка `day`)
    "campaign_id",            # CampaignID (CSV-колонка `campaignid`)
    "impressions",            # impressions
    "clicks",                 # clicks
    "costs_nds",              # costs_without_nds * (1 + ставка_НДС по году даты)
    "costs_without_nds",      # ← spend (доллары БЕЗ НДС; float, округление до 2 знаков)
    "ak",                     # константа: 0.5 (агентская комиссия)
    "costs_nds_ak",           # вычисляется: costs_nds * (1 + ak)
    "costs_without_nds_ak",   # вычисляется: costs_without_nds * (1 + ak)
    "account_id",             # константа: 1
    "source_type_id",         # константа: 10
    "id_key_camp",            # вычисляется: "1_" + campaign_id
]

CREATIVES_STAT_COLUMNS = [
    "date",                   # Day (CSV-колонка `day`)
    "campaign_id",            # CampaignID (CSV-колонка `campaignid`)
    "creative_id",            # CreativeID (CSV-колонка `creativeid`)
    "impressions",
    "clicks",
    "costs_nds",
    "costs_without_nds",
    "ak",
    "costs_nds_ak",
    "costs_without_nds_ak",
    "account_id",
    "source_type_id",
    "id_key_camp",
    "id_key_ad",              # вычисляется: id_key_camp + "_" + creative_id (групп в Bidease нет; решение 2026-07-21)
]

ADMIN_AUDIT_COLUMNS = [
    "date",
    "account_id",
    "source_type_id",
    "owner_id",
    "impressions",
    "clicks",
    "costs_nds",
    "costs_without_nds",
    "chef_flag",              # константа: 1 (дефолт)
]


# ── Клиент ────────────────────────────────────────────────────────────────────

class BideaseClient:
    """HTTP-клиент для Bidease Reporting API.

    Авторизация — статический API-токен в query-параметре `api-token`
    (выдаёт техподдержка/CSM Bidease; эндпоинтов выпуска/обновления нет).
    Все даты запроса и ответа — в таймзоне токена (по умолчанию UTC+0).
    """

    def __init__(self, api_token: str | None = None) -> None:
        self._api_token = api_token or os.environ.get("API_TOKEN")
        if not self._api_token:
            raise RuntimeError(
                "API-токен Bidease не предоставлен. "
                "Передайте api_token или задайте переменную окружения API_TOKEN."
            )
        self._session = requests.Session()

    # ── HTTP-обёртка ──────────────────────────────────────────────────────────

    def _get_report(self, params: list[tuple[str, Any]]) -> pd.DataFrame:
        """GET /api/reporting/v1/stats → DataFrame из CSV-ответа.

        params — список пар (ключ, значение); повторяемые параметры (`group`,
        `campaigns`, …) передаются несколькими парами с одним ключом.
        `api-token` добавляется автоматически.
        При 429 — экспоненциальный backoff (лимиты API не документированы — защита).
        """
        url = f"{BASE_URL}{STATS_PATH}"
        full_params: list[tuple[str, Any]] = [("api-token", self._api_token), *params]
        wait = RATE_LIMIT_BASE_SEC
        for attempt in range(RATE_LIMIT_RETRY_MAX + 1):
            try:
                resp = self._session.get(url, params=full_params, timeout=HTTP_TIMEOUT_SEC)
                resp.raise_for_status()
                return self._parse_csv(resp)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 429:
                    if attempt == RATE_LIMIT_RETRY_MAX:
                        raise
                    retry_after = int(exc.response.headers.get("Retry-After", wait))
                    logger.warning(
                        "429 Too Many Requests — ждём %d сек (попытка %d/%d)",
                        retry_after, attempt + 1, RATE_LIMIT_RETRY_MAX,
                    )
                    time.sleep(retry_after)
                    wait *= 2
                else:
                    raise
        raise RuntimeError("unreachable")  # pragma: no cover

    @staticmethod
    def _parse_csv(resp: requests.Response) -> pd.DataFrame:
        """Парсит CSV-тело ответа в DataFrame.

        Кодировка/разделитель в доках не зафиксированы (ожидается UTF-8 / `,`) —
        подтверждается фактом на первом smoke-тесте и фиксируется в info/.
        Пустой результат → пустой DataFrame.
        """
        text = resp.text
        if not text.strip():
            return pd.DataFrame()
        return pd.read_csv(io.StringIO(text))


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _todate_exclusive(date_to: str) -> str:
    """date_to (включительно, YYYY-MM-DD) → todate для API (эксклюзивно): +1 день."""
    d = datetime.strptime(date_to, "%Y-%m-%d").date()
    return (d + timedelta(days=1)).isoformat()


def _validate_period(date_from: str, date_to: str) -> None:
    """Проверяет период: формат дат, date_from ≤ date_to, в пределах 1 года от сегодня."""
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    if end < start:
        raise ValueError(f"date_to ({date_to}) раньше date_from ({date_from})")
    if start < date.today() - timedelta(days=PERIOD_MAX_DAYS):
        raise ValueError(
            f"date_from ({date_from}) выходит за лимит API: "
            f"период должен быть в пределах {PERIOD_MAX_DAYS} дней от текущей даты"
        )


# ── Публичные функции (стабы — реализуются на Шаге 4 через spec → plan → impl) ─

def get_campaign_dict() -> pd.DataFrame:
    """Справочник кампаний из группировок отчёта.

    GET /stats, group=CampaignID+CampaignName+AdvertiserID+ProductID,
    период — последний год (максимум API); метрики отбрасываются,
    дедупликация по campaign_id.

    Возвращает DataFrame с колонками CAMPAIGN_DICT_COLUMNS.
    """
    raise NotImplementedError("Реализуется на Шаге 4 (spec → plan → impl)")


def get_campaigns_daily_stat(date_from: str, date_to: str) -> pd.DataFrame:
    """Дневная статистика по кампаниям.

    GET /stats, group=Day+CampaignID — один запрос на весь период.
    date_from / date_to — включительно (todate API — эксклюзивная, учтено внутри).

    Возвращает DataFrame с колонками CAMPAIGNS_STAT_COLUMNS.
    """
    raise NotImplementedError("Реализуется на Шаге 4 (spec → plan → impl)")


def get_creatives_daily_stat(date_from: str, date_to: str) -> pd.DataFrame:
    """Дневная статистика по креативам.

    GET /stats, group=Day+CampaignID+CreativeID — один запрос на весь период.
    date_from / date_to — включительно (todate API — эксклюзивная, учтено внутри).

    Возвращает DataFrame с колонками CREATIVES_STAT_COLUMNS.
    """
    raise NotImplementedError("Реализуется на Шаге 4 (spec → plan → impl)")


def get_admin_audit(date_from: str, date_to: str) -> pd.DataFrame:
    """Сводный аудит по дням (admin_audit).

    Собственного эндпоинта нет — агрегат поверх get_campaigns_daily_stat:
    суммы impressions/clicks/costs_nds/costs_without_nds
    по date × account_id × source_type_id × owner_id; chef_flag = 1.

    Возвращает DataFrame с колонками ADMIN_AUDIT_COLUMNS.
    """
    raise NotImplementedError("Реализуется на Шаге 4 (spec → plan → impl)")
