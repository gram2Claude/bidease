# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -r {MODULE_NAME}/requirements.txt
```

Credentials go in `{MODULE_NAME}/.env` (copy from `{MODULE_NAME}/.env.example`):

```
# [OAUTH variant]
{ENV_VAR_1}=...
{ENV_VAR_2}=...

# [API KEY variant — replace above two lines with]
# {ENV_VAR_1}=...
```

`{CLASS_NAME}` reads credentials from env vars `{ENV_VAR_1}` / `{ENV_VAR_2}`,
or they can be passed explicitly to the constructor.

## Running

Demo notebook:
```bash
jupyter notebook {MODULE_NAME}/{MODULE_NAME}_demo.ipynb
```

Quick smoke-test from Python REPL (requires real credentials):
```python
import sys; sys.path.insert(0, "{MODULE_NAME}")
from {MODULE_NAME} import {FUNCTION_1_NAME}
df = {FUNCTION_1_NAME}()
print(df.shape)
```

## Architecture

Single-file library: `{MODULE_NAME}/{MODULE_NAME}.py`.

**`{CLASS_NAME}`** — internal HTTP client:
- [OAUTH] OAuth 2.0 `client_credentials` auth; token auto-refreshed 60 s before expiry
- [API KEY] Static API key passed in `{API_KEY_HEADER}` header on every request
- [ASYNC] `_submit_report()` → returns UUID (async report, up to {BATCH_SIZE} {ENTITY_NAME}s/batch)
- [ASYNC] `_poll_uuid()` → polls `GET {POLL_PATH_PREFIX}{UUID}` every {POLL_INTERVAL_SEC} s (max {POLL_MAX_ATTEMPTS} attempts ≈ {POLL_TIMEOUT_MIN} min)
- [ASYNC] `_download_report()` → `GET {DOWNLOAD_PATH}?UUID=...`
- [SYNC] `_fetch_{ENTITY_NAME}_data()` → direct GET/POST, no UUID involved
- 429 handling: exponential backoff, max {RATE_LIMIT_RETRY_MAX} retries, starts at {RATE_LIMIT_BASE_SEC} s

**Public functions** (all return `pd.DataFrame`):

| Function | Granularity | API endpoint |
|----------|-------------|--------------|
| `{FUNCTION_1_NAME}()` | {FN_1_GRANULARITY} | `{FN_1_ENDPOINT}` |
| `{FUNCTION_2_NAME}(date_from, date_to)` | {FN_2_GRANULARITY} | `{FN_2_ENDPOINT}` |
| `{FUNCTION_N_NAME}(...)` | {FN_N_GRANULARITY} | `{FN_N_ENDPOINT}` |

<!-- Добавь строку в таблицу для каждой дополнительной функции -->

**[INCLUDE IF F4 cumulative metrics] Special metric semantics:**
{CUMULATIVE_METRIC_NOTE}
<!-- Пример:
«`{FUNCTION_CUMULATIVE_NAME}` uses `global_start_date` because {CUMULATIVE_METRIC_NAME} is
a cumulative metric (unique users since period start) — it cannot be summed across days.
For per-day values, each day D requires a separate request covering [global_start_date, D]
with groupBy=NO_GROUP_BY, reading totals.{CUMULATIVE_METRIC_FIELD}. Total API calls =
N_days × N_batches. The `increment` column is computed locally via groupby().diff().» -->

**Правила запроса данных (зафиксированы по умолчанию):**
- **Статистика (все функции кроме охвата):** данные запрашиваются отдельно за каждый день — один запрос на (день × батч). Период в одном запросе всегда = 1 день.
- **Охват (reach/cumulative):** данные не разбиваются по дням на стороне API — кумулятивный показатель. Для каждого дня D запрашивается период [global_start_date, D] с groupBy=NO_GROUP_BY; разбивка на дневные дельты (`increment`) вычисляется локально через `groupby().diff()`.

**Report flow** [ASYNC]:
1. Fetch all {ENTITY_NAME}s → split into batches of ≤{BATCH_SIZE}
2. For each (day, batch): submit → poll → download → parse rows into dicts
3. Collect all dicts → `pd.DataFrame` with fixed column order

**Helper functions** (private, module-level):
- `_parse_num()` — {NUM_FORMAT_NOTE}
- `_parse_date_str()` — {DATE_FORMAT_NOTE}
- `_pick()` — first-found key from dict (handles API field name variations)

## API Constraints

From `specs/{API_REFERENCE_FILENAME}` (repo root):
- Max **{BATCH_SIZE} {ENTITY_NAME}s** per statistics request
- [ASYNC] Max **{MAX_CONCURRENT} concurrent** report generation tasks
- Max **{MAX_REQUESTS_PER_DAY} requests/day** per account
- Max **{PERIOD_MAX_DAYS} days** per report period
- {EXTRA_CONSTRAINT_1}

## Обогащение DataFrame (соглашение проекта)

Каждая публичная функция обогащает результат фиксированным набором константных
и вычисляемых полей **перед** `df.reindex(columns=...)`:

**Константы (для всех функций):**
- `account_id = 1`, `source_type_id = 9` — примеры, заменяемые при интеграции

**Для справочников:** дополнительно `product_id = 1`, `product_name = "prod_test"`,
`camp_type = "camp_test"`, `camp_category = "cat_test"`, `owner_id = 1`

**Для функций с расходами** (агентская комиссия `ak = 0.5`):
- `costs_nds` — **десятичный тип (float), округление до 2 знаков** сразу после чтения из API,
  до вычисления производных
- `costs_without_nds = costs_nds / (1 + ставка_НДС)` — **ставка по году даты строки:
  year ≥ 2026 → 22% (делитель 1.22), раньше → 20% (делитель 1.20)**; считается per-row по `date`
- `costs_nds_ak = costs_nds * 1.5`
- `costs_without_nds_ak = costs_without_nds * 1.5`

**Составные ключи:**
- `id_key_camp = "1_" + campaign_id` — для всех функций
- `id_key_ad = id_key_camp + "_" + ad_id` — **только для ad-level** функций

> **Важно про `costs_nds`:** название = «расход С НДС». Источник зависит от типа
> отчёта API (BANNER → «Расход, ₽, с НДС»; VIDEO_BANNER → «Расход, ₽» без НДС).
> При несовпадении название колонки может вводить в заблуждение — фиксировать в
> `info/01_functions_implemented.md` по каждой функции отдельно.

Значения констант — заменяемые при реальной интеграции (вписываются клиентом).

## Windows Encoding

`{MODULE_NAME}.py` reconfigures `sys.stdout/stderr` to UTF-8 on import — required on Windows
where the default console encoding may be cp1251. This is intentional; do not remove it.

<!-- DELETE THIS SECTION if data is ASCII-only or non-Windows deployment is guaranteed -->

## Spec Reference

`specs/{API_REFERENCE_FILENAME}` (repo root) — full list of {API_NAME} API endpoints.
Already-implemented endpoints are marked. Use this when adding new API methods.
