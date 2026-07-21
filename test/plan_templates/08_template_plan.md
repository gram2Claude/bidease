# Plan: {SPEC_FUNCTION_NAME}

<!-- 
Имя файла: plans/{NN}_plan_{SPEC_FUNCTION_NAME}.md
где {NN} — тот же порядковый номер, что и в соответствующей спецификации specs/{NN}_spec_...
      "plan" — фиксированное ключевое слово (показывает, что это план)
Пример: plans/01_plan_get_campaign_dict.md
        plans/02_plan_get_campaign_daily_stat.md
        plans/03_plan_get_campaign_reach_daily_stat.md
-->

## Контекст

На основании спецификации `specs/{NN}_spec_{SPEC_FUNCTION_NAME}.md`.

## Изменения в `{MODULE_NAME}.py`

### 1. Новые константы
- `{SPEC_COLUMNS_CONST}` = [список колонок, **включая** константные и вычисляемые поля,
  см. spec → раздел «Обязательное обогащение DataFrame»]
  - для справочника: `[..., "account_id", "source_type_id", "product_id", "product_name", "camp_type", "camp_category", "id_key_camp", "owner_id"]`
  - для статистики (campaign-level): `[..., "costs_without_nds", "ak", "costs_nds_ak", "costs_without_nds_ak", "account_id", "source_type_id", "id_key_camp"]`
  - для статистики (ad-level): добавить `"id_key_ad"` в конец списка
  - для охвата (campaign-level): `[..., "account_id", "source_type_id", "id_key_camp"]`
  - для охвата (ad-level): добавить `"id_key_ad"` в конец списка

### 2. Новые приватные методы
- `_fetch_{SPEC_ENTITY}_for_{SPEC_SCOPE}(...)` — описание

### 3. Новая публичная функция
- `{SPEC_FUNCTION_NAME}(...)` — описание
- **[ASYNC]** Добавить параметр `raw_cache_dir: str | Path | None = None` —
  сохраняет каждый распакованный CSV-отчёт в `raw_data/raw_files/raw_{date_from}_{date_to}_{campaign_id}_{day}.csv`.
  При повторном запуске (например, после фикса парсера) данные берутся из кэша — API не вызывается.
  При запросе других дат `_evict_stale_raw_cache()` удаляет `raw_*.csv` с несоответствующим префиксом.
  Функции с одинаковым endpoint и теми же датами разделяют кэш автоматически.

### 4. Изменения в существующем коде
- (если есть — перечислить; если нет — «нет»)

## Порядок реализации

> **После создания плана — ждать явного утверждения пользователя. Не начинать реализацию автоматически.**

1. Добавить константу `{SPEC_COLUMNS_CONST}`
2. Реализовать приватный метод `_fetch_{SPEC_ENTITY}_for_{SPEC_SCOPE}()`
3. Реализовать публичную функцию `{SPEC_FUNCTION_NAME}()`:
   - Парсинг API-данных → промежуточный `df`
   - **Перед** `df.reindex(columns={SPEC_COLUMNS_CONST})` — обогатить df:
     - Для функций с расходами — сначала тип `costs_nds`: десятичный, 2 знака после запятой
       (`df["costs_nds"] = pd.to_numeric(df["costs_nds"], errors="coerce").astype(float).round(2)`),
       затем производные: `df["costs_without_nds"] = df["costs_nds"] / _vat_divisor(df["date"])`
       — ставка НДС по году даты строки (year ≥ 2026 → 1.22 / 22%, иначе → 1.20 / 20%);
       `df["ak"] = 0.5`; `df["costs_nds_ak"] = df["costs_nds"] * 1.5`;
       `df["costs_without_nds_ak"] = df["costs_without_nds"] * 1.5`
     - Константы: `df["account_id"] = 1`, `df["source_type_id"] = 9` (для всех функций)
     - Для справочников: добавить `product_id=1`, `product_name="prod_test"`,
       `camp_type="camp_test"`, `camp_category="cat_test"`, `owner_id=1`
     - Ключи: `df["id_key_camp"] = "1_" + df["campaign_id"].astype(str)`
     - Для ad-level: `df["id_key_ad"] = df["id_key_camp"] + "_" + df["ad_id"].astype(str)`
4. Обновить docstring модуля
5. Запустить smoke-тест самостоятельно (не ждать команды пользователя):
   - Smoke-тест сохраняет DataFrame в `{MODULE_NAME}/raw_data/<имя_функции>[_{date_from}_{date_to}].csv`
   - **Перед сохранением** smoke-тест удаляет старые `<имя_функции>_*.csv` этой же функции:
     имя содержит период, поэтому выгрузки за прежние даты сами не перезаписываются и копятся.
     Очистка — **после** успешного вызова API (упавший прогон не стирает прежнюю выгрузку):
     ```python
     for old in out_dir.glob("<имя_функции>_*.csv"):
         old.unlink()
     ```
   - Показать результат **из сохранённого CSV** (не из памяти): shape, columns, head(5).to_markdown(index=False)
   - **[ОХВАТ]** параметр `global_start_date` брать из `TEST_GLOBAL_START_DATE`, НЕ из `TEST_START_DATE`

## Проверка

- [ ] Функция возвращает DataFrame с колонками `{SPEC_COLUMNS_CONST}`
- [ ] При пустом ответе API возвращается пустой DataFrame с правильными колонками
- [ ] Существующие функции работают без изменений
