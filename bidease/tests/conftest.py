"""Общая настройка pytest: импорт библиотеки из соседнего каталога bidease/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
