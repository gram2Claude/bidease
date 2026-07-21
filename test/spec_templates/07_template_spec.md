# Spec for {SPEC_FUNCTION_NAME}

<!-- 
Имя файла: specs/{NN}_spec_{SPEC_FUNCTION_NAME}.md
где {NN} — порядковый номер в хронологии реализации (01, 02, 03 ...)
      "spec" — фиксированное ключевое слово (показывает, что это спецификация)
Пример: specs/01_spec_get_campaign_dict.md
        specs/02_spec_get_campaign_daily_stat.md
        specs/03_spec_get_campaign_reach_daily_stat.md
-->

## Summary

Новая публичная функция в `{MODULE_NAME}.py`, возвращающая {SPEC_RETURN_DESCRIPTION}.

{SPEC_SPECIAL_SEMANTICS}
<!-- Пример для охвата:
«Reach — кумулятивный показатель (уникальные пользователи за период).
НЕЛЬЗЯ суммировать ни по дням, ни по объявлениям, ни в каком виде.
Для каждого дня D запрашивается [global_start_date, D] с groupBy=NO_GROUP_BY.
Campaign-level reach берётся из строки «Всего» в CSV (API дедуплицирует уникальных пользователей).
increment вычисляется локально: reach[D] - reach[D-1].
В smoke-тесте: global_start_date = TEST_GLOBAL_START_DATE (не TEST_START_DATE!).
Передача TEST_START_DATE даёт охват за 1 день вместо накопительного — числа будут неверные.» -->
<!-- Удали эту строку если функция простая (нет особой семантики) -->

## Functional Requirements

### 1. Сигнатура функции

```python
def {SPEC_FUNCTION_NAME}(
    {SPEC_PARAMS}
    # Пример:
    # date_from: str,  # YYYY-MM-DD — начало периода
    # date_to: str,    # YYYY-MM-DD — конец периода
) -> pd.DataFrame:
```

### 2. Алгоритм

<!-- Выбери подходящий паттерн и удали второй -->

**[ASYNC] Асинхронный паттерн:**
- Для каждого дня D в [{SPEC_DATE_FROM}, {SPEC_DATE_TO}]:
  - Для каждого батча `{ENTITY_NAME}` (≤{BATCH_SIZE} шт. — ограничение API):
    - `POST {SUBMIT_PATH}` с телом:
      ```json
      {SPEC_REQUEST_BODY_EXAMPLE}
      ```
    - Poll UUID → скачать отчёт → взять данные из `{SPEC_RESPONSE_ROWS_PATH}`
- Строки с нулевыми показателями пропускаются (опционально)

**[ASYNC] Кэш сырых данных:**
Функция принимает `raw_cache_dir: str | Path | None = None`.
Каждый CSV-отчёт сохраняется как `raw_data/raw_files/raw_{date_from}_{date_to}_{campaign_id}_{day}.csv`.
При повторном запуске с теми же датами данные берутся из кэша, API не вызывается.
При смене дат `_evict_stale_raw_cache()` удаляет `raw_*.csv` с несоответствующим префиксом.
Если другая функция использует тот же endpoint с теми же датами — кэш разделяется автоматически.

**[ASYNC] Probe перед парсером:**
Если CSV-формат (кодировка, разделитель, структура строк) неизвестен или есть open questions —
перед реализацией парсера сделать probe: запросить один батч, сохранить сырые байты, изучить.
Только после подтверждения формата писать финальный парсер.

**[SYNC] Синхронный паттерн:**
- `{SPEC_HTTP_METHOD} {SPEC_ENDPOINT_PATH}` с параметрами: `{SPEC_REQUEST_PARAMS}`
- Данные разбираются напрямую из `{SPEC_RESPONSE_ROWS_PATH}` ответа

### 3. Возвращаемый DataFrame

Все имена колонок — **snake_case** (например: `costs_nds`, `ad_id`, `campaign_name`).

| Колонка | Тип | Описание |
|---------|-----|----------|
| {SPEC_COL_1} | {SPEC_TYPE_1} | {SPEC_DESC_1} |
| {SPEC_COL_2} | {SPEC_TYPE_2} | {SPEC_DESC_2} |
| ... | | |

#### Обязательное обогащение DataFrame (соглашение проекта)

Помимо полей из API, **каждая** функция добавляет в DataFrame фиксированный набор
константных и вычисляемых полей. Это соглашение проекта, оно действует для **всех**
функций без исключений.

**Для справочников** (без дат):

| Колонка | Тип | Источник | Описание |
|---------|-----|----------|----------|
| `account_id` | integer | константа `1` | пример, заменить при интеграции |
| `source_type_id` | integer | константа `9` | пример, заменить при интеграции |
| `product_id` | integer | константа `1` | пример |
| `product_name` | string | константа `"prod_test"` | пример |
| `camp_type` | string | константа `"camp_test"` | пример |
| `camp_category` | string | константа `"cat_test"` | пример |
| `id_key_camp` | string | вычисляется: `"1_" + campaign_id` | составной ключ |
| `owner_id` | integer | константа `1` | пример |

**Для статистики (без расходов):**

| Колонка | Тип | Источник | Описание |
|---------|-----|----------|----------|
| `account_id` | integer | константа `1` | пример |
| `source_type_id` | integer | константа `9` | пример |
| `id_key_camp` | string | вычисляется: `"1_" + campaign_id` | составной ключ |
| `id_key_ad` | string | вычисляется: `id_key_camp + "_" + ad_id` | **только для ad-level** |

**Для статистики с расходами (и ad-level, и campaign-level):**

| Колонка | Тип | Источник | Описание |
|---------|-----|----------|----------|
| `costs_without_nds` | float | вычисляется: `costs_nds / (1 + ставка_НДС)` (ставка по году даты строки, см. ниже) | расход без НДС |
| `ak` | float | константа `0.5` | агентская комиссия 50% |
| `costs_nds_ak` | float | вычисляется: `costs_nds * (1 + ak)` | расход с НДС и комиссией |
| `costs_without_nds_ak` | float | вычисляется: `costs_without_nds * (1 + ak)` | расход без НДС с комиссией |
| `account_id` | integer | константа `1` | пример |
| `source_type_id` | integer | константа `9` | пример |
| `id_key_camp` | string | вычисляется: `"1_" + campaign_id` | составной ключ |
| `id_key_ad` | string | вычисляется: `id_key_camp + "_" + ad_id` | **только для ad-level** |

> **Ставка НДС (по году даты строки):** `costs_without_nds = costs_nds / (1 + ставка)`, где
> ставка = **22% при year ≥ 2026** (делитель `1.22`), **20% при year < 2026** (делитель `1.20`).
> Вычисляется per-row по году из колонки `date` (в одном отчёте возможны дни разных лет).

> **Важно про `costs_nds`:** название означает «расход С НДС». Источник — поле API
> «Расход, ₽, с НДС» для BANNER. Если API возвращает поле без НДС (например,
> VIDEO_BANNER возвращает «Расход, ₽» без НДС), то `costs_nds` хранит то, что
> вернул API — название колонки в этом случае может вводить в заблуждение,
> обязательно зафиксировать это в комментарии spec и в реестре функций.

> **Тип `costs_nds`:** десятичный (**float**), округление до **2 знаков после запятой**
> сразу после чтения из API — `pd.to_numeric(..., errors="coerce").astype(float).round(2)` —
> **до** вычисления производных `costs_without_nds`/`costs_*_ak`. Даже если API отдаёт
> целые ₽, тип на выходе должен быть десятичным.

<!-- Для кумулятивной метрики (reach):
| increment | float | Прирост reach относительно предыдущей даты; для первой даты = reach |

ВАЖНО для reach: нельзя суммировать значения из строк данных CSV ни по объявлениям,
ни по дням — это даст дубли. Использовать только строку «Всего» (campaign-level, дедуплицировано API).
-->

### 4. Изменения в `{MODULE_NAME}.py`

- Добавить константу `{SPEC_COLUMNS_CONST}` = [список колонок]
- [Если нужен новый паттерн запроса] Расширить `_submit_report()` или `_fetch_..._data()` новыми параметрами
- Добавить приватный метод `_fetch_{SPEC_ENTITY}_for_{SPEC_SCOPE}()`
- Добавить публичную функцию `{SPEC_FUNCTION_NAME}()`
- Обновить docstring модуля

## Ограничения API

| Ограничение | Значение | Реализация |
|-------------|----------|------------|
| {ENTITY_NAME} в одном запросе | макс **{BATCH_SIZE}** | `BATCH_SIZE = {BATCH_SIZE}`, разбивка батчами |
| Одновременных задач | макс **{MAX_CONCURRENT}** | `MAX_CONCURRENT`, `_active_uuids`, `_wait_for_free_slot` |
| Скачиваний отчётов в сутки | макс **1000** | мониторится оператором; не enforced в коде |
| Длительность периода | макс **{PERIOD_MAX_DAYS}** дней | документируется как precondition |
| Burst-rate-limit | недокументирован | `MIN_SUBMIT_INTERVAL_SEC = 3` — пейсинг между POST'ами |
| {SPEC_EXTRA_CONSTRAINT} | {SPEC_EXTRA_VALUE} | {SPEC_EXTRA_IMPL} |

**Поведение при 429:**
- Экспоненциальный backoff: базовый интервал {RATE_LIMIT_BASE_SEC} сек, удваивается
- Макс. {RATE_LIMIT_RETRY_MAX} повторов
- Учитывается заголовок `Retry-After` если присутствует

## Possible Edge Cases

- `{SPEC_FIELD_NAME}` отсутствует в ответе или называется иначе (`"{SPEC_FIELD_ALT_1}"`) —
  обрабатывается через `_pick(row, "{SPEC_FIELD_NAME}", "{SPEC_FIELD_ALT_1}")`
- Нет данных за период — возвращается `pd.DataFrame(columns={SPEC_COLUMNS_CONST})`
- `date_from == date_to` — один запрос за один день, валидно
- {SPEC_EDGE_1} — {SPEC_EDGE_1_HANDLER}
- {SPEC_EDGE_2} — {SPEC_EDGE_2_HANDLER}
<!-- Для кумулятивного паттерна добавь:
- global_start_date > date_from — задокументировать как precondition или валидировать на входе
- Период [global_start_date, date_to] превышает {PERIOD_MAX_DAYS} дней — ограничение API
-->

## Acceptance Criteria

- [ ] `{SPEC_FUNCTION_NAME}({SPEC_EXAMPLE_CALL})` возвращает DataFrame с колонками `{SPEC_COLUMNS_LIST}`
- [ ] {SPEC_ROW_INVARIANT}
  <!-- Пример: «В DataFrame ровно N уникальных дат» или «Одна строка на entity × день» -->
- [ ] {SPEC_METRIC_INVARIANT}
  <!-- Пример: «costs_nds ≥ 0 для всех строк» -->
- [ ] При отсутствии данных возвращается пустой DataFrame с правильными колонками
- [ ] Существующие функции работают без изменений (нет регрессий)
- [ ] [ASYNC] Клиент не превышает `MAX_CONCURRENT` одновременных задач
- [ ] [ASYNC] Между submit-запросами выдерживается интервал ≥ `MIN_SUBMIT_INTERVAL_SEC` сек
<!-- Для кумулятивного паттерна добавь:
- [ ] Для первой даты в диапазоне `increment == metric[t]` (fillna значением метрики; не NaN)
- [ ] Для последующих дат `increment == metric[t] - metric[t-1]` в рамках одной сущности
-->

## Open Questions

- {SPEC_OPEN_Q_1}
- {SPEC_OPEN_Q_2}
<!-- Примеры:
- Как называется поле {METRIC} в totals: «reach», «uniques» или другое? — проверить реальным запросом.
- groupBy=NO_GROUP_BY возвращает данные в totals или в rows? Предполагаем totals.
-->
