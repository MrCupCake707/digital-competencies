import unittest

from app.core.knowledge_graph import KnowledgeGraph
from app.core.models import EmployeeProfile
from app.core.trajectory_builder import TrajectoryBuilder
from app.storage.loaders import load_competences


class TrajectoryTestCase(unittest.TestCase):
                                                                                  
    def test_trajectory_contains_gaps(self) -> None:
                                                                                                            
        graph = KnowledgeGraph(load_competences())
        profile = EmployeeProfile("Тест", "Аналитик", "ИТ", {code: 0 for code in graph.nodes})
        steps = TrajectoryBuilder(graph).build(profile)
        self.assertGreaterEqual(len(steps), 15)
        self.assertTrue(all(step.current_level < step.target_level for step in steps))

    def test_graph_has_no_cycles(self) -> None:
                                                                                                       
        graph = KnowledgeGraph(load_competences())
        ordered = graph.topological_sort()
        self.assertEqual(len(ordered), len(graph.nodes))


    def test_directions_sorted_naturally(self) -> None:
                                                                                                               
        graph = KnowledgeGraph(load_competences())
        directions = graph.directions()
        self.assertLess(
            directions.index("2. Поиск и проверка информации"),
            directions.index("10. Электронный документооборот"),
        )
        self.assertLess(
            directions.index("9. Клиентский опыт и цифровые сервисы"),
            directions.index("10. Электронный документооборот"),
        )

    def test_trajectory_sorted_by_direction_number(self) -> None:
                                                                                                                         
        graph = KnowledgeGraph(load_competences())
        profile = EmployeeProfile("Тест", "", "", {})
        steps = TrajectoryBuilder(graph).build(profile, "Все направления")
        numbers = [int(step.competence.direction.split(".", 1)[0]) for step in steps]
        self.assertEqual(numbers, sorted(numbers))


if __name__ == "__main__":
    unittest.main()
