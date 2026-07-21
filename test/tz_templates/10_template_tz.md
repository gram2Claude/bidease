# ТЗ: {API_NAME} API — портирование на {TARGET_LANG}

<!--
Имя выходного файла: TZ_{MODULE_NAME}_{TARGET_LANG}.pdf
Сохрани заполненную версию как: specs/TZ_{MODULE_NAME}_{TARGET_LANG}.md

Плейсхолдеры:
  {API_NAME}          — человекочитаемое название API (из анкеты A1)
  {MODULE_NAME}       — имя модуля/репозитория (из анкеты A2)
  {BASE_URL}          — базовый URL API (из анкеты B1)
  {TARGET_LANG}       — целевой язык (PHP / Go / Java / ...)
  {ENTITY_NAME}       — название основной сущности (campaign / product / order / ...)
  {ENTITY_NAME_PLURAL}— множественное число (campaigns / products / orders / ...)
  {ENV_VAR_1}         — переменная окружения для первого credentials (CLIENT_ID)
  {ENV_VAR_2}         — переменная окружения для второго credentials (CLIENT_SECRET)
  {BATCH_SIZE}        — максимум сущностей в одном запросе (из CLAUDE.md)
  {MAX_CONCURRENT}    — максимум параллельных задач (из CLAUDE.md)
  {PERIOD_MAX_DAYS}   — максимум дней в одном отчёте (из CLAUDE.md)
  {POLL_INTERVAL_SEC} — интервал polling (из константы в {MODULE_NAME}.py)
  {POLL_MAX_ATTEMPTS} — максимум попыток polling (из константы)
  {RATE_LIMIT_BASE_SEC} — начальная пауза при 429 (из константы)
  {RATE_LIMIT_RETRY_MAX} — максимум повторов при 429 (из константы)
  {TOKEN_TTL_SEC}     — время жизни токена в секундах (из ответа API /token)

Блоки вариантов — Claude удаляет неподходящие целиком:
  [OAUTH ONLY]     / [/OAUTH ONLY]     — только для OAuth 2.0
  [API KEY ONLY]   / [/API KEY ONLY]   — только для статического API-ключа
  [ASYNC ONLY]     / [/ASYNC ONLY]     — только для асинхронного паттерна
  [SYNC ONLY]      / [/SYNC ONLY]      — только для синхронного паттерна
  [CUMULATIVE]     / [/CUMULATIVE]     — только если есть кумулятивная метрика (reach)
-->

Эталонная реализация: `{MODULE_NAME}.py` (Python).
Цель — портировать функциональность на {TARGET_LANG} с сохранением структуры выходных данных.

---

## 1. Цель проекта

Разработать {TARGET_LANG}-библиотеку для работы с {API_NAME}.
Библиотека загружает справочник {ENTITY_NAME_PLURAL} и собирает дневную статистику
({STAT_METRICS_BRIEF}).
<!-- Пример {STAT_METRICS_BRIEF}: «показы, клики, расход, охват, видео-метрики» -->

Выход каждой публичной функции — структурированный массив строк (или объект-обёртка),
эквивалентный pandas DataFrame в Python-эталоне.

---

## 2. Общая логика работы библиотеки

Все функции статистики работают по одной схеме:

1. **Получить справочник {ENTITY_NAME_PLURAL}.**
   Один запрос `GET {ENTITY_LIST_PATH}` возвращает все {ENTITY_NAME_PLURAL} аккаунта.
   Из каждой берём `{ENTITY_ID_FIELD}` (привести к строке) и тип/статус если нужна фильтрация.

2. **Сформировать список дат.**
   Из параметров `date_from` / `date_to` — массив отдельных дней (YYYY-MM-DD).

3. **Разбить {ENTITY_NAME_PLURAL} на батчи.**
   API принимает максимум `{BATCH_SIZE}` {ENTITY_NAME_PLURAL} за раз → делим список на группы.

<!-- [ASYNC ONLY] -->
4. **Для каждой пары (день, батч) — запросить статистику.**
   `POST {SUBMIT_PATH}` со списком ID и одним днём.
   API не отдаёт данные сразу — возвращает UUID задачи.

5. **Ждать готовности отчёта (polling).**
   Каждые `{POLL_INTERVAL_SEC}` сек опрашиваем `GET {POLL_PATH_PREFIX}{UUID}`.
   Когда `state = OK` — переходим к скачиванию.

6. **Скачать и распаковать отчёт.**
   `GET {DOWNLOAD_PATH}?UUID=...` → CSV (1 {ENTITY_NAME}) или ZIP с CSV-файлами.
   Распаковываем, привязываем каждый CSV к своей {ENTITY_NAME}.
<!-- [/ASYNC ONLY] -->

<!-- [SYNC ONLY] -->
4. **Для каждой пары (день, батч) — запросить статистику.**
   `GET {SYNC_DATA_PATH}` с параметрами дат и ID — данные возвращаются сразу.
<!-- [/SYNC ONLY] -->

7. **Распарсить ответ.**
   В зависимости от функции: суммировать строки по (date, entity_id)
   или оставить гранулярность без агрегации.

8. **Собрать итоговый результат.**
   Все строки из всех дней и батчей объединить в один массив с фиксированными колонками.

<!-- [CUMULATIVE] -->
**Для охват-функций** логика немного отличается: для каждого дня D запрос делается
за период `[global_start_date, D]` (не один день), а из ответа берётся кумулятивный охват.
Дневной прирост (`increment`) вычисляется локально как разница между соседними днями.
<!-- [/CUMULATIVE] -->

---

## 3. Ключевые принципы работы с {API_NAME}

### 3.1. Авторизация

<!-- [OAUTH ONLY] -->
- OAuth 2.0, `grant_type=client_credentials`.
  `POST {TOKEN_PATH}` с `{"client_id": ..., "client_secret": ..., "grant_type": "client_credentials"}`.
- Ответ: `{access_token, expires_in (~{TOKEN_TTL_SEC} сек), token_type: Bearer}`.
- Заголовок запроса: `Authorization: Bearer <token>`.
- Токен обновлять заранее — за 60 сек до истечения (`TOKEN_REFRESH_LEEWAY_SEC = 60`),
  иначе протухнет в середине длинного цикла.
- Учётные данные: переменные окружения `{ENV_VAR_1}` / `{ENV_VAR_2}`.
<!-- [/OAUTH ONLY] -->

<!-- [API KEY ONLY] -->
- Статический API-ключ в заголовке `{API_KEY_HEADER}`.
- Ключ: переменная окружения `{ENV_VAR_1}`.
<!-- [/API KEY ONLY] -->

### 3.2. Базовый URL и используемые эндпоинты

`BASE_URL = {BASE_URL}`

| Метод | Путь | Назначение |
|-------|------|-----------|
| GET | `{ENTITY_LIST_PATH}` | Список всех {ENTITY_NAME_PLURAL} |
<!-- [ASYNC ONLY] -->
| POST | `{SUBMIT_PATH}` | Запрос отчёта статистики (возвращает UUID) |
| GET | `{POLL_PATH_PREFIX}{UUID}` | Статус готовности отчёта |
| GET | `{DOWNLOAD_PATH}?UUID=...` | Скачивание готового отчёта |
<!-- [/ASYNC ONLY] -->
<!-- [SYNC ONLY] -->
| GET | `{SYNC_DATA_PATH}` | Прямое получение статистики |
<!-- [/SYNC ONLY] -->

### 3.3. Схема получения отчётов

<!-- [ASYNC ONLY] -->
Все методы статистики работают по схеме **submit → poll → download**:

1. `POST {SUBMIT_PATH}` → получить `{UUID_FIELD}` задачи.
2. Опрашивать `GET {POLL_PATH_PREFIX}{UUID}` каждые {POLL_INTERVAL_SEC} сек
   (макс. {POLL_MAX_ATTEMPTS} попыток ≈ {POLL_TIMEOUT_MIN} мин).
   Поле статуса: `{STATUS_FIELD}` — значения: `NOT_STARTED / IN_PROGRESS / OK / ERROR`.
3. После `{STATUS_DONE}`: скачать `GET {DOWNLOAD_PATH}?{UUID_PARAM}=...`
   → JSON `{ "{ENTITY_NAME}_id": { "report": { "rows": [...], "totals": {...} } } }`.
<!-- Пример {POLL_TIMEOUT_MIN}: «~5» (40 × 7 сек = 280 сек) -->
<!-- [/ASYNC ONLY] -->

<!-- [SYNC ONLY] -->
Методы статистики работают **синхронно** — данные возвращаются в ответе сразу,
без UUID и polling.
<!-- [/SYNC ONLY] -->

### 3.4. Лимиты API — критичны, несоблюдение приводит к 429 / блокировке

| Лимит | Значение | Как соблюдать |
|-------|----------|---------------|
| {ENTITY_NAME_PLURAL} в одном запросе | ≤ {BATCH_SIZE} | Разбивать список на батчи |
<!-- [ASYNC ONLY] -->
| Параллельных задач генерации | ≤ {MAX_CONCURRENT} | Не submit'ить при {MAX_CONCURRENT} активных UUID |
| Скачиваний отчётов в сутки | ≤ {DAILY_DOWNLOAD_LIMIT} | Учитывать при больших периодах |
<!-- [/ASYNC ONLY] -->
| Запросов в сутки на аккаунт | ≤ {DAILY_REQUEST_LIMIT} | Общий лимит |
| Дней в одном отчёте | ≤ {PERIOD_MAX_DAYS} | Период `dateTo - dateFrom ≤ {PERIOD_MAX_DAYS}` |
<!-- Пример {DAILY_DOWNLOAD_LIMIT}: 1000; {DAILY_REQUEST_LIMIT}: 100000 -->

### 3.5. Обработка ошибок и rate-limit

- **HTTP 429** — повторить с экспоненциальным backoff:
  стартовая пауза {RATE_LIMIT_BASE_SEC} сек, удвоение, до {RATE_LIMIT_RETRY_MAX} повторов.
  Уважать заголовок `Retry-After` если присутствует.
<!-- [ASYNC ONLY] -->
- **Пейсинг submit'ов**: выдерживать ≥ 3 сек между POST-запросами — даже при
  последовательной работе сервер может засчитывать предыдущую задачу активной.
- **Лимит параллельных задач**: если активных UUID уже {MAX_CONCURRENT} —
  ждать освобождения слота через polling статуса перед новым submit.
<!-- [/ASYNC ONLY] -->
- **Ошибки на уровне батча** (HTTP-ошибка / таймаут polling / `{STATUS_ERROR}`) —
  не прерывать общий цикл. Логировать предупреждение и продолжать со следующим батчем.

### 3.6. Подводные камни форматов данных

- **Числа** приходят строками с запятой как разделителем дробной части:
  `"25833,00"` → `25833.0`; `"0,07"` → `0.07`.
  Парсер обязан заменять `","` на `"."` и убирать пробелы.
  <!-- Если API возвращает числа с точкой — замените это описание -->
- **Даты** внутри строк отчёта приходят в формате `DD.MM.YYYY` (например, `"24.04.2026"`).
  В запросах — формат `YYYY-MM-DD`. Необходима функция-конвертер.
  <!-- Если даты уже ISO 8601 — удалите этот пункт -->
- **Вариативные имена полей**: одно и то же поле может называться по-разному
  в разных эндпоинтах. Использовать helper «взять первый существующий ключ из списка»:
  ```
  pick(row, "banner", "bannerId", "objectId", "id")
  ```
- **Envelope списка {ENTITY_NAME_PLURAL}**: ответ `{ENTITY_LIST_PATH}` может быть
  `{"{ENTITY_ENVELOPE_KEY}": [...]}` или `{"{ENTITY_ENVELOPE_KEY_ALT}": [...]}` или сразу массивом.
- **`{ENTITY_NAME}_id` хранить как строку** — в JSON-ключах ответа он строковый.

<!-- [CUMULATIVE] -->
### 3.7. Особый случай — кумулятивная метрика «{CUMULATIVE_METRIC_NAME}»

`{CUMULATIVE_METRIC_NAME}` — количество уникальных {CUMULATIVE_METRIC_SUBJECT} за период.
**Нельзя суммировать по дням.**

Чтобы получить значение за день D: отправить запрос за период
`[global_start_date, D]` с `groupBy=NO_GROUP_BY` и взять `totals.{CUMULATIVE_METRIC_FIELD}`.

Дневной прирост (`increment`) считается локально:
`increment[D] = {CUMULATIVE_METRIC_NAME}[D] − {CUMULATIVE_METRIC_NAME}[D−1]` в рамках одного `{ENTITY_NAME}_id`.

Ограничение: период `[global_start_date, date_to]` ≤ {PERIOD_MAX_DAYS} дней.
<!-- [/CUMULATIVE] -->

---

## 4. Публичные функции

<!-- Повтори блок ниже для каждой функции из 03_ENTITY_FUNCTIONS.md -->

### 4.1. {FUNCTION_1_NAME}()

{FN_1_ONELINER}

HTTP: `GET {ENTITY_LIST_PATH}`

| Поле | Тип | Источник в API (ключ) |
|------|-----|-----------------------|
| `{ENTITY_NAME}_id` | string | `{ENTITY_ID_FIELD}` / `{ENTITY_ID_FIELD_ALT}` |
| `{ENTITY_NAME}_name` | string | `{ENTITY_NAME_FIELD_1}` / `{ENTITY_NAME_FIELD_2}` |
| `state` | string | `state` (`{STATE_RUNNING}` / `{STATE_FINISHED}` / ...) |
| `account_id` | integer | **константа** (значение `1` — пример, задаётся на стороне клиента) |
| `source_type_id` | integer | **константа** (значение `9` — пример, задаётся на стороне клиента) |
| `product_id` | integer | **константа** (значение `1` — пример, задаётся на стороне клиента) |
| `product_name` | string | **константа** (значение `"prod_test"` — пример, задаётся на стороне клиента) |
| `camp_type` | string | **константа** (значение `"camp_test"` — пример, задаётся на стороне клиента) |
| `camp_category` | string | **константа** (значение `"cat_test"` — пример, задаётся на стороне клиента) |
| `id_key_camp` | string | **вычисляется**: `account_id + "_" + {ENTITY_NAME}_id` (пример: `"1_25725956"`) |
| `owner_id` | integer | **константа** (значение `1` — пример, задаётся на стороне клиента) |
<!-- Добавь строки для дополнительных полей справочника -->

> Константные поля (`account_id`, `source_type_id`, `product_id`, `product_name`, `camp_type`, `camp_category`, `owner_id`) и вычисляемое поле `id_key_camp` заполняются фиксированными значениями на стороне клиента — не из API. Конкретные значения приведены как пример и должны быть заменены на актуальные при интеграции.

---

### 4.2. {FUNCTION_2_NAME}(date_from, date_to)

{FN_2_ONELINER}

Гранулярность: одна строка на `{ENTITY_NAME}_id × date`.

<!-- [ASYNC ONLY] -->
HTTP: `POST {SUBMIT_PATH}` с `groupBy={GROUP_BY_DATE}`. Из ответа берётся `report.totals`.
<!-- [/ASYNC ONLY] -->
<!-- [SYNC ONLY] -->
HTTP: `GET {SYNC_DATA_PATH}` с `dateFrom` / `dateTo`. Данные из `{SYNC_RESPONSE_KEY}`.
<!-- [/SYNC ONLY] -->

Строки с нулевыми показателями не включаются в результат.

| Поле | Тип | Описание |
|------|-----|----------|
| `date` | string | YYYY-MM-DD |
| `{ENTITY_NAME}_id` | string | ID {ENTITY_NAME} |
| `{ENTITY_NAME}_name` | string | Название |
| `views` | float | Показы |
| `clicks` | float | Клики |
| `costs_nds` | float | Расход в рублях **с НДС** (как отдаёт API); десятичный тип, **округление до 2 знаков** после запятой |
| `costs_without_nds` | float | **вычисляется**: `costs_nds / (1 + ставка_НДС)`, где ставка зависит от года даты строки (см. примечание ниже) |
| `ak` | float | **константа** (значение `0.5` — агентская комиссия 50%) |
| `costs_nds_ak` | float | **вычисляется**: `costs_nds * (1 + ak)` |
| `costs_without_nds_ak` | float | **вычисляется**: `costs_without_nds * (1 + ak)` |
| `account_id` | integer | **константа** (значение `1` — пример, задаётся на стороне клиента) |
| `source_type_id` | integer | **константа** (значение `9` — пример, задаётся на стороне клиента) |
| `id_key_camp` | string | **вычисляется**: `"1_" + {ENTITY_NAME}_id` |

> **Ставка НДС (зависит от года даты строки):** если год в `date` **≥ 2026 — 22%** (делитель `1.22`),
> если **раньше 2026 — 20%** (делитель `1.20`). Ставка вычисляется для каждой строки отдельно по её
> году, т.к. в одном отчёте могут быть дни разных лет. Расход из API (`costs_nds`) приходит **с НДС**.

> ⚠️ **Формат расходов на входе от источника:** API отдаёт расходы **целочисленным значением**
> (целые рубли, без копеек). Из-за этого возможны **незначительные расхождения со статистикой
> в личном кабинете** — там расходы отображаются с двумя знаками после запятой. Это особенность
> источника, а не ошибка выгрузки. <!-- Проверь формат своего API: если расходы приходят
> с копейками — удали/скорректируй это примечание. -->

---

<!-- Добавь блок для каждой дополнительной функции статистики -->
<!-- Пример (ad-level — добавляет id_key_ad):
### 4.3. {FUNCTION_3_NAME}(date_from, date_to)
Гранулярность: одна строка на объявление/баннер × date.
HTTP: POST {SUBMIT_PATH_2} с groupBy={GROUP_BY_OBJECT}.
| Поле | Тип | Описание |
| ... | ... | ... |
| `id_key_camp` | string | **вычисляется**: `"1_" + {ENTITY_NAME}_id` |
| `id_key_ad` | string | **вычисляется**: `id_key_camp + "_" + ad_id` (пример: `"1_25725956_602761"`) |
-->

<!-- [CUMULATIVE] -->
### 4.{FN_CUMULATIVE_NUM}. {FUNCTION_CUMULATIVE_NAME}(global_start_date, date_from, date_to)

{FN_CUMULATIVE_ONELINER}

Для каждого дня D из `[date_from, date_to]` — отдельный запрос:
`POST {SUBMIT_PATH}` с `dateFrom=global_start_date`, `dateTo=D`, `groupBy=NO_GROUP_BY`.
Значение берётся из `totals.{CUMULATIVE_METRIC_FIELD}`.

Количество запросов: `N_days × N_batches` (где `N_batches = ceil(N_{ENTITY_NAME_PLURAL} / {BATCH_SIZE})`).

| Поле | Тип | Описание |
|------|-----|----------|
| `date` | string | YYYY-MM-DD |
| `{ENTITY_NAME}_id` | string | ID {ENTITY_NAME} |
| `{ENTITY_NAME}_name` | string | Название |
| `{CUMULATIVE_METRIC_NAME}` | float | Значение за период `[global_start_date, date]` |
| `increment` | float | Прирост относительно предыдущей даты; для первой даты = `{CUMULATIVE_METRIC_NAME}` |
| `account_id` | integer | **константа** (значение `1` — пример) |
| `source_type_id` | integer | **константа** (значение `9` — пример) |
| `id_key_camp` | string | **вычисляется**: `"1_" + {ENTITY_NAME}_id` |
<!-- Для ad-level reach-функций добавь: -->
<!-- | `id_key_ad` | string | **вычисляется**: `id_key_camp + "_" + ad_id` (пример: `"1_25725956_602761"`) | -->
<!-- [/CUMULATIVE] -->

---

## 5. Алгоритм сбора статистики (общий шаблон)

```
1. GET {ENTITY_LIST_PATH} → массив {ENTITY_NAME}_id.
2. Сформировать список дат [date_from..date_to].
3. Разбить {ENTITY_NAME_PLURAL} на батчи по {BATCH_SIZE}.
4. Для каждой пары (день, батч):
```
<!-- [ASYNC ONLY] -->
```
     a. Если активных UUID >= {MAX_CONCURRENT} — ждать освобождения слота.
     b. Выдержать паузу >= 3 сек с предыдущего submit.
     c. POST {SUBMIT_PATH} → получить UUID.
     d. Polling каждые {POLL_INTERVAL_SEC} сек до state={STATUS_DONE}
        (макс. {POLL_MAX_ATTEMPTS} попыток).
     e. GET {DOWNLOAD_PATH}?{UUID_PARAM}=... → JSON.
     f. Распарсить rows / totals в плоский массив строк.
     g. При ошибке — лог + пропуск батча, не прерывая цикл.
```
<!-- [/ASYNC ONLY] -->
<!-- [SYNC ONLY] -->
```
     a. GET {SYNC_DATA_PATH}?dateFrom=...&dateTo=... → JSON.
     b. Распарсить ответ в плоский массив строк.
     c. При ошибке — лог + пропуск, не прерывая цикл.
```
<!-- [/SYNC ONLY] -->
```
5. Собрать массив строк, привести к фиксированному набору колонок.
```

---

## 6. Примеры запросов и ответов API

### 6.1. Авторизация
<!-- [OAUTH ONLY] -->
```
POST {BASE_URL}{TOKEN_PATH}
Content-Type: application/json

{
  "client_id":     "<значение {ENV_VAR_1}>",
  "client_secret": "<значение {ENV_VAR_2}>",
  "grant_type":    "client_credentials"
}

Ответ:
{
  "access_token": "eyJhbGc...",
  "expires_in":   {TOKEN_TTL_SEC},
  "token_type":   "Bearer"
}
```
<!-- [/OAUTH ONLY] -->
<!-- [API KEY ONLY] -->
```
Все запросы: заголовок {API_KEY_HEADER}: <значение {ENV_VAR_1}>
```
<!-- [/API KEY ONLY] -->

<!-- [ASYNC ONLY] -->
### 6.2. Запрос отчёта (submit)

```
POST {BASE_URL}{SUBMIT_PATH}
Authorization: Bearer <token>
Content-Type: application/json

{SUBMIT_REQUEST_EXAMPLE}
```
<!-- Вставь реальный JSON-пример тела запроса -->

```
Ответ:
{SUBMIT_RESPONSE_EXAMPLE}
```
<!-- Вставь реальный JSON-пример ответа с UUID -->

### 6.3. Опрос статуса

```
GET {BASE_URL}{POLL_PATH_PREFIX}<UUID>

Ответ (в работе):  { "{STATUS_FIELD}": "IN_PROGRESS", ... }
Ответ (готов):     { "{STATUS_FIELD}": "{STATUS_DONE}", ... }
```

### 6.4. Скачивание отчёта

```
GET {BASE_URL}{DOWNLOAD_PATH}?{UUID_PARAM}=<UUID>

Ответ:
{DOWNLOAD_RESPONSE_EXAMPLE}
```
<!-- Вставь реальный JSON-пример ответа — 1–2 {ENTITY_NAME} с rows/totals -->
<!-- [/ASYNC ONLY] -->

<!-- [SYNC ONLY] -->
### 6.2. Запрос данных

```
GET {BASE_URL}{SYNC_DATA_PATH}?dateFrom=...&dateTo=...
Authorization: ...

Ответ:
{SYNC_RESPONSE_EXAMPLE}
```
<!-- [/SYNC ONLY] -->

---

## 7. Примеры таблиц на выходе

### 7.1. {FUNCTION_1_NAME} — справочник

| {ENTITY_NAME}_id | {ENTITY_NAME}_name | state | account_id | source_type_id | product_id | product_name | camp_type | camp_category | id_key_camp | owner_id |
|------------------|--------------------|-------|-----------|----------------|------------|--------------|-----------|---------------|-------------|----------|
| {DICT_ROW_1} | | | 1 | 9 | 1 | prod_test | camp_test | cat_test | 1_{DICT_ROW_1} | 1 |
| {DICT_ROW_2} | | | 1 | 9 | 1 | prod_test | camp_test | cat_test | 1_{DICT_ROW_2} | 1 |

<!-- Вставь 2–3 реальных строки из своего аккаунта (или обезличенные) -->
> Константные поля заполняются примерными значениями — при интеграции заменить на актуальные.

### 7.2. {FUNCTION_2_NAME} — дневная статистика

| date | {ENTITY_NAME}_id | {ENTITY_NAME}_name | views | clicks | costs_nds | costs_without_nds | ak | costs_nds_ak | costs_without_nds_ak | account_id | source_type_id | id_key_camp |
|------|------------------|--------------------|-------|--------|-----------|-------------------|----|--------------|----------------------|-----------|----------------|-------------|
| {STAT_ROW_1} | | | | | | | 0.5 | | | 1 | 9 | 1_{ENTITY_NAME_ROW_1_ID} |
| {STAT_ROW_2} | | | | | | | 0.5 | | | 1 | 9 | 1_{ENTITY_NAME_ROW_2_ID} |

> Константные поля заполняются примерными значениями — при интеграции заменить на актуальные.

<!-- [CUMULATIVE] -->
### 7.3. {FUNCTION_CUMULATIVE_NAME} — кумулятивная метрика

| date | {ENTITY_NAME}_id | {ENTITY_NAME}_name | {CUMULATIVE_METRIC_NAME} | increment | account_id | source_type_id | id_key_camp |
|------|------------------|--------------------|--------------------------|-----------|-----------|----------------|-------------|
| {REACH_ROW_1} | | | (значение) | (= {CUMULATIVE_METRIC_NAME}, fillna) | 1 | 9 | 1_{ROW_1_ID} |
| {REACH_ROW_2} | | | (значение) | (= {CUMULATIVE_METRIC_NAME}[D] − {CUMULATIVE_METRIC_NAME}[D−1]) | 1 | 9 | 1_{ROW_2_ID} |

> Константные поля заполняются примерными значениями — при интеграции заменить на актуальные.

<!-- Для ad-level кумулятивной функции добавь id_key_ad: -->
<!-- | date | {ENTITY_NAME}_id | ad_id | ad_name | {CUMULATIVE_METRIC_NAME} | increment | account_id | source_type_id | id_key_camp | id_key_ad | -->
<!-- [/CUMULATIVE] -->

<!-- Добавь таблицы для каждой дополнительной функции -->
<!-- Для ad-level stat-функций добавь id_key_ad в таблицу констант: -->
<!--
| {ENTITY_NAME}_id | ad_id | account_id | source_type_id | id_key_camp | id_key_ad |
|------------------|-------|-----------|----------------|-------------|-----------|
| {ID} | {AD_ID} | 1 | 9 | 1_{ID} | 1_{ID}_{AD_ID} |
-->

---

## 8. Рекомендации по реализации на {TARGET_LANG}

<!-- Заполни под конкретный язык. Ниже пример для PHP: -->

- **Версия**: {TARGET_LANG} ≥ {TARGET_LANG_MIN_VERSION}. Composer-проект.
- **HTTP-клиент**: {HTTP_CLIENT_LIB} с retry-middleware для 429.
- **Кэширование токена**: `private $token, $expiresAt` в классе.
  Метод `ensureToken()` перед каждым запросом.
- **`parseNum()`**: `str_replace(',', '.', trim($v))` → `(float)`.
- **`parseDateStr()`**: `DD.MM.YYYY` → `YYYY-MM-DD` (substr / DateTime).
- **`pick()`**: первый не-null ключ из массива вариантов.
- **Прогресс**: вывод в stderr или {PROGRESS_LIB}.
- **Логирование**: PSR-3 / {LOGGING_LIB}. Все skip-предупреждения уровня `warning`.
- **Тайминги** (использовать как константы, не хардкодить в цикле):

| Константа | Значение |
|-----------|---------|
| `POLL_INTERVAL_SEC` | {POLL_INTERVAL_SEC} |
| `POLL_MAX_ATTEMPTS` | {POLL_MAX_ATTEMPTS} |
| `TOKEN_REFRESH_LEEWAY_SEC` | 60 |
| `RATE_LIMIT_BASE_SEC` | {RATE_LIMIT_BASE_SEC} |
| `RATE_LIMIT_RETRY_MAX` | {RATE_LIMIT_RETRY_MAX} |
| `MIN_SUBMIT_INTERVAL_SEC` | 3 |
| `MAX_CONCURRENT` | {MAX_CONCURRENT} |
| `BATCH_SIZE` | {BATCH_SIZE} |

- **Сравнения статусов** — приводить к верхнему регистру: `strtoupper($state)`.
- **Тесты**: моки HTTP-клиента на все публичные функции + тест retry на 429 + тест таймаута polling.

---

## 9. Критерии приёмки

- [ ] Все {FUNCTION_COUNT} публичных функций возвращают данные с теми же колонками
      и в том же порядке, что в Python-эталоне `{MODULE_NAME}.py`.
- [ ] Корректная работа на реальных учётных данных при объёме > {ACCEPTANCE_ENTITY_COUNT} {ENTITY_NAME_PLURAL}
      и периоде > 7 дней без ошибок 429.
<!-- [OAUTH ONLY] -->
- [ ] Токен переподписывается автоматически при многочасовом цикле.
<!-- [/OAUTH ONLY] -->
<!-- [ASYNC ONLY] -->
- [ ] Лимит {MAX_CONCURRENT} параллельных UUID не превышается.
- [ ] Между submit-запросами выдерживается интервал ≥ 3 сек.
<!-- [/ASYNC ONLY] -->
- [ ] Числа парсятся корректно (запятая → точка), даты приводятся к ISO YYYY-MM-DD.
- [ ] При сбое любого батча процесс продолжает работать, ошибка попадает в лог.
<!-- [CUMULATIVE] -->
- [ ] Для первой даты диапазона `increment == {CUMULATIVE_METRIC_NAME}` (не null, fillna значением метрики).
- [ ] Для последующих дат `increment == {CUMULATIVE_METRIC_NAME}[D] − {CUMULATIVE_METRIC_NAME}[D−1]`.
<!-- [/CUMULATIVE] -->
- [ ] README с примерами вызова + `.env.example`.
