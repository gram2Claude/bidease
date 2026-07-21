# Сущности и функции — Bidease Reporting

Заполняется после основной анкеты (`02_NEW_PROJECT_QUESTIONNAIRE.md`).
Один файл на проект. Скопируй блок функции нужное количество раз.

**Как заполнять:** в каждом пункте под строкой `Пример:` есть строка `Ответ:`.
Замени `<впиши сюда>` своим значением. Строку `Пример:` не трогай —
она остаётся как подсказка. В пункте `Fn2. Тип` поставь `[x]` напротив одного
варианта (только один тип на функцию).

**Важно про Fn5 (колонки):** перечисляй только поля, которые приходят **из API**
(например: `date, campaign_id, ad_id, ad_name, views, clicks, costs_nds`).
Стандартные константные и вычисляемые поля (`account_id`, `source_type_id`,
`id_key_camp`, `id_key_ad`, `costs_without_nds`, `ak`, `costs_nds_ak`,
`costs_without_nds_ak`, плюс справочные `product_id`, `product_name`,
`camp_type`, `camp_category`, `owner_id`) Claude **добавляет автоматически**
по соглашению проекта — их в Fn5 указывать не нужно. См. шаблон
`test/spec_templates/07_template_spec.md` → раздел «Обязательное обогащение DataFrame».

> **Примечание по API (см. `info/00_api_methods.md`):**
> Bidease Reporting — один синхронный GET-эндпоинт `/api/reporting/v1/stats`, ответ CSV.
> Справочников-эндпоинтов нет — «справочник кампаний» собирается тем же эндпоинтом с
> группировками по атрибутам кампании за длинный период (до 1 года — максимум API).
> Статистика группируется на сервере (`group=Day&group=CampaignID…`) — **один запрос на
> весь период на функцию**, без перебора сущностей (в отличие от avito). Уровня «группы
> объявлений» в Bidease нет — иерархия: кампания → креатив. Охватных метрик (reach)
> нет → функций типа «Охват» нет. `todate` эксклюзивна — функции принимают обе даты
> включительно, библиотека сама передаёт `todate = date_to + 1 день`.
> Расчётные метрики API (`ctr`, `ecpm`, `ecpc`, `i2c`, `cpi`) не выгружаются (конвенция
> проекта); `conversions`/`revenue`/`iap*`/`goal1–6` исключены решением проекта 2026-07-21
> (только базовые: показы/клики/расход). ⚠️ `spend` приходит **в долларах** — применимость
> НДС-производных (`costs_without_nds`) уточняется на этапе спеки функции статистики.

---

## Функции

### Функция 1

```
Fn1. Имя функции (snake_case):
     Пример:  get_campaign_dict, get_campaign_daily_stat
     Ответ:   get_campaign_dict
     → Плейсхолдер: {FUNCTION_1_NAME}

Fn2. Тип (поставь [x] напротив одного варианта):
     [x] Справочник  — уникальные сущности с атрибутами, без дат
     [ ] Статистика  — метрики по дням, date_from / date_to
     [ ] Охват       — кумулятивная метрика, global_start_date + date_from / date_to

Fn4. Описание одной строкой:
     Пример:  Дневная статистика по рекламным кампаниям
     Ответ:   Справочник кампаний из группировок отчёта (GET /stats, group=CampaignID+CampaignName+AdvertiserID+ProductID, период — последний год)
     → Плейсхолдер: {FN_1_ONELINER}

Fn5. Колонки выходного DataFrame (перечисли имена через запятую):
     Пример:  date, campaign_id, campaign_name, views, clicks, costs_nds
     Ответ:   campaign_id, campaign_name, advertiser_id, product_id
     Правило: все имена колонок — snake_case.
     Типы данных определяются автоматически из ответа API.
     → Плейсхолдер: {DF_1_COLUMNS}
     Маппинг на API: campaign_id←CampaignID, campaign_name←CampaignName,
       advertiser_id←AdvertiserID, product_id←ProductID (колонки группировок CSV).
       Метрики из ответа отбрасываются — строки дедуплицируются по campaign_id.
       ⚠️ product_id здесь — РЕАЛЬНЫЙ ID продукта Bidease (не константа-пример,
       как в avito) — отступление от конвенции фиксируется в спеке.
```

---

### Функция 2

```
Fn1. Имя функции (snake_case):
     Пример:  get_campaign_dict, get_campaign_daily_stat
     Ответ:   get_campaigns_daily_stat
     → Плейсхолдер: {FUNCTION_2_NAME}

Fn2. Тип (поставь [x] напротив одного варианта):
     [ ] Справочник  — уникальные сущности с атрибутами, без дат
     [x] Статистика  — метрики по дням, date_from / date_to
     [ ] Охват       — кумулятивная метрика, global_start_date + date_from / date_to

Fn4. Описание одной строкой:
     Пример:  Дневная статистика по рекламным кампаниям
     Ответ:   Дневная статистика по кампаниям (GET /stats, group=Day+CampaignID)
     → Плейсхолдер: {FN_2_ONELINER}

Fn5. Колонки выходного DataFrame (перечисли имена через запятую):
     Пример:  date, campaign_id, campaign_name, views, clicks, costs_nds
     Ответ:   date, campaign_id, impressions, clicks, spend
     Правило: все имена колонок — snake_case.
     Типы данных определяются автоматически из ответа API.
     → Плейсхолдер: {DF_2_COLUMNS}
     Маппинг на API: date←Day, campaign_id←CampaignID; метрики impressions, clicks —
       1:1; costs_nds←spend (⚠️ доллары). Названий в статистике нет (конвенция) —
       campaign_name джойнить из get_campaign_dict. Один запрос на весь период
       (todate = date_to + 1 день из-за эксклюзивности).
```

---

### Функция 3

```
Fn1. Имя функции (snake_case):
     Пример:  get_campaign_dict, get_campaign_daily_stat
     Ответ:   get_creatives_daily_stat
     → Плейсхолдер: {FUNCTION_3_NAME}

Fn2. Тип (поставь [x] напротив одного варианта):
     [ ] Справочник  — уникальные сущности с атрибутами, без дат
     [x] Статистика  — метрики по дням, date_from / date_to
     [ ] Охват       — кумулятивная метрика, global_start_date + date_from / date_to

Fn4. Описание одной строкой:
     Пример:  Дневная статистика по рекламным кампаниям
     Ответ:   Дневная статистика по креативам (GET /stats, group=Day+CampaignID+CreativeID)
     → Плейсхолдер: {FN_3_ONELINER}

Fn5. Колонки выходного DataFrame (перечисли имена через запятую):
     Пример:  date, campaign_id, campaign_name, views, clicks, costs_nds
     Ответ:   date, campaign_id, creative_id, impressions, clicks, spend
     Правило: все имена колонок — snake_case.
     Типы данных определяются автоматически из ответа API.
     → Плейсхолдер: {DF_3_COLUMNS}
     Маппинг на API: date←Day, campaign_id←CampaignID, creative_id←CreativeID;
       метрики как в функции 2. Уровня групп в Bidease нет → формула id_key_ad
       без group-звена (уточняется в спеке: id_key_camp + "_" + creative_id).
```

---

### Функция 4

```
Fn1. Имя функции (snake_case):
     Пример:  get_campaign_dict, get_campaign_daily_stat
     Ответ:   get_admin_audit
     → Плейсхолдер: {FUNCTION_4_NAME}

Fn2. Тип (поставь [x] напротив одного варианта):
     [ ] Справочник  — уникальные сущности с атрибутами, без дат
     [x] Статистика  — метрики по дням, date_from / date_to
         (агрегатная таблица admin_audit поверх get_campaigns_daily_stat,
          собственного эндпоинта API нет)
     [ ] Охват       — кумулятивная метрика, global_start_date + date_from / date_to

Fn4. Описание одной строкой:
     Пример:  Дневная статистика по рекламным кампаниям
     Ответ:   Сводный аудит по дням (admin_audit): суммы impressions/clicks/costs_nds/costs_without_nds
     → Плейсхолдер: {FN_4_ONELINER}

Fn5. Колонки выходного DataFrame (перечисли имена через запятую):
     Пример:  date, campaign_id, campaign_name, views, clicks, costs_nds
     Ответ:   date, account_id, source_type_id, owner_id, impressions, clicks, costs_nds, costs_without_nds, chef_flag
     Правило: все имена колонок — snake_case.
     → Плейсхолдер: {DF_4_COLUMNS}
     Маппинг: собственного API-вызова нет — группировка результата get_campaigns_daily_stat
       по date × account_id × source_type_id × owner_id с суммированием
       impressions/clicks/costs_nds/costs_without_nds; owner_id — из справочника
       кампаний (join по campaign_id); chef_flag — константа 1 (дефолт).
```
