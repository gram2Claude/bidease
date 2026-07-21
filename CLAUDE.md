# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -r bidease/requirements.txt
pip install -r bidease/requirements-dev.txt   # pytest (для unit-тестов)
```

Credentials go in `bidease/.env` (copy from `bidease/.env.example`):

```
API_TOKEN=...         # API-токен Bidease Reporting (выдаёт техподдержка/CSM Bidease)
TEST_START_DATE=...   # YYYY-MM-DD — период для smoke-тестов статистики (включительно)
TEST_END_DATE=...     # YYYY-MM-DD (включительно; эксклюзивность todate библиотека учитывает сама)
```

`BideaseClient` reads the token from env var `API_TOKEN`, or it can be passed
explicitly to the constructor.

## Статус проекта

Шаги 0–3 завершены (структура, анкета, сводка API, скаффолд). **Шаг 4 — реализация
функций через цикл spec → plan → impl → smoke-тест — не начат:** все 4 публичные
функции — стабы с `NotImplementedError`. Порядок реализации: `get_campaign_dict` →
`get_campaigns_daily_stat` → `get_creatives_daily_stat` → `get_admin_audit`.

## Running

Unit-тесты (pytest, моки — без сети и `.env`):
```bash
python -m pytest bidease/tests -q
```

Smoke-тесты (живой API, нужен `.env`; запуск из корня репо, по одному файлу на функцию):
```bash
python bidease/smoke_tests/test_<имя_функции>.py
```
Даты статистики берутся из `.env` (`TEST_START_DATE`/`TEST_END_DATE`). Результат сохраняется в
`bidease/raw_data/<имя_функции>[_{from}_{to}].csv` (cp1251, gitignored); перед записью
тест удаляет старые выгрузки этой же функции. После прогона показать первые 5 строк
**из сохранённого CSV** (не из памяти) — см. `test/00_README.md`.

Demo notebook:
```bash
jupyter notebook bidease/bidease_demo.ipynb
```

## Architecture

Single-file library: `bidease/bidease.py`.

**`BideaseClient`** — internal HTTP client:
- Auth: **статический API-токен в query-параметре `api-token`** (не заголовок, не OAuth;
  эндпоинтов выпуска/обновления токена нет — токен выдаёт поддержка Bidease).
- Единственный эндпоинт: `GET https://ui-api.bidease.com/api/reporting/v1/stats` → **CSV**.
- `_get_report(params)` → DataFrame; повторяемые query-параметры (`group`, `campaigns`, …)
  передаются списком пар `(ключ, значение)`. 429 → экспоненциальный backoff
  (макс. 5 повторов, старт 1 с; лимиты API не документированы — защита).
- `_parse_csv()` → пустое тело = пустой DataFrame.

**Public functions** (all return `pd.DataFrame`; все — стабы до Шага 4):

| Function | Granularity | Запрос к API |
|----------|-------------|--------------|
| `get_campaign_dict()` | справочник (кампании) | `group=CampaignID+CampaignName+AdvertiserID+ProductID`, период — последний год |
| `get_campaigns_daily_stat(date_from, date_to)` | статистика по дням (кампании) | `group=Day+CampaignID`, один запрос на период |
| `get_creatives_daily_stat(date_from, date_to)` | статистика по дням (креативы) | `group=Day+CampaignID+CreativeID`, один запрос на период |
| `get_admin_audit(date_from, date_to)` | сводный аудит по дням (admin_audit) | собственного запроса нет — агрегат поверх campaigns stats |

**Правила запроса данных (специфика Bidease — отличается от avito):**
- **Справочников-эндпоинтов нет** — справочник кампаний собирается тем же stats-эндпоинтом
  с группировками по атрибутам; метрики отбрасываются, дедупликация по `campaign_id`.
- **Статистика группируется на сервере** (`group=Day+…`) — **один GET на весь период на
  функцию**, без перебора сущностей и без пагинации.
- **`todate` — ЭКСКЛЮЗИВНАЯ граница** (главная ловушка API). Публичные функции принимают
  `date_from`/`date_to` включительно; в запрос уходит `todate = date_to + 1 день`
  (`_todate_exclusive`).
- **Все даты/часы — в таймзоне токена** (по умолчанию UTC+0). Относительные даты API
  (`today`, `today-20d`) в библиотеке не используются — только явные `YYYY-MM-DD`.
- **Период — в пределах 1 года от текущей даты** (`PERIOD_MAX_DAYS = 365`) — валидируется
  на входе (`_validate_period`).
- **Иерархия сущностей: кампания → креатив** (уровня «группы объявлений» в Bidease нет).
- **Расчётные метрики API (`ctr`, `ecpm`, `ecpc`, `i2c`, `cpi`) не выгружаются** (конвенция
  проекта); `conversions`/`revenue`/`iap*`/`goal1–6` исключены решением проекта 2026-07-21
  (только базовые: показы/клики/расход). Охватных метрик (reach) в API нет вовсе.

## API Constraints

From `info/00_api_methods.md`:
- Период отчёта: в пределах **1 года** от текущей даты; `todate` эксклюзивна.
- Группировки: максимум **7** значений `group` на запрос (доступно 26 разрезов).
- Rate limits: **не документированы**; 429-backoff — защитный.
- Ошибки (факт 2026-07-21): невалидный токен → **401** (пустое тело); `fromdate ≥ todate`
  И выход за лимит года → **400** с plain-text ` -> fromdate should be less than todate`
  (текст одинаковый — для «за лимитом года» вводит в заблуждение).
- Формат ответа: только CSV, разделитель `,` (факт). Колонки группировок — в **нижнем
  регистре** в конце строки (`day`, `campaignid`, `campaignname`, …). Реальный заголовок
  **богаче доков** (35 метрик, есть `profit`/`roi`/`roas`/`uniq_*`/`ecpa1–6`; заявленной
  `i2c` нет) — см. `info/00_api_methods.md`. Пустой результат: с группировками — только
  заголовок; без группировок — одна строка нулей.

## Обогащение DataFrame (соглашение проекта)

Каждая публичная функция обогащает результат фиксированным набором константных
и вычисляемых полей **перед** `df.reindex(columns=...)`:

**Константы (для всех функций):**
- `account_id = 1`, `source_type_id = 10` (решение проекта 2026-07-21) — примеры,
  заменяемые при интеграции

**Для справочника кампаний:** `product_name = "prod_test"`, `camp_type = "camp_test"`,
`camp_category = "cat_test"`, `owner_id = 1` — константы-примеры;
⚠️ `product_id` — **реальный `ProductID` из API Bidease** (отступление от avito-конвенции,
где это константа; фиксируется в спеке).

**Для функций с расходами** (агентская комиссия `ak = 0.5`):
- `costs_without_nds` ← API `spend` — **десятичный тип (float), округление до 2 знаков**
- `costs_nds = costs_without_nds * (1 + ставка_НДС)` — ставка по году даты строки:
  год ≥ 2026 → 22% (множитель 1.22), ранее → 20% (множитель 1.20)
- `costs_nds_ak = costs_nds * 1.5`; `costs_without_nds_ak = costs_without_nds * 1.5`

> ⚠️ **`spend` у Bidease — доллары США БЕЗ НДС** (решение проекта 2026-07-21: «считаем,
> что изначально в источнике расходы без НДС»). Поэтому направление расчёта **ОБРАТНОЕ
> avito**: база — `costs_without_nds` (← `spend`), а `costs_nds` вычисляется
> **УМНОЖЕНИЕМ** на (1 + ставка). Валюта не пересчитывается — значения остаются в долларах.

**Составные ключи:**
- `id_key_camp = "1_" + campaign_id` — для всех функций
- `id_key_ad = id_key_camp + "_" + creative_id` — для ad-level (креативы); в Bidease
  нет групп → без group-звена (решение 2026-07-21)

Значения констант — заменяемые при реальной интеграции (вписываются клиентом).

## Windows Encoding

`bidease.py` reconfigures `sys.stdout/stderr` to UTF-8 on import — required on Windows
where the default console encoding may be cp1251. CSV в `raw_data/` пишется/читается
в `cp1251` с `errors="replace"`. This is intentional; do not remove it.

## Spec Reference

`info/00_api_methods.md` — полная сводка Bidease Reporting API (auth + единственный
stats-эндпоинт: параметры, 26 группировок, колонки CSV, лимиты) — единая точка правды по API.
`info/01_functions_implemented.md` — реестр реализованных функций (ведётся на Шаге 4).
Процесс разработки описан в `test/00_README.md`.

## Git

Репозиторий: https://github.com/gram2Claude/bidease.git (личный репо gram2Claude,
публичный). Ветка `main`, коммиты — Conventional Commits, прямой push в main.
