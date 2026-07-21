# Структура проекта — {API_NAME}

Запусти этот файл в начале нового проекта. Claude создаст необходимые папки и файлы.

---

## Команда для инициализации

Скажи Claude: **«Инициализируй структуру проекта»** — и он создаст всё описанное ниже.

**Важно:** Claude создаёт папку `{MODULE_NAME}/` **внутри текущей рабочей директории** и кладёт
все файлы проекта в неё. Шаблоны (`test/`) остаются на уровне репозитория и не смешиваются
с файлами проекта.

Итоговая структура репозитория:
```
repo_root/
├── test/                  ← шаблоны (не трогать)
├── manual_forms/          ← заполненные анкеты (входные данные для Claude)
├── auto_generated/        ← скаффолд, сгенерированный Claude на Шаге 3
├── CLAUDE.md              ← инструкции для Claude Code
├── info/                  ← сводка методов API, реестр реализованных функций
├── specs/                 ← спецификации функций
├── plans/                 ← планы реализации функций
└── {MODULE_NAME}/         ← исполняемый код проекта
    ├── {MODULE_NAME}.py
    ├── {MODULE_NAME}_demo.ipynb
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── .env
    ├── .env.example
    ├── .gitignore
    ├── tests/
    ├── smoke_tests/
    └── raw_data/
```

В `{MODULE_NAME}/` — только исполняемый код и данные (библиотека, тесты, raw_data, env).
Документация и артефакты процесса (`CLAUDE.md`, `info/`, `specs/`, `plans/`,
`manual_forms/`, `auto_generated/`) живут на уровне репозитория.

---

## Структура папок

На уровне репозитория (не внутри `{MODULE_NAME}/`):

```
CLAUDE.md                     # инструкции для Claude Code (генерируется на Шаге 3)
│
├── info/                     # справочные материалы по API и проекту
│   ├── 00_api_methods.md     # сводка методов API (заполняет Claude на Шаге 1.5)
│   └── 01_functions_implemented.md  # реестр реализованных функций (обновляется на Шаге 4)
│
├── specs/                    # спецификации функций
│   └── .gitkeep
│
└── plans/                    # планы реализации функций
    └── .gitkeep
```

Внутри `{MODULE_NAME}/` — только исполняемый код:

```
{MODULE_NAME}/
│
├── {MODULE_NAME}.py          # основная библиотека-клиент
├── {MODULE_NAME}_demo.ipynb  # демо-ноутбук
├── requirements.txt          # зависимости
├── requirements-dev.txt      # dev-зависимости (pytest, ruff)
├── .env                      # учётные данные (не коммитить)
├── .env.example              # шаблон учётных данных
├── .gitignore
│
├── tests/                    # pytest unit-тесты с моками
│   ├── conftest.py           # фикстуры pytest (моки клиента, тестовые данные)
│   └── test_{MODULE_NAME}.py
│
├── smoke_tests/              # smoke-тесты на реальном API (требуют .env)
│   └── test_{FUNCTION_NAME}.py  # один файл на функцию
│
└── raw_data/                 # CSV-результаты успешных вызовов всех публичных функций (в .gitignore);
    │                         #   только последняя выгрузка каждой функции — старые периоды smoke-тест удаляет
    ├── raw_files/            # сырые CSV до парсинга (кэш; raw_{date_from}_{date_to}_{campaign_id}_{day}.csv)
    └── .gitkeep
```

---

## Файлы для создания при инициализации

### `requirements.txt`
```
requests>=2.31.0
pandas>=2.0.0
python-dotenv>=1.0.0
tqdm>=4.66.0
```

### `.env.example`

**ВАЖНО:** имена переменных credentials — **без префикса модуля/API**:
`CLIENT_ID` / `CLIENT_SECRET` для OAuth, `API_KEY` для статического ключа.
НЕ использовать `OZON_CLIENT_ID`, `{MODULE_NAME}_CLIENT_ID`, `WB_API_KEY` и т.п.
Каждый проект живёт в отдельном репозитории с собственным `.env` —
дополнительный префикс избыточен и расходится с этим шаблоном.

```
CLIENT_ID=...
CLIENT_SECRET=...

# Даты для smoke-тестов
TEST_START_DATE=YYYY-MM-DD
TEST_END_DATE=YYYY-MM-DD
TEST_GLOBAL_START_DATE=YYYY-MM-DD
```

### `.env`
Создаётся автоматически (копия `.env.example`). Пользователь заполняет только `CLIENT_ID` и `CLIENT_SECRET` (без префикса модуля — см. предупреждение выше).
```
CLIENT_ID=...
CLIENT_SECRET=...

# Даты для smoke-тестов
TEST_START_DATE=YYYY-MM-DD
TEST_END_DATE=YYYY-MM-DD
TEST_GLOBAL_START_DATE=YYYY-MM-DD
```

### `requirements-dev.txt`
```
pytest>=8.0.0
pytest-mock>=3.12.0
ruff>=0.4.0
```

### `.gitignore`
```
.env
__pycache__/
*.pyc
.ipynb_checkpoints/
raw_data/
```

---

## Соглашения

| Тип файла | Папка | Пример имени |
|-----------|-------|-------------|
| Инструкции для Claude | корень репо | `CLAUDE.md` |
| Сводка методов API | `info/` (корень репо) | `00_api_methods.md` |
| Реестр реализованных функций | `info/` (корень репо) | `01_functions_implemented.md` |
| Спецификация функции | `specs/` (корень репо) | `01_spec_get_campaign_dict.md` |
| План реализации | `plans/` (корень репо) | `01_plan_get_campaign_dict.md` |
| Основная библиотека | `{MODULE_NAME}/` | `{MODULE_NAME}.py` |
| Демо-ноутбук | `{MODULE_NAME}/` | `{MODULE_NAME}_demo.ipynb` |
| Unit-тесты | `{MODULE_NAME}/tests/` | `test_{MODULE_NAME}.py` |
| Smoke-тесты | `{MODULE_NAME}/smoke_tests/` | `test_get_campaign_dict.py` |
| CSV-результаты | `{MODULE_NAME}/raw_data/` | `get_campaign_dict.csv`, `get_campaigns_daily_stat_2026-04-24_2026-04-25.csv` |
