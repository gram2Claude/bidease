# Реестр реализованных функций — Bidease Reporting API

Ведётся по шаблону `test/manual_forms/02c_FUNCTIONS_IMPLEMENTED.md`.
Актуальная картина «что уже умеет клиент»: API-метод каждой публичной функции,
поля выходного DataFrame, специфика сопровождения.

---

## Функция: `get_campaign_dict`

- **Статус:** реализована
- **Дата реализации:** 2026-07-22
- **Тип:** справочник (кампании)
- **Файл:** `bidease/bidease.py` → модульная функция `get_campaign_dict()`
- **Spec:** `specs/01_spec_get_campaign_dict.md`
- **Plan:** `plans/01_plan_get_campaign_dict.md`
- **Smoke-test:** `bidease/smoke_tests/test_get_campaign_dict.py`
- **Unit-tests:** `bidease/tests/test_get_campaign_dict.py`

### API-метод

- **Endpoint:** `GET /api/reporting/v1/stats` (единственный эндпоинт API)
- **Тип:** sync
- **Формат ответа:** `text/csv` (UTF-8 без charset в Content-Type — клиент форсирует)
- **Ссылка на сводку:** `info/00_api_methods.md`
- **Особая семантика:** справочных эндпоинтов в API нет — справочник собирается
  stats-запросом с группировками `CampaignID+CampaignName+AdvertiserID+ProductID`
  за последний год (`fromdate = сегодня−364d`, `todate = сегодня`, эксклюзивна);
  метрики отбрасываются. В справочник попадают только кампании с хотя бы одним
  событием за период.

### Параметры функции (Python-сигнатура)

```python
def get_campaign_dict() -> pd.DataFrame:
    ...
```

Без параметров (зеркально avito); период вычисляется внутри (`_dict_period()`).

### Поля выходного DataFrame

| Колонка (итоговая) | Тип pandas | Источник (поле API) | Описание |
|--------------------|-----------|---------------------|----------|
| `campaign_id` | int64 | CSV `campaignid` | ID кампании; дедупликация `keep="first"` |
| `campaign_name` | object | CSV `campaignname` | название кампании |
| `advertiser_id` | int64 | CSV `advertiserid` | ID рекламодателя ui.bidease.com |
| `account_id` | int64 | константа `1` | пример, заменить при интеграции |
| `source_type_id` | int64 | константа `10` | решение проекта 2026-07-21 |
| `product_id` | int64 | CSV `productid` | ⚠️ **реальный ProductID из API** (отступление от avito-конвенции, решение 2026-07-21) |
| `product_name` | object | константа `"prod_test"` | пример |
| `camp_type` | object | константа `"camp_test"` | пример |
| `camp_category` | object | константа `"cat_test"` | пример |
| `id_key_camp` | object | вычисляется: `"1_" + campaign_id` | составной ключ кампании |
| `owner_id` | int64 | константа `1` | пример |

Расходов в справочнике нет — блок `costs_*`/`ak` не применяется.

### Специфика / сложности реализации

- **Кодировка ответа:** UTF-8, но `Content-Type: text/csv` БЕЗ charset → requests
  по умолчанию декодировал бы ISO-8859-1 (кириллица-кракозябры); `_parse_csv`
  форсирует `resp.encoding = "utf-8"` (факт 2026-07-22).
- **CSV-колонки группировок** — в нижнем регистре в конце строки; маппинг в
  snake_case — модульная константа `GROUP_CSV_RENAME` (переиспользуется).
- **Пустой аккаунт** → только строка заголовка → пустой DataFrame с колонками
  `CAMPAIGN_DICT_COLUMNS` (не ошибка).
- **Сохранение в raw_data:** `encoding="cp1251", errors="replace"` (конвенция
  проекта для Excel/Windows); кириллица имён кампаний в cp1251 представима.
- **Дедупликация:** `keep="first"` — при переименовании кампании внутри года
  (если API отдаст исторические срезы) останется первая встреченная строка;
  на текущих данных один ID = одна строка (open question спеки).

### История изменений

| Дата | Изменение | Причина |
|------|-----------|---------|
| 2026-07-22 | Первичная реализация | — |

---

## Функция: `get_campaigns_daily_stat`

- **Статус:** реализована
- **Дата реализации:** 2026-07-22
- **Тип:** статистика (кампании, по дням)
- **Файл:** `bidease/bidease.py` → модульная функция `get_campaigns_daily_stat()`
- **Spec:** `specs/02_spec_get_campaigns_daily_stat.md`
- **Plan:** `plans/02_plan_get_campaigns_daily_stat.md`
- **Smoke-test:** `bidease/smoke_tests/test_get_campaigns_daily_stat.py`
- **Unit-tests:** `bidease/tests/test_get_campaigns_daily_stat.py`

### API-метод

- **Endpoint:** `GET /api/reporting/v1/stats`, `group=Day+CampaignID`
- **Тип:** sync — **один GET на весь период** (группировка серверная, пагинации нет)
- **Формат ответа:** `text/csv` (UTF-8 форсируется клиентом)
- **Ссылка на сводку:** `info/00_api_methods.md`

### Параметры функции (Python-сигнатура)

```python
def get_campaigns_daily_stat(date_from: str, date_to: str) -> pd.DataFrame:
    ...
```

`date_from`/`date_to` — `YYYY-MM-DD`, **включительно** (в запрос уходит
`todate = date_to + 1 день`, эксклюзивность API учтена). Валидация периода
(`≤ 1 года от текущей даты`) — до запроса, `ValueError`.

### Поля выходного DataFrame

| Колонка (итоговая) | Тип pandas | Источник (поле API) | Описание |
|--------------------|-----------|---------------------|----------|
| `date` | object (str `YYYY-MM-DD`) | CSV `day` (`MM/DD/YYYY 00:00:00`) | дата; парсинг явным форматом, fail-loud |
| `campaign_id` | int64 | CSV `campaignid` | ID кампании |
| `impressions` | int64 | CSV `impressions` | показы |
| `clicks` | int64 | CSV `clicks` | клики |
| `costs_usd` | float64 | ← CSV `spend`, round(2) | **доллары США как есть**; НДС и комиссия не применяются (решение 2026-07-27) |
| `account_id` | int64 | константа `1` | пример |
| `source_type_id` | int64 | константа `10` | решение 2026-07-21 |
| `id_key_camp` | object | `"1_" + campaign_id` | составной ключ |

### Специфика / сложности реализации

- ⚠️ **Валюта — доллары США, рублёвых `costs_*` НЕТ** (решение 2026-07-27): поля
  конвенции `costs_nds`/`costs_without_nds`/`costs_*_ak` и константа `ak`
  подразумевают рубли, а Bidease отдаёт `spend` в долларах → вся группа убрана,
  расход отдаётся одним полем `costs_usd ← spend` (round(2)). НДС не считается,
  курс не применяется — пересчёт на стороне приёмника.
- **Формат `day`** — `MM/DD/YYYY 00:00:00` (не ISO; факт 2026-07-22) — парсится
  явным форматом `DAY_CSV_FORMAT`, несовпадение → громкая ошибка.
- **Округление `costs_usd` — numpy/pandas `.round(2)`, half-to-even по двоичному float:**
  `12.345 → 12.34` (не 12.35), `12.346 → 12.35`, `2.675 → 2.68`. Поведение унаследовано
  от прежней схемы (так же округлялась база `costs_without_nds`) и закреплено тестом
  `test_bad_spend_becomes_zero`. Если приёмнику нужно арифметическое half-up —
  это отдельное решение, меняющее контракт.
- **Битый `spend`** (пустой, нечисловой) → `costs_usd = 0.0`, строка НЕ отбрасывается,
  показы/клики сохраняются (`to_numeric(errors="coerce").fillna(0)`). То же правило
  применяется к `impressions` и `clicks`.
- 🔒 **Токен не утекает в исключения** (фикс 2026-07-27, найден ревью ТЗ): `api-token`
  едет в query, а requests кладёт полный URL в текст ошибки — теперь клиент
  перевыбрасывает исключения с `api-token=<redacted>` (`_redact`/`_sanitized`),
  сохраняя тип исключения, `response` и код статуса. Покрыто
  `bidease/tests/test_client_errors.py`, проверено на живом 401.
- ⚠️ **Показы зависят от разреза группировки** (факт 2026-07-27): `impressions` в
  разрезах `Day` / `Day+CampaignID` / `Day+CampaignID+CreativeID` за один период
  расходятся на 0.08–0.43 % — свойство агрегации Bidease (повторный запрос тем же
  разрезом идентичен, строк с пустыми id нет). `clicks`/`spend` совпадают точно →
  сверять уровни по ним. Детали — `info/00_api_methods.md`.
- Пустой период → пустой DataFrame с колонками (не ошибка).

### История изменений

| Дата | Изменение | Причина |
|------|-----------|---------|
| 2026-07-22 | Первичная реализация | — |
| 2026-07-27 | Убраны `costs_nds`, `costs_without_nds`, `costs_nds_ak`, `costs_without_nds_ak`, `ak`; добавлено `costs_usd` | источник отдаёт расход в долларах, а `costs_*` конвенции — рублёвые |

---

## Функция: `get_creatives_daily_stat`

- **Статус:** реализована
- **Дата реализации:** 2026-07-22
- **Тип:** статистика (креативы, по дням)
- **Файл:** `bidease/bidease.py` → модульная функция `get_creatives_daily_stat()`
- **Spec:** `specs/03_spec_get_creatives_daily_stat.md`
- **Plan:** `plans/03_plan_get_creatives_daily_stat.md`
- **Smoke-test:** `bidease/smoke_tests/test_get_creatives_daily_stat.py`
- **Unit-tests:** `bidease/tests/test_get_creatives_daily_stat.py`

### API-метод

- **Endpoint:** `GET /api/reporting/v1/stats`, `group=Day+CampaignID+CreativeID`
- **Тип:** sync — один GET на весь период
- **Формат ответа:** `text/csv`

### Параметры функции (Python-сигнатура)

```python
def get_creatives_daily_stat(date_from: str, date_to: str) -> pd.DataFrame:
    ...
```

### Поля выходного DataFrame

Как у `get_campaigns_daily_stat` + после `campaign_id`:

| Колонка | Тип pandas | Источник | Описание |
|---------|-----------|----------|----------|
| `creative_id` | int64 | CSV `creativeid` | ID креатива |
| `id_key_ad` | object | `id_key_camp + "_" + creative_id` | ⚠️ **без group-звена** — групп в Bidease нет (решение 2026-07-21) |

### Специфика / сложности реализации

- Иерархия Bidease: кампания → креатив (уровня групп объявлений нет) → `id_key_ad`
  двухзвенный, отступление от avito-шаблона.
- Строки без `campaign_id` ИЛИ `creative_id` отбрасываются (оба нужны для ключа).
- Остальное — как у `get_campaigns_daily_stat` (общие хелперы).

### История изменений

| Дата | Изменение | Причина |
|------|-----------|---------|
| 2026-07-22 | Первичная реализация | — |
| 2026-07-27 | Убраны `costs_*`-поля и `ak`; добавлено `costs_usd` | расход источника — в долларах (см. `get_campaigns_daily_stat`) |

---

## Функция: `get_admin_audit`

- **Статус:** реализована
- **Дата реализации:** 2026-07-22
- **Тип:** сводный аудит (агрегат по дням)
- **Файл:** `bidease/bidease.py` → модульная функция `get_admin_audit()`
- **Spec:** `specs/04_spec_get_admin_audit.md`
- **Plan:** `plans/04_plan_get_admin_audit.md`
- **Smoke-test:** `bidease/smoke_tests/test_get_admin_audit.py`
- **Unit-tests:** `bidease/tests/test_get_admin_audit.py`

### API-метод

- **Собственного эндпоинта нет** — агрегат поверх `get_campaigns_daily_stat`
  (+ `owner_id` из `get_campaign_dict`, join по `campaign_id`). Итого 2 HTTP-запроса.

### Параметры функции (Python-сигнатура)

```python
def get_admin_audit(date_from: str, date_to: str) -> pd.DataFrame:
    ...
```

### Поля выходного DataFrame

| Колонка | Тип pandas | Источник | Описание |
|---------|-----------|----------|----------|
| `date` | object (str) | статистика кампаний | ключ группировки |
| `account_id` | int64 | константа `1` | ключ группировки |
| `source_type_id` | int64 | константа `10` | ключ группировки |
| `owner_id` | int64 | `get_campaign_dict` (merge; NaN → 1) | ключ группировки |
| `impressions` | int64 | сумма по дню | |
| `clicks` | int64 | сумма по дню | |
| `costs_usd` | float64 | сумма по дню, round(2) | доллары США |
| `chef_flag` | int64 | константа `1` | дефолт |

### Специфика / сложности реализации

- **Страховка от потери строк:** `owner_id` после left-merge может быть NaN
  (кампания в статистике, но не в справочнике) — NaN в ключе groupby молча
  выбрасывает строку → `fillna(1)` до группировки.
- Пустая статистика → пустой DataFrame, справочник НЕ запрашивается.
- Округление: `costs_usd` округляется после суммирования (снимает хвост сложения float).

### История изменений

| Дата | Изменение | Причина |
|------|-----------|---------|
| 2026-07-22 | Первичная реализация | — |
| 2026-07-27 | `costs_nds`/`costs_without_nds` заменены одним `costs_usd` | расход источника — в долларах (см. `get_campaigns_daily_stat`) |
