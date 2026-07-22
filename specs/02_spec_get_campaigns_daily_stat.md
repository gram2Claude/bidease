# Spec for get_campaigns_daily_stat

## Summary

Публичная функция в `bidease.py`: **дневная статистика по кампаниям** (DataFrame:
одна строка = день × кампания). Группировка выполняется на сервере
(`group=Day+CampaignID`) — **один GET на весь период**, без перебора сущностей
и пагинации (специфика Bidease).

## Functional Requirements

### 1. Сигнатура функции

```python
def get_campaigns_daily_stat(date_from: str, date_to: str) -> pd.DataFrame:
```

`date_from` / `date_to` — `YYYY-MM-DD`, **включительно** (эксклюзивность `todate`
API учитывается внутри: `todate = date_to + 1 день`, `_todate_exclusive`).

### 2. Алгоритм

**[SYNC] Синхронный паттерн:**

1. `_validate_period(date_from, date_to)` — формат, `date_from ≤ date_to`,
   в пределах 1 года от текущей даты (лимит API).
2. `GET /api/reporting/v1/stats`: `api-token`, `fromdate=date_from`,
   `todate=_todate_exclusive(date_to)`, `group=Day`, `group=CampaignID`.
3. Ответ — CSV: 35 колонок метрик + группировки `day`, `campaignid` (нижний регистр).
4. Переименование по `GROUP_CSV_RENAME` (`day→date`, `campaignid→campaign_id`);
   из метрик остаются только `impressions`, `clicks`, `spend`.
5. **Парсинг даты:** значения `day` — `MM/DD/YYYY 00:00:00` (факт API 2026-07-22) →
   строка `YYYY-MM-DD` (явный формат `%m/%d/%Y %H:%M:%S`, при несовпадении — громкая
   ошибка, не тихий NaN).
6. Отбросить строки без `campaign_id`; `campaign_id → int64`. Дедупликация не нужна —
   уникальность день×кампания обеспечивает серверная группировка.
7. Обогащение (общий хелпер `_apply_stat_enrichment`, раздел 3) и
   `reindex(columns=CAMPAIGNS_STAT_COLUMNS)`.

### 3. Возвращаемый DataFrame

Порядок — `CAMPAIGNS_STAT_COLUMNS` (уже в скаффолде):

| Колонка | Тип | Описание |
|---------|-----|----------|
| `date` | string `YYYY-MM-DD` | из CSV `day` (`MM/DD/YYYY 00:00:00`) |
| `campaign_id` | int64 | CSV `campaignid` |
| `impressions` | int64 | CSV `impressions` |
| `clicks` | int64 | CSV `clicks` |
| `costs_nds` | float | вычисляется: `costs_without_nds × (1 + ставка_НДС года даты)` |
| `costs_without_nds` | float | ← CSV `spend` (**доллары БЕЗ НДС**, решение 2026-07-21), округление до 2 знаков |
| `ak` | float | константа `0.5` |
| `costs_nds_ak` | float | `costs_nds × 1.5` |
| `costs_without_nds_ak` | float | `costs_without_nds × 1.5` |
| `account_id` | int64 | константа `1` |
| `source_type_id` | int64 | константа `10` |
| `id_key_camp` | string | `"1_" + campaign_id` |

#### Обязательное обогащение (соглашение проекта; ⚠️ направление ОБРАТНОЕ avito)

`spend` у Bidease — доллары **БЕЗ НДС** → база `costs_without_nds ← spend`
(float, **round(2)** — округляется только база, производные не округляются,
зеркально avito, где округлялась база `costs_nds`), затем
`costs_nds = costs_without_nds × _vat_multiplier(date)`; множитель по году даты
строки: год ≥ 2026 → **1.22**, ранее → **1.20**. `ak = 0.5`;
`costs_nds_ak = costs_nds × 1.5`; `costs_without_nds_ak = costs_without_nds × 1.5`;
`account_id = 1`; `source_type_id = 10`; `id_key_camp = "1_" + campaign_id`.
Валюта не пересчитывается — значения остаются в долларах.

### 4. Изменения в `bidease.py`

- Реализовать тело `get_campaigns_daily_stat()` (заменить стаб).
- Новые приватные хелперы (переиспользуются функциями статистики):
  `_fetch_daily_stat(date_from, date_to, groups)` — валидация + GET;
  `_parse_day_column(df)` — `day` → `YYYY-MM-DD`;
  `_vat_multiplier(date_series)` — множитель НДС по году (зеркало avito `_vat_divisor`);
  `_apply_stat_enrichment(df)` — блок обогащения расходов.
- Обновить docstring модуля.

## Ограничения API

| Ограничение | Значение | Реализация |
|-------------|----------|------------|
| Период | ≤ 1 года от текущей даты | `_validate_period` на входе |
| `todate` | эксклюзивна | `_todate_exclusive(date_to)` |
| Группировок | ≤ 7 | используем 2 |
| Rate limits | не документированы | 429-backoff в `_get_report` |
| Ошибки | 401 пустое тело; 400 plain-text | `raise_for_status` |

## Possible Edge Cases

- **Пустой период** (нет событий) → только заголовок → пустой DataFrame с колонками
  `CAMPAIGNS_STAT_COLUMNS`. Не ошибка.
- **Период через границу года** (2025→2026): ставка НДС считается **по-строчно** по году
  даты — в одном DataFrame будут строки с 1.20 и 1.22.
- **Свежие даты (сегодня/вчера)** — счётчики API «плывут» между запросами
  (факт 2026-07-22); повторный вызов может дать немного иные суммы. Не дефект функции.
- **`date_to` = сегодня** — допустимо; данные за сегодня частичные.
- **Неожиданный формат `day`** → громкое исключение парсинга (fail-loud, не NaN).

## Acceptance Criteria

- [ ] DataFrame ровно с колонками `CAMPAIGNS_STAT_COLUMNS` в заданном порядке.
- [ ] `date` — строки `YYYY-MM-DD`; исходный `MM/DD/YYYY 00:00:00` распарсен точно.
- [ ] Расходы: `costs_without_nds == round(spend, 2)`;
      `costs_nds == costs_without_nds × 1.22` для дат 2026+ (1.20 — ранее);
      `*_ak == × 1.5`; направление расчёта обратное avito.
- [ ] `id_key_camp == "1_" + str(campaign_id)`; `source_type_id == 10`.
- [ ] Пустой результат → пустой DataFrame с правильными колонками, без исключений.
- [ ] Невалидный период (`date_to < date_from`; выход за год) → `ValueError` до запроса.
- [ ] Unit-тесты (мок HTTP): нормальный CSV, пустой, граница года НДС, строка без
      `campaign_id`, валидация периода.
- [ ] Smoke-тест на живом API; CSV `bidease/raw_data/get_campaigns_daily_stat_{from}_{to}.csv`
      (cp1251), старые выгрузки функции удалены, показаны первые 5 строк из CSV.

## Open Questions

- Нет (формат `day` и семантика `spend` установлены фактами 2026-07-21/22).
