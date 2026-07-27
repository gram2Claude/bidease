# Spec for get_campaigns_daily_stat

## Summary

Публичная функция в `bidease.py`: **дневная статистика по кампаниям** (DataFrame:
одна строка = день × кампания). Группировка выполняется на сервере
(`group=Day+CampaignID`) — **один GET на весь период**, без перебора сущностей
и пагинации (специфика Bidease).

> **Ревизия 2026-07-27 (решение пользователя):** поля `costs_*` конвенции проекта
> подразумевают **рубли**, а Bidease отдаёт расход в **долларах США**. Поэтому вся
> рублёвая группа (`costs_nds`, `costs_without_nds`, `costs_nds_ak`,
> `costs_without_nds_ak`) и константа агентской комиссии `ak` из итоговой таблицы
> **убраны**; расход отдаётся ровно одним полем **`costs_usd`** ← `spend` как есть.
> Логика НДС (`_vat_multiplier`) удалена из библиотеки целиком.

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
| `costs_usd` | float | ← CSV `spend` (**доллары США как есть**), округление до 2 знаков |
| `account_id` | int64 | константа `1` |
| `source_type_id` | int64 | константа `10` |
| `id_key_camp` | string | `"1_" + campaign_id` |

#### Обязательное обогащение (соглашение проекта; ⚠️ отличие от avito — валюта)

Расход — единственное поле `costs_usd ← spend` (float, **round(2)**). НДС и
агентская комиссия **не применяются**, валюта **не пересчитывается**: значения
остаются в долларах США, налоги/курс — на стороне приёмника данных
(решение 2026-07-27). Далее `account_id = 1`; `source_type_id = 10`;
`id_key_camp = "1_" + campaign_id`.

### 4. Изменения в `bidease.py`

- Реализовать тело `get_campaigns_daily_stat()` (заменить стаб).
- Новые приватные хелперы (переиспользуются функциями статистики):
  `_fetch_daily_stat(date_from, date_to, groups)` — валидация + GET;
  `_parse_day_column(df)` — `day` → `YYYY-MM-DD`;
  `_apply_stat_enrichment(df)` — блок обогащения расходов
  (ревизия 2026-07-27: `_vat_multiplier` удалён — НДС не считается).
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
- **Период через границу года** (2025→2026): на расход не влияет — `costs_usd` равен
  `round(spend, 2)` в любом году (НДС не применяется, ревизия 2026-07-27).
- **Показы зависят от разреза группировки** (факт 2026-07-27): суммы `impressions`
  этой функции и `get_creatives_daily_stat` за один период расходятся на 0.1–0.5 %
  — свойство агрегации Bidease, не дефект функции (`clicks`/`spend` совпадают точно).
- **Свежие даты (сегодня/вчера)** — счётчики API могут обновляться на лету; для
  устоявшихся дат повторный запрос даёт идентичные числа (факт 2026-07-27).
- **`date_to` = сегодня** — допустимо; данные за сегодня частичные.
- **Неожиданный формат `day`** → громкое исключение парсинга (fail-loud, не NaN).

## Acceptance Criteria

- [ ] DataFrame ровно с колонками `CAMPAIGNS_STAT_COLUMNS` в заданном порядке.
- [ ] `date` — строки `YYYY-MM-DD`; исходный `MM/DD/YYYY 00:00:00` распарсен точно.
- [ ] Расходы: `costs_usd == round(spend, 2)` (доллары как есть); полей
      `costs_nds`/`costs_without_nds`/`costs_*_ak`/`ak` в DataFrame НЕТ.
- [ ] `id_key_camp == "1_" + str(campaign_id)`; `source_type_id == 10`.
- [ ] Пустой результат → пустой DataFrame с правильными колонками, без исключений.
- [ ] Невалидный период (`date_to < date_from`; выход за год) → `ValueError` до запроса.
- [ ] Unit-тесты (мок HTTP): нормальный CSV, пустой, граница года (расход неизменен),
      строка без `campaign_id`, валидация периода.
- [ ] Smoke-тест на живом API; CSV `bidease/raw_data/get_campaigns_daily_stat_{from}_{to}.csv`
      (cp1251), старые выгрузки функции удалены, показаны первые 5 строк из CSV.

## Open Questions

- Нет (формат `day` и семантика `spend` установлены фактами 2026-07-21/22).
