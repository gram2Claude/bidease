# Spec for get_admin_audit

## Summary

Публичная функция в `bidease.py`: **сводный аудит по дням** (admin_audit).
Собственного запроса к API нет — **агрегат поверх `get_campaigns_daily_stat`**
(суммы метрик по дням), `owner_id` подтягивается из `get_campaign_dict`
(зеркально avito), `chef_flag = 1`.

## Functional Requirements

### 1. Сигнатура функции

```python
def get_admin_audit(date_from: str, date_to: str) -> pd.DataFrame:
```

`date_from` / `date_to` — `YYYY-MM-DD`, включительно (валидация — внутри
`get_campaigns_daily_stat`).

### 2. Алгоритм

1. `stats = get_campaigns_daily_stat(date_from, date_to)`; пустой →
   пустой DataFrame с колонками `ADMIN_AUDIT_COLUMNS`.
2. `camps = get_campaign_dict()[["campaign_id", "owner_id"]]`;
   `merge(camps, on="campaign_id", how="left")`.
3. **Страховка**: `owner_id` после merge может быть NaN (кампания в статистике,
   но не в справочнике — например, `date_from` на 365-й день назад при периоде
   справочника 364 дня; NaN в ключе groupby молча теряет строки) →
   `fillna(1)` (дефолт конвенции) + `astype("int64")`.
4. `groupby(["date", "account_id", "source_type_id", "owner_id"], as_index=False)`
   → суммы `impressions`, `clicks`, `costs_nds`, `costs_without_nds`.
5. `costs_without_nds` (— **база** расчёта у Bidease) после суммирования →
   `round(2)`; `costs_nds` не округляется (зеркально avito, где округлялась
   база `costs_nds`).
6. `chef_flag = 1`; `reindex(columns=ADMIN_AUDIT_COLUMNS)`.

### 3. Возвращаемый DataFrame

Порядок — `ADMIN_AUDIT_COLUMNS` (в скаффолде):

| Колонка | Тип | Описание |
|---------|-----|----------|
| `date` | string `YYYY-MM-DD` | из статистики кампаний |
| `account_id` | int64 | константа `1` (ключ группировки) |
| `source_type_id` | int64 | константа `10` (ключ группировки) |
| `owner_id` | int64 | из `get_campaign_dict` (merge по `campaign_id`; NaN → 1) |
| `impressions` | int64 | сумма по дню |
| `clicks` | int64 | сумма по дню |
| `costs_nds` | float | сумма по дню (не округляется) |
| `costs_without_nds` | float | сумма по дню, round(2) — база |
| `chef_flag` | int64 | константа `1` (дефолт) |

### 4. Изменения в `bidease.py`

- Реализовать тело `get_admin_audit()` (заменить стаб). Новых хелперов не требуется.
- Обновить docstring модуля.

## Ограничения API

Наследуются от `get_campaigns_daily_stat` (+ один GET справочника из
`get_campaign_dict`). Итого 2 HTTP-запроса на вызов.

## Possible Edge Cases

- Пустая статистика → пустой DataFrame с колонками `ADMIN_AUDIT_COLUMNS`
  (справочник не запрашивается).
- Кампания в статистике отсутствует в справочнике → `owner_id = 1` (страховка §2.3),
  строки НЕ теряются.
- Все константы (`account_id`, `source_type_id`) одинаковы → фактическая
  группировка = по `date` × `owner_id`; при константном `owner_id=1` — по дням.
- Свежие даты «плывут» — суммы двух последовательных вызовов могут отличаться.

## Acceptance Criteria

- [ ] DataFrame ровно с колонками `ADMIN_AUDIT_COLUMNS` в порядке.
- [ ] Суммы `impressions`/`clicks`/`costs_*` равны суммам строк дневной статистики
      по соответствующему дню.
- [ ] `chef_flag == 1`; `owner_id` из справочника (NaN → 1, строки не теряются).
- [ ] Пустой период → пустой DataFrame с колонками, без исключений.
- [ ] Unit-тесты (мок HTTP): нормальный агрегат (2 кампании × 2 дня → 2 строки),
      пустая статистика, кампания вне справочника (owner_id=1, строка жива).
- [ ] Smoke-тест на живом API; CSV `get_admin_audit_{from}_{to}.csv` (cp1251),
      очистка старых, 5 строк из CSV.

## Open Questions

- Нет.
