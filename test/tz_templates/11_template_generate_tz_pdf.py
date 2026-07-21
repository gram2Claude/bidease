"""Генератор PDF из заполненного шаблона ТЗ.

Использование:
    python 11_template_generate_tz_pdf.py

Перед запуском:
    pip install fpdf2

Инструкция по заполнению:
    Замени все строки вида REPLACE_* на реальный контент.
    Каждая константа соответствует разделу или таблице итогового PDF.
    Не меняй структуру функций H1/H2/P/BUL/CODE/TABLE — только контент.
"""

# ── [ПРОВЕРЬ ПЕРЕД ЗАПУСКОМ] ──────────────────────────────────────────────────
# Все REPLACE_* должны быть заменены на реальный текст.
# ─────────────────────────────────────────────────────────────────────────────

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

# ── Пути к шрифтам ─────────────────────────────────────────────────────────────
# Windows: arial.ttf обычно в C:/Windows/Fonts/
# Linux/Mac: замени на DejaVuSans.ttf или другой TTF с кириллицей
FONT_REG  = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_ITAL = r"C:\Windows\Fonts\ariali.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"   # Consolas; замени при отсутствии

NX = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

# ── Метаданные (заполни) ───────────────────────────────────────────────────────

API_NAME    = "REPLACE_API_NAME"          # Пример: "Ozon Performance"
TARGET_LANG = "REPLACE_TARGET_LANG"       # Пример: "PHP"
MODULE_NAME = "REPLACE_MODULE_NAME"       # Пример: "ozon_performance"
OUT_FILE    = f"TZ_{MODULE_NAME}_{TARGET_LANG}.pdf"


# ── PDF-хелперы ────────────────────────────────────────────────────────────────

class PDF(FPDF):
    def header(self): pass
    def footer(self):
        self.set_y(-12)
        self.set_font("arial", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Стр. {self.page_no()}", align="C")


def make_pdf() -> PDF:
    p = PDF(unit="mm", format="A4")
    p.set_margins(left=15, top=15, right=15)
    p.set_auto_page_break(auto=True, margin=15)
    p.add_font("arial", "",  FONT_REG)
    p.add_font("arial", "B", FONT_BOLD)
    p.add_font("arial", "I", FONT_ITAL)
    p.add_font("mono",  "",  FONT_MONO)
    p.add_page()
    return p


pdf = make_pdf()


def H1(text: str) -> None:
    pdf.set_font("arial", "B", 16)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(2)
    pdf.multi_cell(0, 8, text, **NX)
    pdf.ln(1)


def H2(text: str) -> None:
    pdf.set_font("arial", "B", 13)
    pdf.set_text_color(30, 30, 90)
    pdf.ln(2)
    pdf.multi_cell(0, 7, text, **NX)
    pdf.ln(1)


def P(text: str) -> None:
    pdf.set_font("arial", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5, text, **NX)
    pdf.ln(0.5)


def BUL(items: list[str]) -> None:
    pdf.set_font("arial", "", 10)
    pdf.set_text_color(30, 30, 30)
    for it in items:
        pdf.cell(5)
        pdf.cell(3, 5, "•")
        pdf.multi_cell(0, 5, it, **NX)
    pdf.ln(0.5)


def CODE(text: str) -> None:
    pdf.set_font("mono", "", 8.5)
    pdf.set_text_color(20, 20, 20)
    pdf.set_fill_color(245, 245, 245)
    pdf.multi_cell(0, 4.2, text, fill=True, border=0, **NX)
    pdf.ln(0.5)


def TABLE(headers: list[str], rows: list[list[str]], widths: list[int]) -> None:
    pdf.set_font("arial", "B", 9)
    pdf.set_fill_color(220, 225, 240)
    pdf.set_text_color(20, 20, 20)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, h, border=1, fill=True)
    pdf.ln()
    pdf.set_font("arial", "", 9)
    fill = False
    for row in rows:
        max_lines = 1
        for val, w in zip(row, widths):
            lines = pdf.multi_cell(w, 4.5, val, dry_run=True, output="LINES")
            max_lines = max(max_lines, len(lines))
        h = 4.5 * max_lines
        if pdf.get_y() + h > pdf.h - 15:
            pdf.add_page()
        for val, w in zip(row, widths):
            x, y = pdf.get_x(), pdf.get_y()
            pdf.multi_cell(w, 4.5, val, border=1, fill=fill, max_line_height=4.5)
            pdf.set_xy(x + w, y)
        pdf.ln(h)
        fill = not fill
    pdf.ln(1)


# ══════════════════════════════════════════════════════════════════════════════
# СОДЕРЖИМОЕ ДОКУМЕНТА
# Замени все строки REPLACE_* на реальный текст.
# Структуру (порядок вызовов H1/H2/P/BUL/CODE/TABLE) менять не обязательно —
# добавляй/удаляй разделы под конкретный проект.
# ══════════════════════════════════════════════════════════════════════════════

# ── Титул ─────────────────────────────────────────────────────────────────────
pdf.set_font("arial", "B", 20)
pdf.set_text_color(20, 30, 90)
pdf.multi_cell(0, 10, "Техническое задание", **NX)
pdf.set_font("arial", "B", 14)
pdf.set_text_color(60, 60, 60)
pdf.multi_cell(0, 8, f"Реализация клиента {API_NAME} на {TARGET_LANG}", **NX)
pdf.ln(2)
pdf.set_font("arial", "I", 10)
pdf.set_text_color(100, 100, 100)
pdf.multi_cell(
    0, 5,
    f"Эталонная Python-реализация: {MODULE_NAME}.py. "
    f"Цель — портировать функциональность на {TARGET_LANG} с сохранением структуры выходных данных.",
    **NX,
)
pdf.ln(3)

# ── 1. Цель ───────────────────────────────────────────────────────────────────
H1("1. Цель проекта")
P("REPLACE_PROJECT_GOAL")
# Пример: "Разработать PHP-библиотеку для работы с Ozon Performance API, которая загружает
# справочник рекламных кампаний и собирает дневную статистику (показы, клики, расход, охват).
# Выход каждой публичной функции — структурированный массив строк."

# ── 2. Общая логика ───────────────────────────────────────────────────────────
H1("2. Общая логика работы библиотеки")
P("REPLACE_GENERAL_LOGIC_INTRO")
# Пример: "Все функции статистики работают по одной схеме."
BUL([
    "REPLACE_STEP_1",   # Получить справочник сущностей
    "REPLACE_STEP_2",   # Сформировать список дат
    "REPLACE_STEP_3",   # Разбить на батчи
    "REPLACE_STEP_4",   # Запросить статистику (submit)
    "REPLACE_STEP_5",   # Polling готовности
    "REPLACE_STEP_6",   # Скачать и распаковать
    "REPLACE_STEP_7",   # Распарсить ответ
    "REPLACE_STEP_8",   # Собрать результат
])
# Если есть кумулятивные метрики — добавь P() с описанием охват-функций:
# P("REPLACE_CUMULATIVE_LOGIC_NOTE")

# ── 3. Принципы работы с API ──────────────────────────────────────────────────
H1(f"3. Ключевые принципы работы с {API_NAME}")

H2("3.1. Авторизация")
BUL([
    "REPLACE_AUTH_POINT_1",   # Тип авторизации, endpoint, тело запроса
    "REPLACE_AUTH_POINT_2",   # Ответ: поля access_token, expires_in
    "REPLACE_AUTH_POINT_3",   # Заголовок запроса
    "REPLACE_AUTH_POINT_4",   # Логика обновления токена
    "REPLACE_AUTH_POINT_5",   # Переменные окружения
])

H2("3.2. Базовый URL и эндпоинты")
P("REPLACE_BASE_URL_NOTE")
BUL([
    "REPLACE_ENDPOINT_1",
    "REPLACE_ENDPOINT_2",
    "REPLACE_ENDPOINT_3",
    # Добавь/убери строки под количество эндпоинтов
])

H2("3.3. Асинхронная схема получения отчётов")
# Удали этот раздел если API синхронный
P("REPLACE_ASYNC_SCHEME_INTRO")
BUL([
    "REPLACE_ASYNC_STEP_1",   # submit → UUID
    "REPLACE_ASYNC_STEP_2",   # polling: интервал, макс. попытки, статусы
    "REPLACE_ASYNC_STEP_3",   # download → структура ответа
])

H2("3.4. Лимиты API (критичны)")
TABLE(
    ["Лимит", "Значение", "Где применять"],
    [
        ["REPLACE_LIMIT_NAME_1", "REPLACE_LIMIT_VAL_1", "REPLACE_LIMIT_IMPL_1"],
        ["REPLACE_LIMIT_NAME_2", "REPLACE_LIMIT_VAL_2", "REPLACE_LIMIT_IMPL_2"],
        ["REPLACE_LIMIT_NAME_3", "REPLACE_LIMIT_VAL_3", "REPLACE_LIMIT_IMPL_3"],
        ["REPLACE_LIMIT_NAME_4", "REPLACE_LIMIT_VAL_4", "REPLACE_LIMIT_IMPL_4"],
        ["REPLACE_LIMIT_NAME_5", "REPLACE_LIMIT_VAL_5", "REPLACE_LIMIT_IMPL_5"],
    ],
    [55, 35, 90],
)

H2("3.5. Обработка ошибок и rate-limit")
BUL([
    "REPLACE_ERROR_HANDLING_1",  # 429 backoff
    "REPLACE_ERROR_HANDLING_2",  # пейсинг между submit'ами
    "REPLACE_ERROR_HANDLING_3",  # лимит параллельных UUID
    "REPLACE_ERROR_HANDLING_4",  # ERROR статус
    "REPLACE_ERROR_HANDLING_5",  # пропуск батча, не прерывать цикл
])

H2("3.6. Подводные камни форматов данных")
BUL([
    "REPLACE_FORMAT_GOTCHA_1",   # числа как строки с запятой
    "REPLACE_FORMAT_GOTCHA_2",   # формат дат
    "REPLACE_FORMAT_GOTCHA_3",   # вариативные имена полей
    "REPLACE_FORMAT_GOTCHA_4",   # envelope ответа списка сущностей
    "REPLACE_FORMAT_GOTCHA_5",   # ID как строка
])

# Раздел 2.7 — только для кумулятивных метрик (reach).
# Удали H2 + P + P ниже если кумулятивных метрик нет.
H2("3.7. Особый случай — кумулятивная метрика «REPLACE_CUMULATIVE_METRIC»")
P("REPLACE_CUMULATIVE_METRIC_EXPLANATION")
P("REPLACE_CUMULATIVE_INCREMENT_FORMULA")

# ── 4. Публичные функции ──────────────────────────────────────────────────────
H1("4. Публичные функции")

# Повтори блок H2+P+TABLE для каждой функции
H2("4.1. REPLACE_FUNCTION_1_SIGNATURE")
P("REPLACE_FN1_DESCRIPTION")
P("HTTP: REPLACE_FN1_HTTP")
P("Колонки результата:")
TABLE(
    ["Поле", "Тип", "Источник (ключ API)"],
    [
        ["REPLACE_COL_1", "REPLACE_TYPE_1", "REPLACE_SOURCE_1"],
        ["REPLACE_COL_2", "REPLACE_TYPE_2", "REPLACE_SOURCE_2"],
        ["REPLACE_COL_3", "REPLACE_TYPE_3", "REPLACE_SOURCE_3"],
        # Добавь/убери строки
    ],
    [40, 25, 115],
)

H2("4.2. REPLACE_FUNCTION_2_SIGNATURE")
P("REPLACE_FN2_DESCRIPTION")
P("HTTP: REPLACE_FN2_HTTP")
P("Колонки: REPLACE_FN2_COLUMNS")

# Добавь H2+P+TABLE для каждой дополнительной функции:
# H2("4.3. ...")
# ...

# ── 5. Алгоритм ───────────────────────────────────────────────────────────────
H1("5. Алгоритм сбора статистики (общий шаблон)")
CODE("""REPLACE_ALGORITHM_PSEUDOCODE""")
# Вставь псевдокод из раздела 4 заполненного 10_template_tz.md

# ── 6. Примеры запросов и ответов API ─────────────────────────────────────────
H1("6. Примеры запросов и ответов API")

H2("6.1. Авторизация")
CODE("""REPLACE_AUTH_REQUEST_EXAMPLE""")

H2("6.2. Запрос отчёта (submit)")
CODE("""REPLACE_SUBMIT_REQUEST_EXAMPLE""")

H2("6.3. Опрос статуса")
CODE("""REPLACE_POLL_EXAMPLE""")

H2("6.4. Скачивание отчёта")
CODE("""REPLACE_DOWNLOAD_EXAMPLE""")

# Удали 5.2–5.4 и добавь один блок если API синхронный:
# H2("6.2. Запрос данных")
# CODE("""...""")

# ── 7. Примеры таблиц ─────────────────────────────────────────────────────────
H1("7. Примеры таблиц на выходе")

H2("7.1. REPLACE_FUNCTION_1_NAME — справочник")
TABLE(
    ["REPLACE_DICT_COL_1", "REPLACE_DICT_COL_2", "REPLACE_DICT_COL_3", "..."],
    [
        ["REPLACE_DICT_ROW_1_V1", "REPLACE_DICT_ROW_1_V2", "REPLACE_DICT_ROW_1_V3", ""],
        ["REPLACE_DICT_ROW_2_V1", "REPLACE_DICT_ROW_2_V2", "REPLACE_DICT_ROW_2_V3", ""],
    ],
    [40, 60, 30, 50],  # подбери ширины под свои колонки (сумма ≤ 180)
)

H2("7.2. REPLACE_FUNCTION_2_NAME — дневная статистика")
TABLE(
    ["date", "REPLACE_ENTITY_id", "REPLACE_ENTITY_name", "views", "clicks", "costs_nds", "costs_without_nds", "ak", "costs_nds_ak", "costs_without_nds_ak"],
    [
        ["REPLACE_STAT_ROW_1_DATE", "REPLACE_ID", "REPLACE_NAME", "REPLACE_V", "REPLACE_C", "REPLACE_M", "REPLACE_M_NO_NDS", "0.5", "REPLACE_M_AK", "REPLACE_M_NO_NDS_AK"],
        ["REPLACE_STAT_ROW_2_DATE", "REPLACE_ID", "REPLACE_NAME", "REPLACE_V", "REPLACE_C", "REPLACE_M", "REPLACE_M_NO_NDS", "0.5", "REPLACE_M_AK", "REPLACE_M_NO_NDS_AK"],
    ],
    [16, 16, 32, 14, 12, 20, 22, 10, 20, 18],
)
# ВАЖНО про split-pattern: REPLACE_ENTITY_id и ad_id — это API-поля, они НЕ
# являются ни константными, ни вычисляемыми. Не включать их в доп. таблицы
# «Вычисляемые поля» / «Константные поля» — там должны быть ТОЛЬКО эти типы
# полей. Для сопоставления строк между таблицами полагаемся на порядок строк
# (явно указывать в подписи: «для тех же N строк в том же порядке»).
P("Константные поля account_id, source_type_id и вычисляемое id_key_camp (для тех же 2 строк в том же порядке):")
TABLE(
    ["account_id", "source_type_id", "id_key_camp"],
    [
        ["1", "9", "1_REPLACE_ID"],
        ["1", "9", "1_REPLACE_ID"],
    ],
    [26, 32, 62],
)
P("Значения account_id и source_type_id приведены как пример — при интеграции заменить на актуальные.")

# Добавь TABLE для каждой дополнительной функции.
# Шаблон для ad-level stat-функции (добавляет id_key_ad):
# H2("7.X. REPLACE_FUNCTION_NAME — объявления × день")
# TABLE(
#     ["date", "REPLACE_ENTITY_id", "ad_id", "ad_name", "views", "clicks", "costs_nds"],
#     [["REPLACE_DATE", "REPLACE_ID", "REPLACE_AD_ID", "REPLACE_AD_NAME", "REPLACE_V", "REPLACE_C", "REPLACE_M"]],
#     [22, 24, 20, 40, 18, 14, 26],
# )
# P("Вычисляемые поля (для тех же N строк в том же порядке):")
# TABLE(
#     ["costs_without_nds", "ak", "costs_nds_ak", "costs_without_nds_ak"],
#     [["REPLACE_M_NO_NDS", "0.5", "REPLACE_M_AK", "REPLACE_M_NO_NDS_AK"]],
#     [36, 14, 32, 38],
# )
# P("Константные поля account_id, source_type_id и вычисляемые ключи id_key_camp, id_key_ad (для тех же N строк):")
# TABLE(
#     ["account_id", "source_type_id", "id_key_camp", "id_key_ad"],
#     [["1", "9", "1_REPLACE_ID", "1_REPLACE_ID_REPLACE_AD_ID"]],
#     [22, 28, 34, 42],
# )
# P("Значения account_id и source_type_id приведены как пример — при интеграции заменить на актуальные.")
#
# Шаблон для кумулятивной (reach) функции:
# H2("7.X. REPLACE_CUMULATIVE_NAME — кумулятивная метрика")
# TABLE(
#     ["date", "REPLACE_ENTITY_id", "REPLACE_ENTITY_name", "REPLACE_METRIC", "increment"],
#     [["REPLACE_DATE", "REPLACE_ID", "REPLACE_NAME", "REPLACE_VAL", "REPLACE_INC"]],
#     [22, 26, 50, 28, 28],
# )
# P("Константные поля account_id, source_type_id и вычисляемое id_key_camp (для тех же N строк):")
# TABLE(
#     ["account_id", "source_type_id", "id_key_camp"],  # + "id_key_ad" для ad-level
#     [["1", "9", "1_REPLACE_ID"]],
#     [26, 32, 62],  # для ad-level: ["account_id","source_type_id","id_key_camp","id_key_ad"] / [22,28,34,42]
# )
# P("Значения account_id и source_type_id приведены как пример — при интеграции заменить на актуальные.")

# ── 8. Рекомендации по реализации ─────────────────────────────────────────────
H1(f"8. Рекомендации по реализации на {TARGET_LANG}")
BUL([
    "REPLACE_IMPL_REC_1",   # версия языка, менеджер пакетов
    "REPLACE_IMPL_REC_2",   # HTTP-клиент
    "REPLACE_IMPL_REC_3",   # кэширование токена
    "REPLACE_IMPL_REC_4",   # parseNum
    "REPLACE_IMPL_REC_5",   # parseDateStr
    "REPLACE_IMPL_REC_6",   # pick-helper
    "REPLACE_IMPL_REC_7",   # логирование
    "REPLACE_IMPL_REC_8",   # тестирование
])

# ── 9. Критерии приёмки ───────────────────────────────────────────────────────
H1("9. Критерии приёмки")
BUL([
    "REPLACE_ACCEPTANCE_1",
    "REPLACE_ACCEPTANCE_2",
    "REPLACE_ACCEPTANCE_3",
    "REPLACE_ACCEPTANCE_4",
    "REPLACE_ACCEPTANCE_5",
    "REPLACE_ACCEPTANCE_6",
])

# ── Сохранить ─────────────────────────────────────────────────────────────────
pdf.output(OUT_FILE)
print(f"OK: {OUT_FILE}")
