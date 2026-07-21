# Анкета нового API-проекта

Заполни вручную только секцию A (~2 минуты). Всё остальное Claude определяет
автоматически из документации API по ссылке A3.

**Как заполнять:** в каждом пункте под строкой `Пример:` есть строка `Ответ:`.
Замени `<впиши сюда>` своим значением. Строку `Пример:` не трогай —
она остаётся как подсказка.

---

## A. Идентификация проекта

```
A1. Название API (человекочитаемое):
    Пример:  Ozon Performance, Google Ads, VK Рекламы
    Ответ:   Bidease Reporting
    → Плейсхолдер: {API_NAME}

A2. Имя репозитория/папки проекта (snake_case, без пробелов):
    Пример:  ozon_performance, google_ads, vk_ads
    Ответ:   bidease
    → Плейсхолдер: {MODULE_NAME}

A3. URL документации API:
    Пример:  https://docs.ozon.ru/api/performance/
    Ответ:   https://support.bidease.com/support/solutions/articles/72000586529-bidease-reporting-api-documentation
    → Плейсхолдер: {DOCS_URL}
```

> Git-репозиторий проекта: https://github.com/gram2Claude/bidease.git

---

## E. Сущности данных и публичные функции

→ Заполняется в отдельном файле **`03_ENTITY_FUNCTIONS.md`** после завершения этой анкеты.

---
