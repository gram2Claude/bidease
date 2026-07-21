# Как запросить создание спецификации

## Что должно быть готово перед запросом

- Заполнена анкета `manual_forms/02_NEW_PROJECT_QUESTIONNAIRE.md`
- Заполнен файл `manual_forms/03_ENTITY_FUNCTIONS.md` — функция описана с типом и колонками
- Проект инициализирован (папки `specs/`, `plans/` существуют)

---

## Формула запроса

```
Создай спецификацию для функции [имя функции].
Используй шаблон spec_templates/07_template_spec.md.
Сохрани в specs/[NN]_spec_[имя функции].md
```

Где `[NN]` — порядковый номер (01, 02, ...), `spec` — фиксированное ключевое слово.

---

## Примеры запросов

### Справочник (dict-функция)

```
Создай спецификацию для функции get_campaign_dict.
Это справочник рекламных кампаний — возвращает уникальные кампании с атрибутами.
Используй шаблон spec_templates/07_template_spec.md.
Сохрани в specs/01_spec_get_campaign_dict.md
```

### Статистика по дням

```
Создай спецификацию для функции get_campaign_daily_stat.
Это статистика по кампаниям — метрики по дням (date_from, date_to).
Колонки: date, campaign_id, campaign_name, views, clicks, costs_nds.
Используй шаблон spec_templates/07_template_spec.md.
Сохрани в specs/02_spec_get_campaign_daily_stat.md
```

### Статистика по объявлениям внутри кампании

```
Создай спецификацию для функции get_ads_daily_stat.
Это статистика по объявлениям — метрики по дням с разбивкой по баннерам.
Колонки: date, campaign_id, object_id, object_name, views, clicks, costs_nds.
Используй шаблон spec_templates/07_template_spec.md.
Сохрани в specs/03_spec_get_ads_daily_stat.md
```

### Охват (кумулятивная метрика)

```
Создай спецификацию для функции get_campaign_reach_daily_stat.
Это охват по кампаниям — кумулятивная метрика, параметры: global_start_date, date_from, date_to.
Колонки: date, campaign_id, campaign_name, reach, increment.
Используй шаблон spec_templates/07_template_spec.md.
Сохрани в specs/04_spec_get_campaign_reach_daily_stat.md
```

> **Правило охвата (reach):** нельзя суммировать ни по дням, ни по объявлениям, ни в каком виде.
> Reach = уникальные пользователи, суммирование даёт дубли.
> - Для дня D → отдельный запрос `[global_start_date, D]` с `groupBy=NO_GROUP_BY`
> - Campaign-level reach → строка **«Всего»** в CSV (API дедуплицировал пользователей)
> - `increment` = `reach[D] - reach[D-1]` (вычисляется локально через `diff()`)

---

## Что Claude сделает автоматически

- Прочитает документацию API из A3 анкеты
- Определит эндпоинт, паттерн (async/sync), структуру ответа
- Заполнит таблицу ограничений API
- Опишет edge cases и acceptance criteria
- Задаст open questions если что-то неясно из документации
- **Добавит обязательное обогащение DataFrame** (константы `account_id`, `source_type_id`,
  справочные `product_id`/`product_name`/`camp_type`/`camp_category`/`owner_id`,
  вычисляемые `costs_without_nds`/`ak`/`costs_nds_ak`/`costs_without_nds_ak`,
  составные ключи `id_key_camp` и для ad-level — `id_key_ad`) согласно соглашению
  проекта — см. раздел «Обязательное обогащение DataFrame» в шаблоне spec

---

## После получения спецификации

1. Прочитай и проверь содержимое
2. Внеси правки если что-то неточно
3. Напиши «Спецификация утверждена» — только после этого переходи к плану
