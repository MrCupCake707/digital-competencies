from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Level(str, Enum):
    NONE = "0 — не владеет"
    INITIAL = "1 — начальный"
    BASIC = "2 — базовый"
    INTERMEDIATE = "3 — средний"
    ADVANCED = "4 — продвинутый"
    EXPERT = "5 — экспертный"

    @property
    def score(self) -> int:
        return list(Level).index(self)

    @staticmethod
    def from_score(score: int) -> "Level":
        return list(Level)[max(0, min(5, int(score)))]


@dataclass(frozen=True)
class LearningResource:
    title: str
    kind: str
    duration_hours: int
    url: str = ""

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "LearningResource":
        return LearningResource(
            title=str(raw.get("title") or raw.get("Название") or "Материал"),
            kind=str(raw.get("kind") or raw.get("Тип") or "Курс"),
            duration_hours=int(raw.get("duration_hours") or raw.get("Часы") or 1),
            url=str(raw.get("url") or raw.get("Ссылка") or ""),
        )

    def to_knowledge_dict(self) -> dict[str, Any]:
        return {
            "Название": self.title,
            "Тип": self.kind,
            "Часы": self.duration_hours,
            "Ссылка": self.url,
        }


@dataclass(frozen=True)
class Competence:
    code: str
    title: str
    direction: str
    description: str
    target_level: int
    weight: int
    difficulty: int = 3
    category: str = ""
    prerequisites: tuple[str, ...] = field(default_factory=tuple)
    resources: tuple[LearningResource, ...] = field(default_factory=tuple)

    @staticmethod
    def from_dict(raw: dict[str, Any], code: str | None = None) -> "Competence":
        competence_code = str(code or raw.get("code") or raw.get("Код") or "").strip().upper()
        target_level = int(raw.get("target_level") or raw.get("Целевой уровень") or 3)
        difficulty = int(raw.get("difficulty") or raw.get("Сложность") or target_level)
        resources = raw.get("resources") or raw.get("Материалы") or []
        prerequisites = raw.get("prerequisites") or raw.get("Предварительные компетенции") or raw.get("Зависит от") or []
        direction_raw = raw.get("direction") or raw.get("Направление") or ""

        if isinstance(direction_raw, dict):
            direction_number = str(direction_raw.get("Номер") or "").strip()
            direction_title = str(direction_raw.get("Название") or "").strip()
            direction = f"{direction_number}. {direction_title}" if direction_number else direction_title
        else:
            direction = str(direction_raw)

        return Competence(
            code=competence_code,
            title=str(raw.get("title") or raw.get("Название") or ""),
            direction=direction,
            description=str(raw.get("description") or raw.get("Описание") or raw.get("Краткое описание") or ""),
            target_level=max(0, min(5, target_level)),
            weight=max(1, min(10, int(raw.get("weight") or raw.get("Приоритет") or 1))),
            difficulty=max(1, min(5, difficulty)),
            category=str(raw.get("category") or raw.get("Категория") or ""),
            prerequisites=tuple(str(item).strip().upper() for item in prerequisites if str(item).strip()),
            resources=tuple(LearningResource.from_dict(item) for item in resources),
        )

    def to_knowledge_dict(self) -> dict[str, Any]:
        direction_number = ""
        direction_title = self.direction
        if ". " in self.direction:
            first_part, second_part = self.direction.split(". ", 1)
            if first_part.strip().isdigit():
                direction_number = int(first_part.strip())
                direction_title = second_part.strip()

        return {
            "Название": self.title,
            "Краткое описание": self.description,
            "Сложность": self.difficulty,
            "Направление": {
                "Номер": direction_number,
                "Название": direction_title,
            },
            "Категория": self.category,
            "Целевой уровень": self.target_level,
            "Приоритет": self.weight,
            "Зависит от": list(self.prerequisites),
            "Материалы": [resource.to_knowledge_dict() for resource in self.resources],
        }


@dataclass
class EmployeeProfile:
    full_name: str
    position: str
    department: str
    levels: dict[str, int]


@dataclass(frozen=True)
class TrajectoryStep:
    competence: Competence
    current_level: int
    target_level: int
    priority: float
    reason: str

    @property
    def gap(self) -> int:
        return max(0, self.target_level - self.current_level)
