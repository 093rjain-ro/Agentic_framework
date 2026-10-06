import json
from pathlib import Path

from daa_framework.framework import detect_problem, classify_problem, run_scenario, build_report


def test_fractional_knapsack_detection():
    scenario = {
        "kind": "knapsack",
        "items_divisible": True,
        "items": [{"value": 60, "weight": 10}, {"value": 100, "weight": 20}],
        "capacity": 50,
    }
    result = detect_problem(scenario)
    assert result["problem"] == "fractional_knapsack"


def test_prim_for_dense_graph():
    scenario = {
        "kind": "mst",
        "graph": {
            "vertices": ["A", "B", "C", "D"],
            "edges": [("A", "B", 1), ("A", "C", 2), ("B", "C", 3), ("B", "D", 4), ("C", "D", 5), ("A", "D", 6)],
        },
        "graph_density": 0.8,
    }
    result = detect_problem(scenario)
    assert result["algorithm"] in {"prim", "kruskal"}


def test_tsp_detection_and_execution():
    scenario = {
        "kind": "tsp",
        "graph": {
            "vertices": ["A", "B", "C"],
            "edges": [("A", "B", 1), ("A", "C", 2), ("B", "C", 3), ("B", "A", 1), ("C", "A", 2), ("C", "B", 3)],
        },
        "return_to_start": True,
    }
    result = detect_problem(scenario)
    assert result["problem"] == "tsp"
    assert run_scenario(scenario)["status"] == "ok"


def test_complexity_classification():
    assert classify_problem("fractional_knapsack")["complexity"] == "polynomial"
    assert classify_problem("tsp")["complexity"] == "np_hard"


def test_scenario_file_run(tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps({
        "kind": "mst",
        "graph": {"vertices": ["A", "B", "C"], "edges": [("A", "B", 1), ("B", "C", 2), ("A", "C", 3)]},
        "graph_density": 0.8,
    }))
    result = run_scenario(scenario_path)
    assert result["status"] == "ok"


def test_report_has_assignment_sections():
    report = build_report()
    assert "Scenario and objective" in report
    assert "Why this algorithm was chosen" in report
    assert "Complexity classification" in report
    assert "What changes when the input changes" in report
    assert "Architecture" in report
