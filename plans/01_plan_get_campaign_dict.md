# Plan: get_campaign_dict

## Контекст

На основании спецификации `specs/01_spec_get_campaign_dict.md` (утверждена пользователем
2026-07-22). Синхронный паттерн [SYNC]: один GET stats-эндпоинта с группировками по
атрибутам кампании, метрики отбрасываются.

## Изменения в `bidease.py`

### 1. Новые константы

- `CAMPAIGN_DICT_COLUMNS` — **уже существует** в скаффолде (порядок/состав совпадает со
  спекой, включая обогащение: `account_id`, `source_type_id`, `product_id` (из API!),
  `product_name`, `camp_type`, `camp_category`, `id_key_camp`, `owner_id`). Изменений не требует.
- **Новая** `GROUP_CSV_RENAME: dict[str, str]` — маппинг CSV-колонок группировок
  (нижний регистр, факт API) → snake_case итоговых DataFrame. Модульная константа,
  переиспользуется следующими функциями:

  ```python
  GROUP_CSV_RENAME = {
      "day": "date",
      "campaignid": "campaign_id",
      "campaignname": "campaign_name",
      "advertiserid": "advertiser_id",
      "productid": "product_id",
      "creativeid": "creative_id",
  }
  ```

### 2. Новые приватные функции

- `_dict_period() -> tuple[str, str]` — период справочника:
  `fromdate = сегодня − 364 дня`, `todate = сегодня` (эксклюзивна), обе — ISO `YYYY-MM-DD`.

### 3. Публичная функция

- `get_campaign_dict()` — заменить стаб:
  1. `client = BideaseClient()`; `fromdate, todate = _dict_period()`.
  2. `client._get_report([...])` c `group=CampaignID, CampaignName, AdvertiserID, ProductID`
     (повторяемые пары).
  3. `df.empty` (пустое тело ИЛИ только заголовок) → `pd.DataFrame(columns=CAMPAIGN_DICT_COLUMNS)`.
  4. `rename(columns=GROUP_CSV_RENAME)` → оставить только
     `["campaign_id", "campaign_name", "advertiser_id", "product_id"]` (метрики отброшены).
  5. `dropna(subset=["campaign_id"])` → `drop_duplicates(subset=["campaign_id"], keep="first")`
     → `campaign_id.astype("int64")`.
  6. Обогащение (перед reindex): `account_id=1`, `source_type_id=10`,
     `product_name="prod_test"`, `camp_type="camp_test"`, `camp_category="cat_test"`,
     `id_key_camp="1_"+campaign_id.astype(str)`, `owner_id=1`.
     `product_id` НЕ трогаем — реальное значение из API (решение 2026-07-21).
  7. `return df.reindex(columns=CAMPAIGN_DICT_COLUMNS).reset_index(drop=True)`.

### 4. Изменения в существующем коде

- Заголовок секции «Публичные функции (стабы …)» → нейтральный («стабы» остаются
  у трёх нереализованных функций).
- Docstring модуля: пометить `get_campaign_dict` реализованной.

## Юнит-тесты — `bidease/tests/test_get_campaign_dict.py` (новый) + `conftest.py`

Мок HTTP на уровне `requests.Session.get` (настоящий `requests.Response` с
`_content`-байтами — проверяет и форс UTF-8 в `_parse_csv`); `API_TOKEN` — через
`monkeypatch.setenv`. Кейсы (из Acceptance Criteria спеки):

1. Нормальный CSV (метрики + группировки, кириллица в `campaignname` UTF-8-байтами) →
   колонки ровно `CAMPAIGN_DICT_COLUMNS` в порядке, значения/обогащение/`id_key_camp`
   корректны, кириллица не искажена.
2. Только заголовок (пустой аккаунт) → пустой DataFrame с правильными колонками.
3. Совсем пустое тело → то же.
4. Дубль `campaign_id` → остаётся первая строка.
5. Строка без `campaign_id` → отброшена; пустой `productid` в другой строке → NaN, строка жива.

## Smoke-тест — `bidease/smoke_tests/test_get_campaign_dict.py` (новый)

По конвенции `test/00_README.md` §6: `PROJECT_ROOT = bidease/`, `sys.path.insert`,
`load_dotenv(PROJECT_ROOT / ".env")`; вызов `get_campaign_dict()`; сохранение в
`bidease/raw_data/get_campaign_dict.csv` (`encoding="cp1251", errors="replace"`,
имя фиксированное — очистка старых выгрузок не нужна); показ **из сохранённого CSV**:
shape, columns, первые 5 строк.

## Порядок реализации

1. `GROUP_CSV_RENAME` + `_dict_period()` в `bidease.py`.
2. Тело `get_campaign_dict()` (по §3), правка docstring/заголовка секции.
3. Юнит-тесты + `conftest.py`; прогон `python -m pytest bidease/tests -q` до зелёного.
4. Smoke-тест; самостоятельный запуск `python bidease/smoke_tests/test_get_campaign_dict.py`
   из корня репо; показ первых 5 строк из CSV в чат.
5. Реестр `info/01_functions_implemented.md` (создать по шаблону
   `test/manual_forms/02c_FUNCTIONS_IMPLEMENTED.md`, блок функции + история).
6. Независимое код-ревью дельты; существенные находки → фикс → повтор.
7. Обновить статус (CLAUDE.md, память), commit + push.

## Проверка

- [ ] Функция возвращает DataFrame с колонками `CAMPAIGN_DICT_COLUMNS` (порядок точный)
- [ ] При пустом ответе API — пустой DataFrame с правильными колонками, без исключений
- [ ] Дедупликация по `campaign_id`, строк без `campaign_id` нет
- [ ] `id_key_camp == "1_" + str(campaign_id)`; `source_type_id == 10`; `product_id` — из API
- [ ] Юнит-тесты зелёные; smoke на живом API пройден, CSV сохранён, 5 строк показаны
- [ ] Остальные стабы и клиент — без регрессий
