from __future__ import annotations

from app.core.knowledge_graph import KnowledgeGraph, natural_direction_key
from app.core.models import EmployeeProfile, TrajectoryStep


class TrajectoryBuilder:
    MAX_PRIORITY = 10.0

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def build(self, profile: EmployeeProfile, target_direction: str | None = None) -> list[TrajectoryStep]:
        selected_codes = self._select_codes(target_direction)
        ordered_codes = self.graph.topological_sort(selected_codes)
        raw_steps = [self._build_step_data(profile, code) for code in ordered_codes]
        raw_steps = [item for item in raw_steps if item is not None]

        max_priority = max((item[3] for item in raw_steps), default=1.0)
        steps = [
            TrajectoryStep(
                competence=item[0],
                current_level=item[1],
                target_level=item[2],
                priority=min(self.MAX_PRIORITY, round(item[3] / max_priority * self.MAX_PRIORITY, 1)),
                reason=item[4],
            )
            for item in raw_steps
        ]

        return sorted(
            steps,
            key=lambda item: (
                natural_direction_key(item.competence.direction),
                item.competence.code,
                item.competence.title,
            ),
        )

    def _select_codes(self, target_direction: str | None) -> set[str]:
        if target_direction and target_direction != "Все направления":
            initial_codes = {item.code for item in self.graph.by_direction(target_direction)}
        else:
            initial_codes = set(self.graph.nodes)

        selected_codes = set(initial_codes)
        for code in initial_codes:
            selected_codes.update(self.graph.prerequisites_chain(code))

        return selected_codes

    def _build_step_data(self, profile: EmployeeProfile, code: str) -> tuple[object, int, int, float, str] | None:
        competence = self.graph.get(code)
        current_level = max(0, min(5, int(profile.levels.get(code, 0))))
        target_level = max(0, min(5, competence.target_level))

        if current_level >= target_level:
            return None

        gap = target_level - current_level
        prerequisite_gap = sum(
            max(0, self.graph.get(parent).target_level - int(profile.levels.get(parent, 0)))
            for parent in competence.prerequisites
        )
        priority = gap * competence.weight + prerequisite_gap * 0.5 + competence.difficulty * 0.2
        return competence, current_level, target_level, priority, self._make_reason(gap, prerequisite_gap)

    @staticmethod
    def _make_reason(gap: int, prerequisite_gap: float) -> str:
        if prerequisite_gap > 0:
            return "Есть пробелы в предварительных знаниях, поэтому компетенция повышена в приоритете."
        if gap >= 3:
            return "Большой разрыв между текущим и требуемым уровнем."
        if gap == 2:
            return "Средний разрыв, требуется плановое обучение."
        return "Небольшой разрыв, достаточно короткого курса или практики."
