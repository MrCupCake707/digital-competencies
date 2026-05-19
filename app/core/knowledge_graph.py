from __future__ import annotations

from collections import defaultdict, deque
import re

from app.core.models import Competence


class KnowledgeGraph:
    def __init__(self, competences: list[Competence]) -> None:
        self._nodes = {item.code: item for item in competences}
        self._children: dict[str, list[str]] = defaultdict(list)

        for item in competences:
            for parent in item.prerequisites:
                self._children[parent].append(item.code)

        self._validate_graph()

    @property
    def nodes(self) -> dict[str, Competence]:
        return dict(self._nodes)

    def get(self, code: str) -> Competence:
        return self._nodes[code]

    def by_direction(self, direction: str) -> list[Competence]:
        return [node for node in self._nodes.values() if node.direction == direction]

    def directions(self) -> list[str]:
        return sorted({node.direction for node in self._nodes.values()}, key=natural_direction_key)

    def prerequisites_chain(self, code: str) -> list[str]:
        visited: set[str] = set()
        result: list[str] = []

        def visit(current: str) -> None:
            for parent in self._nodes[current].prerequisites:
                if parent not in visited:
                    visited.add(parent)
                    visit(parent)
                    result.append(parent)

        visit(code)
        return result

    def topological_sort(self, codes: set[str] | None = None) -> list[str]:
        selected = codes or set(self._nodes)
        indegree = {code: 0 for code in selected}

        for code in selected:
            for parent in self._nodes[code].prerequisites:
                if parent in selected:
                    indegree[code] += 1

        queue = deque(sorted(code for code, degree in indegree.items() if degree == 0))
        result: list[str] = []

        while queue:
            code = queue.popleft()
            result.append(code)
            for child in sorted(self._children.get(code, [])):
                if child in indegree:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        queue.append(child)

        if len(result) != len(selected):
            raise ValueError("В графе компетенций обнаружен цикл зависимостей.")

        return result

    def _validate_graph(self) -> None:
        missing = [
            f"{node.code} -> {parent}"
            for node in self._nodes.values()
            for parent in node.prerequisites
            if parent not in self._nodes
        ]
        if missing:
            raise ValueError("Не найдены предварительные компетенции: " + ", ".join(missing))

        self.topological_sort()


def natural_direction_key(direction: str) -> tuple[int, str]:
    match = re.match(r"\s*(\d+)", direction)
    number = int(match.group(1)) if match else 9999
    return number, direction.lower()
