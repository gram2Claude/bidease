"""Smoke-тест get_campaign_dict — живой API Bidease, требует bidease/.env.

Запуск из корня репо: python bidease/smoke_tests/test_get_campaign_dict.py
Результат сохраняется в bidease/raw_data/get_campaign_dict.csv (cp1251);
показ первых 5 строк — из СОХРАНЁННОГО CSV (верифицирует запись файла).
Имя файла фиксированное (справочник) — перезаписывается сам, очистка не нужна.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent   # bidease/
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from bidease import get_campaign_dict  # noqa: E402  (после sys.path/.env)


def main() -> None:
    df = get_campaign_dict()
    print(f"get_campaign_dict() -> shape={df.shape}")

    out_path = PROJECT_ROOT / "raw_data" / "get_campaign_dict.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="cp1251", errors="replace")
    print(f"Сохранено: {out_path}")

    # Показ — из сохранённого файла, не из памяти
    saved = pd.read_csv(out_path, encoding="cp1251")
    print(f"\nИз CSV: shape={saved.shape}")
    print(f"columns: {list(saved.columns)}")
    try:
        print(saved.head(5).to_markdown(index=False))
    except ImportError:                      # tabulate не установлен
        print(saved.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
