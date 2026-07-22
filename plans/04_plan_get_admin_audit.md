# Plan: get_admin_audit

## Контекст

На основании `specs/04_spec_get_admin_audit.md`. Агрегат без собственного запроса —
поверх `get_campaigns_daily_stat` + `owner_id` из `get_campaign_dict` (зеркало avito).

## Изменения в `bidease.py`

### 1. Константы — `ADMIN_AUDIT_COLUMNS` уже в скаффолде; новых нет.

### 2. Приватные функции — новых нет.

### 3. Публичная функция

`get_admin_audit(date_from, date_to)` — заменить стаб:

1. `stats = get_campaigns_daily_stat(date_from, date_to)`; `stats.empty` →
   `pd.DataFrame(columns=ADMIN_AUDIT_COLUMNS)`.
2. `camps = get_campaign_dict()[["campaign_id", "owner_id"]]` →
   `stats.merge(camps, on="campaign_id", how="left")`.
3. `owner_id = fillna(1).astype("int64")` — страховка от потери строк в groupby
   (NaN в ключе молча выбрасывает строку).
4. `groupby(["date", "account_id", "source_type_id", "owner_id"], as_index=False)
   [["impressions", "clicks", "costs_nds", "costs_without_nds"]].sum()`.
5. `costs_without_nds = round(2)` (база Bidease; `costs_nds` не округляется —
   зеркально avito, где округлялась их база `costs_nds`).
6. `chef_flag = 1` → `reindex(ADMIN_AUDIT_COLUMNS)` + `reset_index`.

### 4. Изменения в существующем коде — нет.

## Юнит-тесты — `bidease/tests/test_get_admin_audit.py`

Мок `requests.Session.get` с диспетчеризацией по параметрам запроса (запрос с
`group=AdvertiserID` → CSV справочника; с `group=Day` → CSV статистики).
Кейсы: нормальный агрегат (2 кампании × 2 дня → 2 строки, суммы сходятся, chef_flag=1,
колонки/порядок); пустая статистика → пустой DataFrame (справочник НЕ запрашивается —
проверить счётчиком вызовов); кампания в статистике вне справочника → owner_id=1,
строка не потеряна.

## Smoke-тест — `bidease/smoke_tests/test_get_admin_audit.py`

Как план 02: даты из `.env`, очистка `get_admin_audit_*.csv`, сохранение
`get_admin_audit_{from}_{to}.csv` (cp1251), показ 5 строк из CSV.

## Порядок реализации

1. Тело функции. 2. Юнит-тесты → зелёные. 3. Smoke → зелёный.
4. Блок в реестре. 5. Commit. 6. Консолидированное независимое ревью функций 2–4;
   существенные находки → фикс → раунд. 7. Статус/память/итоговый push.

## Проверка

- [ ] Колонки/порядок `ADMIN_AUDIT_COLUMNS`; суммы равны дневной статистике
- [ ] Пустой период — без второго запроса; owner_id NaN → 1 без потери строк
