# Plan: get_campaigns_daily_stat

## Контекст

На основании спецификации `specs/02_spec_get_campaigns_daily_stat.md`.
Мандат пользователя 2026-07-22 «делай дальше всё без остановок» — цикл выполняется
без промежуточных утверждений, финальные артефакты — на проверку пользователю.

## Изменения в `bidease.py`

### 1. Константы

- `CAMPAIGNS_STAT_COLUMNS` — уже в скаффолде, изменений не требует.
- `GROUP_CSV_RENAME` — уже есть (включая `day → date`).
- Новая `DAY_CSV_FORMAT = "%m/%d/%Y %H:%M:%S"` — формат `day` (факт 2026-07-22).
  (Лишние метрики CSV отбрасываются финальным `reindex` по колонкам — отдельная
  константа списка метрик не нужна.)

### 2. Новые приватные функции (переиспользуются функциями статистики)

- `_fetch_daily_stat(date_from, date_to, groups) -> pd.DataFrame` —
  `_validate_period` → `BideaseClient()._get_report([fromdate, todate=_todate_exclusive,
  *("group", g)])`.
- `_parse_day_column(df) -> pd.DataFrame` — `date` из `MM/DD/YYYY 00:00:00` →
  строка `YYYY-MM-DD`; `pd.to_datetime(..., format=DAY_CSV_FORMAT)` (fail-loud) →
  `.dt.strftime("%Y-%m-%d")`.
- `_vat_multiplier(date_series) -> pd.Series` — множитель по году из `date`-строк
  (`.str[:4]`): ≥ 2026 → 1.22, иначе 1.20 (зеркало avito `_vat_divisor`).
- `_apply_stat_enrichment(df) -> pd.DataFrame` — по спеке §3: база
  `costs_without_nds ← spend` (to_numeric → float → round(2)), `costs_nds = база ×
  _vat_multiplier(date)`, `ak=0.5`, `costs_nds_ak`, `costs_without_nds_ak` (×1.5),
  `account_id=1`, `source_type_id=10`, `id_key_camp`.

### 3. Публичная функция

`get_campaigns_daily_stat(date_from, date_to)` — заменить стаб:
`_fetch_daily_stat(..., ["Day", "CampaignID"])` → empty-гейт → rename →
`_parse_day_column` → dropna(campaign_id) + empty-гейт → `campaign_id/int64`,
`impressions`/`clicks` → int64 → `_apply_stat_enrichment` →
`reindex(CAMPAIGNS_STAT_COLUMNS)` + `reset_index`.

### 4. Изменения в существующем коде — нет (стабы 3/4 не трогаются)

## Юнит-тесты — `bidease/tests/test_get_campaigns_daily_stat.py`

Мок как в тестах функции 1 (реальный `requests.Response`, ISO-8859-1 из заголовков).
Кейсы: нормальный CSV (2 дня × 2 кампании; проверка date-парсинга, расходов 1.22,
ключей, порядка колонок); граница года (строки 12/31/2025 и 01/01/2026 → 1.20 и 1.22);
пустой CSV/тело; строка без `campaign_id`; `ValueError` при `date_to < date_from` и
выходе за год (запрос НЕ уходит).

## Smoke-тест — `bidease/smoke_tests/test_get_campaigns_daily_stat.py`

Конвенция проекта: даты из `.env` (`TEST_START_DATE`/`TEST_END_DATE`), после успешного
вызова — очистка `get_campaigns_daily_stat_*.csv`, сохранение
`get_campaigns_daily_stat_{from}_{to}.csv` (cp1251, errors="replace"), показ shape/columns/
5 строк из СОХРАНЁННОГО CSV.

## Порядок реализации

1. Константы + 4 хелпера. 2. Тело функции. 3. Юнит-тесты → зелёные.
4. Smoke → зелёный, показ таблицы. 5. Блок в `info/01_functions_implemented.md`.
6. Commit. (Независимое ревью — консолидированно после функций 2–4.)

## Проверка

- [ ] Колонки/порядок `CAMPAIGNS_STAT_COLUMNS`; пустой ответ → пустой DataFrame
- [ ] Даты `YYYY-MM-DD`; НДС по году строки; `spend` → база без НДС (направление обратное avito)
- [ ] Валидация периода до запроса; существующие функции без регрессий
