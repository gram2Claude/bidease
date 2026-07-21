"""{API_NAME} API client.

Публичные функции, возвращающие pandas DataFrame:
- {FUNCTION_1_NAME}()                            — {FN_1_ONELINER}
- {FUNCTION_2_NAME}(date_from, date_to)           — {FN_2_ONELINER}
# Добавь строки для каждой дополнительной функции

Учётные данные читаются из переменных окружения {ENV_VAR_1} и {ENV_VAR_2}
(или передаются явно в {CLASS_NAME}).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Iterable

import sys

import pandas as pd
import requests
from tqdm.auto import tqdm

# Перенастройка кодировки — обязательно на Windows (cp1251/cp936 по умолчанию).
# Удали этот блок только если данные гарантированно ASCII или развёртывание не на Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

# ── Константы ─────────────────────────────────────────────────────────────────

BASE_URL = "{BASE_URL}"
BATCH_SIZE = {BATCH_SIZE}              # максимум сущностей в одном запросе (ограничение API)
# Правило запроса: статистика всегда запрашивается по 1 дню за раз (dateFrom == dateTo).
# Исключение: охват (reach) — запрашивается кумулятивно за [global_start_date, D] без разбивки по дням.
HTTP_TIMEOUT_SEC = {HTTP_TIMEOUT_SEC}
RATE_LIMIT_RETRY_MAX = {RATE_LIMIT_RETRY_MAX}   # максимум повторов при 429
RATE_LIMIT_BASE_SEC = {RATE_LIMIT_BASE_SEC}      # начальная пауза при 429 (удваивается)

# ── [ASYNC ONLY] Удали эти константы если API синхронный ──────────────────────
POLL_INTERVAL_SEC = {POLL_INTERVAL_SEC}          # пауза между проверками готовности отчёта
POLL_MAX_ATTEMPTS = {POLL_MAX_ATTEMPTS}          # макс. попыток (~{POLL_MAX_ATTEMPTS} * {POLL_INTERVAL_SEC} сек)
MAX_CONCURRENT = {MAX_CONCURRENT}               # макс. одновременных задач генерации (ограничение API)
MIN_SUBMIT_INTERVAL_SEC = 3             # минимум между POST submit (защита от burst rate limit)
# ── [/ASYNC ONLY] ─────────────────────────────────────────────────────────────

# ── [OAUTH ONLY] Удали эту константу если используется API-ключ ───────────────
TOKEN_REFRESH_LEEWAY_SEC = 60           # обновлять токен за 60 сек до истечения
# ── [/OAUTH ONLY] ────────────────────────────────────────────────────────────

# ── Колонки итоговых DataFrame — фиксируют порядок и состав полей ─────────────

{ENTITY_NAME_UPPER}_DICT_COLUMNS = [
    "{ENTITY_NAME}_id",
    "{ENTITY_NAME}_name",
    "account_id",       # константа: 1
    "source_type_id",   # константа: 9
    "product_id",       # константа: 1
    "product_name",     # константа: "prod_test"
    "camp_type",        # константа: "camp_test"
    "camp_category",    # константа: "cat_test"
    "id_key_camp",      # вычисляется: "1_" + {ENTITY_NAME}_id
    "owner_id",         # константа: 1
    # Добавь дополнительные поля справочника если нужно (state, budget, start_date и т.д.)
]

{ENTITY_NAME_UPPER}_STAT_COLUMNS = [
    "date",
    "{ENTITY_NAME}_id",
    # Добавь метрики: views, clicks, costs_nds и т.д.
    "costs_without_nds",      # costs_nds / (1+НДС); ставка по году даты: 2026+ → 22%, ранее → 20%
    "ak",                     # константа: 0.5 (агентская комиссия)
    "costs_nds_ak",           # вычисляется: costs_nds * (1 + ak)
    "costs_without_nds_ak",   # вычисляется: costs_without_nds * (1 + ak)
    "account_id",             # константа: 1
    "source_type_id",         # константа: 9
    "id_key_camp",            # вычисляется: "1_" + {ENTITY_NAME}_id
]

# Добавь константы колонок для каждой дополнительной функции.
# Для ad-level таблиц (VIDEO, REACH_ADS и т.п.) включи "id_key_ad" последним:
# {ENTITY_NAME_UPPER}_VIDEO_COLUMNS = [..., "id_key_camp", "id_key_ad"]
# {ENTITY_NAME_UPPER}_REACH_COLUMNS = [..., "id_key_camp", "id_key_ad"]


# ── Клиент ────────────────────────────────────────────────────────────────────

class {CLASS_NAME}:
    """HTTP-клиент для {API_NAME} с автоматической авторизацией.

    # [OAUTH ONLY] Авторизация — OAuth 2.0 grant_type=client_credentials.
    # Токен живёт ~{TOKEN_TTL_SEC} сек; клиент сам запрашивает новый при истечении.

    # [API KEY ONLY] Авторизация — статический API-ключ в заголовке {API_KEY_HEADER}.
    """

    def __init__(
        self,
        # ── [OAUTH ONLY] Удали эти параметры если используется API-ключ ──────
        client_id: str | None = None,
        client_secret: str | None = None,
        # ── [/OAUTH ONLY] ────────────────────────────────────────────────────
        # ── [API KEY ONLY] Удали этот параметр если используется OAuth ───────
        api_key: str | None = None,
        # ── [/API KEY ONLY] ──────────────────────────────────────────────────
    ) -> None:
        # ── [OAUTH ONLY] ──────────────────────────────────────────────────────
        self._client_id = client_id or os.environ.get("{ENV_VAR_1}")
        self._client_secret = client_secret or os.environ.get("{ENV_VAR_2}")
        if not self._client_id or not self._client_secret:
            raise RuntimeError(
                "Учётные данные {API_NAME} не предоставлены. "
                "Передайте client_id/client_secret или задайте "
                "{ENV_VAR_1} и {ENV_VAR_2}."
            )
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        # ── [/OAUTH ONLY] ─────────────────────────────────────────────────────

        # ── [API KEY ONLY] ────────────────────────────────────────────────────
        self._api_key = api_key or os.environ.get("{ENV_VAR_1}")
        if not self._api_key:
            raise RuntimeError(
                "API-ключ {API_NAME} не предоставлен. "
                "Передайте api_key или задайте {ENV_VAR_1}."
            )
        # ── [/API KEY ONLY] ───────────────────────────────────────────────────

        self._session = requests.Session()

        # ── [ASYNC ONLY] ──────────────────────────────────────────────────────
        # _active_uuids — UUID submitted-but-not-yet-finalized отчётов.
        # _last_submit_ts — таймштамп последнего submit для пейсинга.
        self._active_uuids: set[str] = set()
        self._last_submit_ts: float = 0.0
        # ── [/ASYNC ONLY] ─────────────────────────────────────────────────────

    # ── [OAUTH ONLY] Авторизация ───────────────────────────────────────────────

    def _refresh_token(self) -> None:
        url = f"{BASE_URL}{TOKEN_PATH}"
        payload = {
            "{CLIENT_ID_PARAM}": self._client_id,
            "{CLIENT_SECRET_PARAM}": self._client_secret,
            "grant_type": "client_credentials",
        }
        resp = self._session.post(url, json=payload, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        expires_in = int(data.get("expires_in", {TOKEN_TTL_SEC}))
        self._token_expires_at = time.time() + expires_in

    def _ensure_token(self) -> None:
        if self._token is None or time.time() >= self._token_expires_at - TOKEN_REFRESH_LEEWAY_SEC:
            self._refresh_token()

    # ── [/OAUTH ONLY] ─────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        # ── [OAUTH ONLY] ──────────────────────────────────────────────────────
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        # ── [/OAUTH ONLY] ─────────────────────────────────────────────────────

        # ── [API KEY ONLY] ────────────────────────────────────────────────────
        return {
            "{API_KEY_HEADER}": self._api_key,
            "Accept": "application/json",
        }
        # ── [/API KEY ONLY] ───────────────────────────────────────────────────

    # ── HTTP-обёртки ──────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{BASE_URL}{path}"
        resp = self._session.get(
            url, headers=self._headers(), params=params, timeout=HTTP_TIMEOUT_SEC
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        url = f"{BASE_URL}{path}"
        headers = self._headers() | {"Content-Type": "application/json"}
        # 429 retry с экспоненциальным backoff
        wait = RATE_LIMIT_BASE_SEC
        for attempt in range(RATE_LIMIT_RETRY_MAX + 1):
            try:
                resp = self._session.post(url, headers=headers, json=body, timeout=HTTP_TIMEOUT_SEC)
                resp.raise_for_status()
                return resp.json()
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

    # ── Получение списка сущностей ────────────────────────────────────────────
    # ── [BATCHING — удали этот метод если API не требует списка сущностей] ────

    def _fetch_all_{ENTITY_NAME}s(self) -> list[dict[str, Any]]:
        """Загружает список всех {ENTITY_NAME} аккаунта.

        Запрос: GET {ENTITY_LIST_PATH}
        """
        data = self._get("{ENTITY_LIST_PATH}")
        # Обработка envelope — подставь нужный ключ или убери если ответ — сразу список
        if isinstance(data, dict):
            return data.get("{ENTITY_ENVELOPE_KEY}") or []
        if isinstance(data, list):
            return data
        return []

    # ── [/BATCHING] ───────────────────────────────────────────────────────────

    # ── [ASYNC ONLY] Управление асинхронными отчётами ─────────────────────────

    def _submit_report(
        self,
        entity_ids: list[int],
        date_from: str,
        date_to: str,
        group_by: str,
        path: str = "{SUBMIT_PATH}",
    ) -> str:
        """Отправляет запрос на формирование отчёта, возвращает UUID.

        При ошибке 429 повторяет запрос с экспоненциальным backoff.
        Ждёт освобождения слота если достигнут лимит MAX_CONCURRENT.
        """
        body = {
            # Подставь нужные поля тела запроса из анкеты Fn6
            "{ENTITY_ID_FIELD}s": entity_ids,
            "dateFrom": date_from,
            "dateTo": date_to,
            "groupBy": group_by,
        }
        while len(self._active_uuids) >= MAX_CONCURRENT:
            self._wait_for_free_slot()
        elapsed = time.time() - self._last_submit_ts
        if elapsed < MIN_SUBMIT_INTERVAL_SEC:
            time.sleep(MIN_SUBMIT_INTERVAL_SEC - elapsed)
        data = self._post(path, body)
        self._last_submit_ts = time.time()
        uuid = data.get("UUID") or data.get("uuid")
        if not uuid:
            raise RuntimeError(f"Запрос отчёта не вернул UUID: {data!r}")
        self._active_uuids.add(uuid)
        return uuid

    def _wait_for_free_slot(self) -> None:
        """Ждёт, пока хотя бы один активный UUID не финализируется (OK/ERROR)."""
        while self._active_uuids:
            for uuid in list(self._active_uuids):
                try:
                    data = self._get(f"{POLL_PATH_PREFIX}{uuid}")
                except requests.HTTPError:
                    self._active_uuids.discard(uuid)
                    return
                state = (data.get("{STATUS_FIELD}") or "").upper()
                if state in ("{STATUS_DONE}", "{STATUS_ERROR}"):
                    self._active_uuids.discard(uuid)
                    return
            time.sleep(POLL_INTERVAL_SEC)

    def _poll_uuid(self, uuid: str) -> None:
        """Ожидает готовности отчёта по UUID. Бросает RuntimeError при ошибке/таймауте."""
        try:
            for _ in range(POLL_MAX_ATTEMPTS):
                data = self._get(f"{POLL_PATH_PREFIX}{uuid}")
                state = (data.get("{STATUS_FIELD}") or "").upper()
                if state == "{STATUS_DONE}":
                    return
                if state == "{STATUS_ERROR}":
                    raise RuntimeError(f"Отчёт {uuid} завершился с ошибкой: {data!r}")
                time.sleep(POLL_INTERVAL_SEC)
            raise RuntimeError(f"Таймаут ожидания отчёта {uuid} после {POLL_MAX_ATTEMPTS} попыток")
        finally:
            self._active_uuids.discard(uuid)

    def _download_report(self, uuid: str) -> dict[str, Any]:
        """Скачивает готовый отчёт по UUID."""
        data = self._get("{DOWNLOAD_PATH}", params={"UUID": uuid})
        return data if isinstance(data, dict) else {}

    # ── [/ASYNC ONLY] ─────────────────────────────────────────────────────────

    # ── Оркестраторы данных ───────────────────────────────────────────────────

    # ── [ASYNC ONLY] ──────────────────────────────────────────────────────────
    def _fetch_{ENTITY_NAME}_stat_for_period(
        self, date_from: str, date_to: str, group_by: str
    ) -> list[dict[str, Any]]:
        """Загружает статистику за период и возвращает нормализованный список строк.

        Алгоритм:
          1. Получить список всех {ENTITY_NAME} аккаунта.
          2. Разбить на батчи по BATCH_SIZE (ограничение API).
          3. Для каждой даты и батча: submit → poll → download → парсинг.
          4. Пропустить батч с предупреждением при ошибке API.
        """
        entities = self._fetch_all_{ENTITY_NAME}s()
        entity_ids = [e["{ENTITY_ID_FIELD}"] for e in entities if e.get("{ENTITY_ID_FIELD}") is not None]
        if not entity_ids:
            return []

        entity_name_by_id = {
            str(e["{ENTITY_ID_FIELD}"]): _pick(e, "{ENTITY_NAME_FIELD_1}", "{ENTITY_NAME_FIELD_2}")
            for e in entities
        }

        days = _date_range(date_from, date_to)
        batches = list(_chunks(entity_ids, BATCH_SIZE))
        all_rows: list[dict[str, Any]] = []

        progress = tqdm(total=len(days) * len(batches), desc="Загрузка статистики", unit="запрос")

        for day in days:
            for i, batch in enumerate(batches, 1):
                progress.set_postfix_str(f"{day}  батч {i}/{len(batches)}")
                try:
                    uuid = self._submit_report(batch, day, day, group_by)
                    self._poll_uuid(uuid)
                    report_data = self._download_report(uuid)

                    for eid_str, entity_data in report_data.items():
                        report = entity_data.get("report", {})
                        entity_name = entity_name_by_id.get(eid_str)

                        # Подставь логику парсинга под структуру ответа твоего API.
                        # Пример для group_by=DATE (итоги по сущности за день):
                        totals = report.get("totals", {})
                        if _any_nonzero(totals, ("views", "clicks")):
                            all_rows.append({
                                "date": day,
                                "{ENTITY_NAME}_id": eid_str,
                                "{ENTITY_NAME}_name": entity_name,
                                # Добавь нужные метрики:
                                "views": _parse_num(totals.get("views")),
                                "clicks": _parse_num(totals.get("clicks")),
                                "costs_nds": _parse_num(totals.get("moneySpent")),
                            })
                except (requests.HTTPError, RuntimeError) as exc:
                    logger.warning(
                        "Пропущен батч (день=%s, entity=%s): %s", day, batch, exc,
                    )
                finally:
                    progress.update(1)

        progress.close()
        return all_rows
    # ── [/ASYNC ONLY] ─────────────────────────────────────────────────────────

    # ── [SYNC ONLY] ───────────────────────────────────────────────────────────
    def _fetch_{ENTITY_NAME}_data(
        self, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Прямой запрос данных без UUID.

        Подставь логику пагинации если API возвращает данные постранично.
        """
        data = self._get("{SYNC_DATA_PATH}", params=params)
        # Разверни envelope если нужно
        if isinstance(data, dict):
            return data.get("data") or data.get("items") or data.get("results") or []
        if isinstance(data, list):
            return data
        return []
    # ── [/SYNC ONLY] ──────────────────────────────────────────────────────────


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _date_range(date_from: str, date_to: str) -> list[str]:
    """Генерирует список дат от date_from до date_to включительно (формат YYYY-MM-DD)."""
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    if end < start:
        raise ValueError(f"date_to ({date_to}) раньше date_from ({date_from})")
    days = []
    cur = start
    while cur <= end:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def _chunks(seq: list, size: int) -> Iterable[list]:
    """Разбивает список на подсписки заданного размера."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _pick(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Возвращает значение первого найденного ключа из словаря.

    Используется когда одно и то же поле может называться по-разному
    в разных эндпоинтах API — перечисляй все варианты имён.
    """
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def _parse_num(value: Any) -> float | None:
    """Конвертирует числа из формата API в float.

    {NUM_FORMAT_NOTE}
    Пример: «25833,00» → 25833.0 (при запятой как разделителе).
    Удали замену запятой если API возвращает числа с точкой или как числа, а не строки.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _parse_date_str(value: str) -> str:
    """Приводит дату из формата API к ISO-формату YYYY-MM-DD.

    {DATE_FORMAT_NOTE}
    Удали эту функцию если API всегда возвращает даты в ISO 8601.
    """
    if not value or len(value) < 10:
        return value
    if value[2] == ".":   # DD.MM.YYYY
        return f"{value[6:10]}-{value[3:5]}-{value[0:2]}"
    if value[2] == "/":   # MM/DD/YYYY
        return f"{value[6:10]}-{value[0:2]}-{value[3:5]}"
    return value           # уже YYYY-MM-DD


def _any_nonzero(d: dict[str, Any], keys: tuple[str, ...]) -> bool:
    """Возвращает True если хотя бы одно из указанных полей имеет ненулевое значение."""
    return any(_parse_num(d.get(k)) for k in keys)


# ── Публичные функции ─────────────────────────────────────────────────────────

def {FUNCTION_1_NAME}() -> pd.DataFrame:
    """{FN_1_ONELINER}

    Возвращает DataFrame с колонками:
        {DF_1_COLUMNS_DOC}
    """
    client = {CLASS_NAME}()
    entities = client._fetch_all_{ENTITY_NAME}s()
    if not entities:
        return pd.DataFrame(columns={ENTITY_NAME_UPPER}_DICT_COLUMNS)

    df = pd.DataFrame([
        {
            "{ENTITY_NAME}_id": _pick(e, "{ENTITY_ID_FIELD}"),
            "{ENTITY_NAME}_name": _pick(e, "{ENTITY_NAME_FIELD_1}", "{ENTITY_NAME_FIELD_2}"),
            # Добавь нужные поля справочника
        }
        for e in entities
    ])
    df = df.dropna(subset=["{ENTITY_NAME}_id"]).drop_duplicates(subset=["{ENTITY_NAME}_id"])
    df["account_id"] = 1
    df["source_type_id"] = 9
    df["product_id"] = 1
    df["product_name"] = "prod_test"
    df["camp_type"] = "camp_test"
    df["camp_category"] = "cat_test"
    df["id_key_camp"] = "1_" + df["{ENTITY_NAME}_id"].astype(str)
    df["owner_id"] = 1
    return df.reindex(columns={ENTITY_NAME_UPPER}_DICT_COLUMNS).reset_index(drop=True)


def {FUNCTION_2_NAME}(date_from: str, date_to: str) -> pd.DataFrame:
    """{FN_2_ONELINER}

    Параметры:
        date_from — начало периода, формат YYYY-MM-DD (например, «2026-01-01»)
        date_to   — конец периода,  формат YYYY-MM-DD (например, «2026-01-31»)

    Возвращает DataFrame с колонками:
        {DF_2_COLUMNS_DOC}
    """
    client = {CLASS_NAME}()

    # ── [ASYNC ONLY] ──────────────────────────────────────────────────────────
    rows = client._fetch_{ENTITY_NAME}_stat_for_period(date_from, date_to, group_by="DATE")
    # ── [/ASYNC ONLY] ─────────────────────────────────────────────────────────

    # ── [SYNC ONLY] ───────────────────────────────────────────────────────────
    rows = client._fetch_{ENTITY_NAME}_data({"dateFrom": date_from, "dateTo": date_to})
    # ── [/SYNC ONLY] ──────────────────────────────────────────────────────────

    if not rows:
        return pd.DataFrame(columns={ENTITY_NAME_UPPER}_STAT_COLUMNS)
    df = pd.DataFrame(rows)
    # costs_nds — десятичный тип, округление до 2 знаков (до вычисления производных)
    df["costs_nds"] = pd.to_numeric(df["costs_nds"], errors="coerce").astype(float).round(2)
    # Расход без НДС: ставка по году даты строки — year >= 2026 → /1.22 (22%), иначе /1.20 (20%)
    _vat_div = pd.Series(1.20, index=df.index, dtype="float64")
    _vat_div[pd.to_numeric(df["date"].astype(str).str[:4], errors="coerce") >= 2026] = 1.22
    df["costs_without_nds"] = df["costs_nds"] / _vat_div
    df["ak"] = 0.5
    df["costs_nds_ak"] = df["costs_nds"] * (1 + 0.5)
    df["costs_without_nds_ak"] = df["costs_without_nds"] * (1 + 0.5)
    df["account_id"] = 1
    df["source_type_id"] = 9
    df["id_key_camp"] = "1_" + df["{ENTITY_NAME}_id"].astype(str)
    # df["id_key_ad"] = df["id_key_camp"] + "_" + df["ad_id"].astype(str)  # только для ad-level
    return df.reindex(columns={ENTITY_NAME_UPPER}_STAT_COLUMNS).reset_index(drop=True)


# ── [INCLUDE IF F4 cumulative metrics exist] ──────────────────────────────────
def {FUNCTION_CUMULATIVE_NAME}(
    global_start_date: str, date_from: str, date_to: str
) -> pd.DataFrame:
    """{FN_CUMULATIVE_ONELINER}

    {CUMULATIVE_METRIC_NOTE}

    Для получения значения метрики за каждый день D запрашивается период
    [global_start_date, D] с groupBy=NO_GROUP_BY — значение берётся из totals.

    Параметры:
        global_start_date — начало накопительного периода, YYYY-MM-DD
        date_from         — первый день диапазона, YYYY-MM-DD
        date_to           — последний день диапазона, YYYY-MM-DD

    Ограничение: период [global_start_date, date_to] ≤ {PERIOD_MAX_DAYS} дней.
    """
    client = {CLASS_NAME}()
    entities = client._fetch_all_{ENTITY_NAME}s()
    entity_ids = [e["{ENTITY_ID_FIELD}"] for e in entities if e.get("{ENTITY_ID_FIELD}") is not None]
    if not entity_ids:
        return pd.DataFrame(columns={ENTITY_NAME_UPPER}_REACH_COLUMNS)

    entity_name_by_id = {
        str(e["{ENTITY_ID_FIELD}"]): _pick(e, "{ENTITY_NAME_FIELD_1}", "{ENTITY_NAME_FIELD_2}")
        for e in entities
    }

    days = _date_range(date_from, date_to)
    batches = list(_chunks(entity_ids, BATCH_SIZE))
    all_rows: list[dict[str, Any]] = []

    progress = tqdm(total=len(days) * len(batches), desc="Загрузка: охват", unit="запрос")

    for day in days:
        for i, batch in enumerate(batches, 1):
            progress.set_postfix_str(f"{day}  батч {i}/{len(batches)}")
            try:
                uuid = client._submit_report(
                    batch, global_start_date, day, group_by="NO_GROUP_BY",
                )
                client._poll_uuid(uuid)
                report_data = client._download_report(uuid)

                for eid_str, entity_data in report_data.items():
                    totals = entity_data.get("report", {}).get("totals", {})
                    metric = _parse_num(_pick(totals, "{CUMULATIVE_METRIC_FIELD}", "{CUMULATIVE_METRIC_FIELD_ALT}"))
                    if metric:
                        all_rows.append({
                            "date": day,
                            "{ENTITY_NAME}_id": eid_str,
                            "{ENTITY_NAME}_name": entity_name_by_id.get(eid_str),
                            "{CUMULATIVE_METRIC_NAME}": metric,
                        })
            except (requests.HTTPError, RuntimeError) as exc:
                logger.warning("Пропущен батч (день=%s, entity=%s): %s", day, batch, exc)
            finally:
                progress.update(1)

    progress.close()
    if not all_rows:
        return pd.DataFrame(columns={ENTITY_NAME_UPPER}_REACH_COLUMNS)
    df = pd.DataFrame(all_rows)
    df = df.sort_values(["{ENTITY_NAME}_id", "date"]).reset_index(drop=True)
    df["increment"] = df.groupby("{ENTITY_NAME}_id")["{CUMULATIVE_METRIC_NAME}"].diff()
    df["increment"] = df["increment"].fillna(df["{CUMULATIVE_METRIC_NAME}"])  # первый день = значение метрики
    df["account_id"] = 1
    df["source_type_id"] = 9
    df["id_key_camp"] = "1_" + df["{ENTITY_NAME}_id"].astype(str)
    # df["id_key_ad"] = df["id_key_camp"] + "_" + df["ad_id"].astype(str)  # только для ad-level
    return df.reindex(columns={ENTITY_NAME_UPPER}_REACH_COLUMNS).reset_index(drop=True)
# ── [/CUMULATIVE] ─────────────────────────────────────────────────────────────
