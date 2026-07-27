# Spec for get_creatives_daily_stat

## Summary

Публичная функция в `bidease.py`: **дневная статистика по креативам** (DataFrame:
одна строка = день × кампания × креатив). Иерархия Bidease: кампания → креатив
(уровня групп нет). Серверная группировка `group=Day+CampaignID+CreativeID` —
**один GET на весь период**.

> **Ревизия 2026-07-27:** рублёвые `costs_*`-поля и `ak` убраны, расход — одно поле
> `costs_usd` ← `spend` (доллары как есть). Обоснование — см. spec 02.

## Functional Requirements

### 1. Сигнатура функции

```python
def get_creatives_daily_stat(date_from: str, date_to: str) -> pd.DataFrame:
```

`date_from` / `date_to` — `YYYY-MM-DD`, включительно (`todate = date_to + 1`).

### 2. Алгоритм

Полностью зеркален `get_campaigns_daily_stat` (spec 02) с отличиями:

1. Группировки запроса: `group=Day`, `group=CampaignID`, `group=CreativeID`.
2. CSV-группировки: `day`, `campaignid`, `creativeid` → `date`, `campaign_id`,
   `creative_id` (`GROUP_CSV_RENAME`).
3. Отбросить строки без `campaign_id` **или** без `creative_id` (оба нужны для
   `id_key_ad`); оба → int64.
4. Обогащение `_apply_stat_enrichment` + **дополнительно**
   `id_key_ad = id_key_camp + "_" + creative_id` (групп в Bidease нет → без
   group-звена, решение проекта 2026-07-21).
5. `reindex(columns=CREATIVES_STAT_COLUMNS)`.

### 3. Возвращаемый DataFrame

Порядок — `CREATIVES_STAT_COLUMNS` (в скаффолде): колонки spec 02 + после
`campaign_id` идёт `creative_id` (int64, CSV `creativeid`), в конце —
`id_key_ad` (string, `id_key_camp + "_" + creative_id`).

Обогащение расходов — идентично spec 02 (`costs_usd ← spend`, round(2), без НДС и
комиссии; `account_id=1`, `source_type_id=10`).

### 4. Изменения в `bidease.py`

- Реализовать тело `get_creatives_daily_stat()` (заменить стаб) на общих хелперах
  spec 02 (`_fetch_daily_stat`, `_parse_day_column`, `_apply_stat_enrichment`).
- Обновить docstring модуля.

## Ограничения API

Как в spec 02 (группировок — 3 из ≤7).

## Possible Edge Cases

- Пустой период → пустой DataFrame с колонками `CREATIVES_STAT_COLUMNS`.
- Граница года на расход не влияет (`costs_usd = round(spend, 2)` в любом году).
- Один креатив в нескольких кампаниях — строки раздельны по `campaign_id`
  (`id_key_ad` различается) — корректно.
- Строка без `creative_id` при живом `campaign_id` → отброшена (нужна для ключа).
- Сумма показов **не обязана** совпадать с `get_campaigns_daily_stat` за тот же период
  (разрез `+CreativeID` даёт другой агрегат показов у Bidease — факт 2026-07-27,
  расхождение 0.1–0.5 %; `clicks`/`spend` совпадают точно). Не дефект.

## Acceptance Criteria

- [ ] DataFrame ровно с колонками `CREATIVES_STAT_COLUMNS` в порядке.
- [ ] `id_key_ad == "1_" + campaign_id + "_" + creative_id` для всех строк.
- [ ] Расходы/даты/константы — как в spec 02 (`costs_usd`, без НДС и комиссии).
- [ ] Пустой результат → пустой DataFrame с колонками, без исключений.
- [ ] Unit-тесты (мок HTTP): нормальный CSV, пустой, строка без `creative_id`,
      `id_key_ad`, граница года.
- [ ] Smoke-тест на живом API; CSV `get_creatives_daily_stat_{from}_{to}.csv` (cp1251),
      очистка старых, 5 строк из CSV.

## Open Questions

- Нет.
