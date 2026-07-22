# Plan: get_creatives_daily_stat

## Контекст

На основании `specs/03_spec_get_creatives_daily_stat.md`. Зеркало плана 02 на общих
хелперах; отличия — третья группировка и `id_key_ad`.

## Изменения в `bidease.py`

### 1. Константы — `CREATIVES_STAT_COLUMNS` уже в скаффолде; новых нет.

### 2. Приватные функции — переиспользуются из плана 02 (`_fetch_daily_stat`,
`_parse_day_column`, `_apply_stat_enrichment`); новых нет.

### 3. Публичная функция

`get_creatives_daily_stat(date_from, date_to)` — заменить стаб:
`_fetch_daily_stat(..., ["Day", "CampaignID", "CreativeID"])` → empty-гейт → rename →
`_parse_day_column` → `dropna(subset=["campaign_id", "creative_id"])` + empty-гейт →
оба ID → int64, метрики → int64 → `_apply_stat_enrichment` →
`id_key_ad = id_key_camp + "_" + creative_id.astype(str)` →
`reindex(CREATIVES_STAT_COLUMNS)` + `reset_index`.

### 4. Изменения в существующем коде — нет.

## Юнит-тесты — `bidease/tests/test_get_creatives_daily_stat.py`

Кейсы: нормальный CSV (2 креатива в одной кампании × 2 дня; `id_key_ad`, порядок
колонок, расходы); строка без `creative_id` → отброшена; пустой CSV; один креатив
в двух кампаниях → раздельные `id_key_ad`.

## Smoke-тест — `bidease/smoke_tests/test_get_creatives_daily_stat.py`

Как план 02: даты из `.env`, очистка `get_creatives_daily_stat_*.csv`, сохранение
`get_creatives_daily_stat_{from}_{to}.csv` (cp1251), показ 5 строк из CSV.

## Порядок реализации

1. Тело функции. 2. Юнит-тесты → зелёные. 3. Smoke → зелёный.
4. Блок в реестре. 5. Commit. (Ревью — консолидированно.)

## Проверка

- [ ] Колонки/порядок `CREATIVES_STAT_COLUMNS`; `id_key_ad` без group-звена
- [ ] Пустой ответ → пустой DataFrame; обогащение идентично функции 2
