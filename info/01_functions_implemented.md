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

Нереализованные (стабы): `get_campaigns_daily_stat`, `get_creatives_daily_stat`,
`get_admin_audit` — очередь Шага 4.
