import json
from pathlib import Path

from daa_framework.framework import (
    build_report,
    classify_problem,
    detect_problem,
    fractional_knapsack,
    minimum_spanning_tree,
    run_scenario,
    tsp_branch_and_bound,
)


def test_fractional_knapsack_detection():
    scenario = {
        "kind": "knapsack",
        "items_divisible": True,
        "items": [{"value": 60, "weight": 10}, {"value": 100, "weight": 20}],
        "capacity": 50,
    }
    result = detect_problem(scenario)
    assert result["problem"] == "fractional_knapsack"


def test_fractional_knapsack_includes_positive_value_zero_weight_items():
    result = fractional_knapsack(
        [{"name": "free", "value": 5, "weight": 0}, {"name": "paid", "value": 10, "weight": 2}],
        1,
    )

    assert result["total_value"] == 10
    assert result["total_weight"] == 1
    assert result["chosen"][0] == {"name": "free", "fraction": 1.0, "weight": 0, "value": 5}


def test_disconnected_mst_is_not_reported_as_spanning_tree():
    graph = {"vertices": ["A", "B", "C"], "edges": [("A", "B", 1)]}

    assert minimum_spanning_tree(graph, "prim")["is_spanning_tree"] is False
    assert minimum_spanning_tree(graph, "kruskal")["is_spanning_tree"] is False


def test_tsp_without_a_tour_does_not_report_zero_cost():
    graph = {"vertices": ["A", "B", "C"], "edges": [("A", "B", 1)]}

    result = tsp_branch_and_bound(graph)

    assert result["tour_found"] is False
    assert result["cost"] is None
    assert result["tour"] == []


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


def test_benchmark_cases_generate_metrics():
    from daa_framework.framework import benchmark_cases

    rows = benchmark_cases()
    assert len(rows) >= 4
    assert all("name" in row and "runtime_seconds" in row and "memory_bytes" in row for row in rows)
    assert any(row["name"] == "dense_mst" for row in rows)
