from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.models import Competence, EmployeeProfile

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
COMPETENCES_PATH = DATA_DIR / "competences.json"
KNOWLEDGE_BASE_PATH = DATA_DIR / "knowledge_base.json"
DEFAULT_PROFILES_PATH = DATA_DIR / "default_profiles.json"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_competences() -> list[Competence]:
    path = COMPETENCES_PATH if COMPETENCES_PATH.exists() else KNOWLEDGE_BASE_PATH
    raw_items = read_json(path)

    if isinstance(raw_items, dict) and "Компетенции" in raw_items:
        raw_items = raw_items["Компетенции"]

    if isinstance(raw_items, dict):
        competences = [
            Competence.from_dict(payload, code)
            for code, payload in raw_items.items()
            if not str(code).startswith("_") and isinstance(payload, dict)
        ]
    else:
        competences = [Competence.from_dict(item) for item in raw_items]

    return sorted(competences, key=lambda item: item.code)


def save_competences(competences: list[Competence]) -> None:
    data = {
        "Описание файла": "Справочник цифровых компетенций приложения. Каждый блок DCxx описывает одну компетенцию.",
        "Подсказка по полям": {
            "Название": "Краткое название компетенции",
            "Краткое описание": "Что должен понимать или уметь сотрудник",
            "Сложность": "Сложность освоения от 1 до 5",
            "Направление": "Номер и название направления развития",
            "Категория": "Группа для окраски графа и фильтрации",
            "Целевой уровень": "Желаемый уровень владения от 0 до 5",
            "Приоритет": "Важность компетенции от 1 до 10",
            "Зависит от": "Коды компетенций, которые желательно освоить раньше",
            "Материалы": "Рекомендуемые учебные материалы"
        },
        "Компетенции": {
            competence.code: competence.to_knowledge_dict()
            for competence in sorted(competences, key=lambda item: item.code)
        },
    }
    COMPETENCES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_default_profiles() -> list[EmployeeProfile]:
    raw_items = read_json(DEFAULT_PROFILES_PATH)
    return [EmployeeProfile(**item) for item in raw_items]
