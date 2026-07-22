"""Smoke-тест get_campaigns_daily_stat — живой API Bidease, требует bidease/.env.

Запуск из корня репо: python bidease/smoke_tests/test_get_campaigns_daily_stat.py
Даты — из .env (TEST_START_DATE / TEST_END_DATE, включительно). Результат —
bidease/raw_data/get_campaigns_daily_stat_{from}_{to}.csv (cp1251); показ первых
5 строк — из СОХРАНЁННОГО CSV. Старые выгрузки функции удаляются после успешного вызова.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent   # bidease/
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from bidease import get_campaigns_daily_stat  # noqa: E402


def main() -> None:
    date_from = os.environ.get("TEST_START_DATE", "").strip().strip("'\"")
    date_to = os.environ.get("TEST_END_DATE", "").strip().strip("'\"")
    assert date_from and date_to, "TEST_START_DATE / TEST_END_DATE не заданы в .env"
    print(f"Период: {date_from} → {date_to} (включительно)")

    df = get_campaigns_daily_stat(date_from, date_to)
    print(f"get_campaigns_daily_stat() -> shape={df.shape}")

    out_dir = PROJECT_ROOT / "raw_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    # очистка старых выгрузок этой функции — ПОСЛЕ успешного вызова API
    for old in out_dir.glob("get_campaigns_daily_stat_*.csv"):
        old.unlink()
    out_path = out_dir / f"get_campaigns_daily_stat_{date_from}_{date_to}.csv"
    df.to_csv(out_path, index=False, encoding="cp1251", errors="replace")
    print(f"Сохранено: {out_path}")

    saved = pd.read_csv(out_path, encoding="cp1251")
    print(f"\nИз CSV: shape={saved.shape}")
    print(f"columns: {list(saved.columns)}")
    try:
        print(saved.head(5).to_markdown(index=False))
    except ImportError:
        print(saved.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
