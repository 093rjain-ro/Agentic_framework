from __future__ import annotations

import json
import math
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


DENSITY_THRESHOLD = 0.4
DECREASE_KEY_DOMINANCE = 1.0


class DSU:
    def __init__(self, vertices):
        self.parent = {v: v for v in vertices}
        self.rank = {v: 0 for v in vertices}

    def find(self, value):
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1
        return True


def load_scenario(input_data: Any) -> Dict[str, Any]:
    if isinstance(input_data, (str, Path)):
        path = Path(input_data)
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        return json.loads(str(input_data))
    if isinstance(input_data, dict):
        return input_data
    raise ValueError("Scenario must be a JSON dict or a file path")


def compute_graph_density(graph: Dict[str, Any]) -> float:
    vertices = graph.get("vertices", [])
    edges = graph.get("edges", [])
    if not vertices:
        return 0.0
    n = len(vertices)
    possible = n * (n - 1) / 2 if n > 1 else 1
    return len(edges) / possible if possible else 0.0


def classify_problem(problem_name: str) -> Dict[str, Any]:
    mapping = {
        "red_black_tree": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; search/insert/delete are O(log n)",
        },
        "b_tree": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; search/insert/delete are O(log n) with high fan-out (disk-friendly)",
        },
        "binomial_heap": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; merge is efficient, operations near O(log n)",
        },
        "fibonacci_heap": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; decrease-key is amortized O(1)",
        },
        "mst": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; MST is O(E log V) or better with appropriate heaps",
        },
        "floyd_warshall": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; all-pairs shortest paths are Θ(V³)",
        },
        "fractional_knapsack": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; greedy by value/weight is optimal for divisible items",
        },
        "zero_one_knapsack": {
            "complexity": "pseudo_polynomial",
            "class": "pseudo_polynomial",
            "decision_vs_optimization": "Decision version is NP-Complete; optimization version is pseudo-polynomial in capacity W",
        },
        "matrix_chain": {
            "complexity": "polynomial",
            "class": "polynomial",
            "decision_vs_optimization": "Optimization version is polynomial; classic DP over parenthesizations",
        },
        "hamiltonian": {
            "complexity": "np_complete",
            "class": "np_complete",
            "decision_vs_optimization": "Decision version is NP-Complete; feasibility of a Hamiltonian cycle",
        },
        "n_queens": {
            "complexity": "exponential",
            "class": "exponential",
            "decision_vs_optimization": "Feasibility / constraint-satisfaction problem; worst-case exponential search tree",
        },
        "tsp": {
            "complexity": "np_hard",
            "class": "np_hard",
            "decision_vs_optimization": "Optimization version is NP-Hard; decision version is NP-Complete",
        },
    }
    return mapping.get(problem_name, {
        "complexity": "unknown",
        "class": "unknown",
        "decision_vs_optimization": "Unknown",
    })


def build_decision_result(
    *,
    problem_type: str,
    chosen_algorithm: str,
    alternative: str,
    rule_id: str,
    rule_fired: str,
    explanation: str,
    features: Dict[str, Any],
) -> Dict[str, Any]:
    complexity = classify_problem(problem_type)
    return {
        "problem_type": problem_type,
        "chosen_algorithm": chosen_algorithm,
        "alternative": alternative,
        "rule_id": rule_id,
        "rule_fired": rule_fired,
        "complexity_class": complexity["class"],
        "complexity": complexity["complexity"],
        "decision_vs_optimization": complexity["decision_vs_optimization"],
        "explanation": explanation,
        "features": features,
        "problem": problem_type,
        "algorithm": chosen_algorithm,
        "reason": explanation,
    }


def detect_problem(scenario: Any) -> Dict[str, Any]:
    data = load_scenario(scenario)
    graph = data.get("graph") or {}
    graph_density = data.get("graph_density")
    if graph_density is None and isinstance(graph, dict):
        graph_density = compute_graph_density(graph)

    kind = str(data.get("kind", "")).lower().strip()

    features = {
        "kind": kind,
        "graph_density": graph_density,
        "storage": data.get("storage"),
        "disk_based": data.get("disk_based"),
        "needs_mergeable_priority": data.get("needs_mergeable_priority"),
        "decrease_key_ratio": data.get("decrease_key_ratio", 0.0),
        "merge_ratio": data.get("merge_ratio", 0.0),
        "return_to_start": data.get("return_to_start"),
        "items_divisible": data.get("items_divisible"),
        "matrix_dims": data.get("matrix_dims"),
        "n": data.get("n"),
        "must_visit_each_vertex": data.get("must_visit_each_vertex"),
        "grid_conflict_constraints": data.get("grid_conflict_constraints"),
        "all_pairs_needed": data.get("all_pairs_needed"),
    }

    if kind in {"ordered_search", "ordered_searchable_data", "red_black_tree", "b_tree"}:
        if data.get("storage") == "disk" or data.get("disk_based"):
            return build_decision_result(
                problem_type="b_tree",
                chosen_algorithm="b_tree",
                alternative="red_black_tree",
                rule_id="RULE_ORDERED_DISK",
                rule_fired="storage == 'disk' or disk_based == True",
                explanation="Disk-resident ordered data benefits from high fan-out (B-Tree) to minimise page I/O.",
                features=features,
            )
        return build_decision_result(
            problem_type="red_black_tree",
            chosen_algorithm="red_black_tree",
            alternative="b_tree",
            rule_id="RULE_ORDERED_MEMORY",
            rule_fired="in-memory ordered search with mixed updates",
            explanation="In-memory ordered dictionary with frequent inserts/deletes/lookups fits a balanced BST (Red-Black Tree).",
            features=features,
        )

    if (kind in {"priority_queue", "mergeable_priority", "priority_workload"}
            or data.get("needs_mergeable_priority")):
        dec_ratio = float(data.get("decrease_key_ratio", 0) or 0)
        merge_ratio = float(data.get("merge_ratio", 0) or 0)

        if dec_ratio > merge_ratio * DECREASE_KEY_DOMINANCE:
            return build_decision_result(
                problem_type="fibonacci_heap",
                chosen_algorithm="fibonacci_heap",
                alternative="binomial_heap",
                rule_id="RULE_HEAP_DECREASE_KEY",
                rule_fired=f"decrease_key_ratio ({dec_ratio}) > merge_ratio ({merge_ratio})",
                explanation="Decrease-key heavy workload favours Fibonacci Heap (amortized O(1) decrease-key).",
                features=features,
            )
        return build_decision_result(
            problem_type="binomial_heap",
            chosen_algorithm="binomial_heap",
            alternative="fibonacci_heap",
            rule_id="RULE_HEAP_MERGE",
            rule_fired="merge-heavy or balanced priority workload",
            explanation="Merge-heavy or balanced priority workload is well-served by Binomial Heap (efficient meld + simpler constants).",
            features=features,
        )

    if kind in {"tsp", "traveling_salesperson", "traveling_salesman"} or data.get("return_to_start"):
        return build_decision_result(
            problem_type="tsp",
            chosen_algorithm="branch_and_bound",
            alternative="held_karp_dp_or_nearest_neighbor",
            rule_id="RULE_TSP",
            rule_fired="return_to_start == True or kind indicates TSP",
            explanation="Minimum-cost complete tour (return to start). Branch-and-Bound is an exact method suitable for modest n.",
            features=features,
        )

    if kind in {"mst", "minimum_spanning_tree"} or graph:
        dens = graph_density if graph_density is not None else 0.0
        if dens >= DENSITY_THRESHOLD:
            preferred = data.get("preferred_algorithm", "prim")
            return build_decision_result(
                problem_type="mst",
                chosen_algorithm=preferred,
                alternative="kruskal",
                rule_id="RULE_MST_DENSE",
                rule_fired=f"graph_density ({dens:.3f}) >= {DENSITY_THRESHOLD}",
                explanation="Dense graph → Prim is typically preferable (avoids sorting all edges, works well with adjacency matrix / dense representation).",
                features=features,
            )
        preferred = data.get("preferred_algorithm", "kruskal")
        return build_decision_result(
            problem_type="mst",
            chosen_algorithm=preferred,
            alternative="prim",
            rule_id="RULE_MST_SPARSE",
            rule_fired=f"graph_density ({dens:.3f}) < {DENSITY_THRESHOLD}",
            explanation="Sparse graph → Kruskal + Union-Find is efficient and simple.",
            features=features,
        )

    if kind in {"floyd_warshall", "all_pairs_shortest_path"} or data.get("all_pairs_needed"):
        return build_decision_result(
            problem_type="floyd_warshall",
            chosen_algorithm="floyd_warshall",
            alternative="repeated_dijkstra",
            rule_id="RULE_ALL_PAIRS",
            rule_fired="all_pairs_needed == True",
            explanation="All-pairs shortest paths required. Floyd-Warshall is the classic exact O(V³) solution (especially natural on dense graphs).",
            features=features,
        )

    if kind in {"knapsack", "fractional_knapsack", "zero_one_knapsack"} or "items_divisible" in data:
        if data.get("items_divisible"):
            return build_decision_result(
                problem_type="fractional_knapsack",
                chosen_algorithm="fractional_knapsack",
                alternative="zero_one_knapsack",
                rule_id="RULE_KNAPSACK_FRACTIONAL",
                rule_fired="items_divisible == True",
                explanation="Items may be taken fractionally → greedy by value/weight is optimal and polynomial.",
                features=features,
            )
        return build_decision_result(
            problem_type="zero_one_knapsack",
            chosen_algorithm="zero_one_knapsack",
            alternative="fractional_knapsack",
            rule_id="RULE_KNAPSACK_01",
            rule_fired="items_divisible == False",
            explanation="Items are indivisible → classic 0/1 Knapsack solved by pseudo-polynomial DP.",
            features=features,
        )

    if kind in {"matrix_chain", "matrix_chain_multiplication"} or data.get("matrix_dims"):
        return build_decision_result(
            problem_type="matrix_chain",
            chosen_algorithm="matrix_chain_multiplication",
            alternative="naive_parenthesization",
            rule_id="RULE_MATRIX_CHAIN",
            rule_fired="matrix_dims provided",
            explanation="Sequence of matrix dimensions defines an optimal parenthesization problem; solved by DP.",
            features=features,
        )

    if kind in {"hamiltonian", "hamiltonian_cycle"} or data.get("must_visit_each_vertex"):
        return build_decision_result(
            problem_type="hamiltonian",
            chosen_algorithm="backtracking",
            alternative="held_karp_style_dp",
            rule_id="RULE_HAMILTONIAN",
            rule_fired="must_visit_each_vertex == True",
            explanation="Visit-every-vertex-exactly-once feasibility problem. Backtracking is appropriate for small instances.",
            features=features,
        )

    if (kind in {"n_queen", "nqueens", "n_queens", "conflict_free_placement"}
            or data.get("grid_conflict_constraints")):
        return build_decision_result(
            problem_type="n_queens",
            chosen_algorithm="backtracking",
            alternative="constraint_programming",
            rule_id="RULE_NQUEENS",
            rule_fired="grid_conflict_constraints == True or kind indicates N-Queens",
            explanation="Non-attacking / mutually conflicting placement on a grid → classic backtracking constraint satisfaction.",
            features=features,
        )

    if data.get("storage") == "disk" or data.get("disk_based"):
        return build_decision_result(
            problem_type="b_tree",
            chosen_algorithm="b_tree",
            alternative="red_black_tree",
            rule_id="RULE_ORDERED_DISK_FALLBACK",
            rule_fired="storage == 'disk' (fallback)",
            explanation="Disk-based ordered data → B-Tree.",
            features=features,
        )

    raise ValueError(f"Unhandled scenario: {data}")


def fractional_knapsack(items: Iterable[Dict[str, float]], capacity: float) -> Dict[str, Any]:
    list_items = list(items)
    total_value = 0.0
    total_weight = 0.0
    chosen: List[Dict[str, Any]] = []
    for item in sorted(list_items, key=lambda x: (x["value"] / x["weight"], x["value"]), reverse=True):
        if capacity <= 0:
            break
        take = min(item["weight"], capacity)
        fraction = take / item["weight"] if item["weight"] > 0 else 0
        total_value += item["value"] * fraction
        total_weight += take
        chosen.append({"name": item.get("name", "item"), "fraction": fraction, "weight": take, "value": item["value"] * fraction})
        capacity -= take
    return {"total_value": total_value, "total_weight": total_weight, "chosen": chosen}


def zero_one_knapsack(items: Iterable[Dict[str, float]], capacity: float) -> Dict[str, Any]:
    list_items = list(items)
    n = len(list_items)
    dp = [[0.0 for _ in range(int(capacity) + 1)] for _ in range(n + 1)]
    for i in range(1, n + 1):
        item = list_items[i - 1]
        weight = int(item["weight"])
        value = item["value"]
        for w in range(int(capacity) + 1):
            if weight <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weight] + value)
            else:
                dp[i][w] = dp[i - 1][w]
    return {"total_value": dp[n][int(capacity)], "dp": dp}


def minimum_spanning_tree(graph: Dict[str, Any], algorithm: str = "prim") -> Dict[str, Any]:
    vertices = graph.get("vertices", [])
    edge_list = graph.get("edges", [])
    if algorithm.lower() == "prim":
        start = vertices[0] if vertices else None
        if start is None:
            return {"cost": 0, "edges": []}
        visited = {start}
        adjacency = defaultdict(list)
        for u, v, w in edge_list:
            adjacency[u].append((v, w))
            adjacency[v].append((u, w))
        edges = []
        total_cost = 0
        candidates = [(w, start, neighbour) for neighbour, w in adjacency[start]]
        while len(visited) < len(vertices) and candidates:
            w, u, v = min(candidates)
            candidates.remove((w, u, v))
            if v in visited:
                continue
            visited.add(v)
            edges.append((u, v, w))
            total_cost += w
            for next_vertex, next_w in adjacency[v]:
                if next_vertex not in visited:
                    candidates.append((next_w, v, next_vertex))
        return {"cost": total_cost, "edges": edges, "tree": edges}

    dsu = DSU(vertices)
    selected = []
    total_cost = 0
    for u, v, w in sorted(edge_list, key=lambda e: e[2]):
        if dsu.union(u, v):
            selected.append((u, v, w))
            total_cost += w
    return {"cost": total_cost, "edges": selected, "tree": selected}


def floyd_warshall(graph: Dict[str, Any]) -> Dict[str, Any]:
    vertices = graph.get("vertices", [])
    edges = graph.get("edges", [])
    dist = {u: {v: math.inf for v in vertices} for u in vertices}
    for u in vertices:
        dist[u][u] = 0
    for u, v, w in edges:
        if dist[u].get(v, math.inf) > w:
            dist[u][v] = w
        if dist[v].get(u, math.inf) > w:
            dist[v][u] = w
    for k in vertices:
        for i in vertices:
            for j in vertices:
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return {"distances": dist, "matrix": dist}


def matrix_chain_multiplication(dimensions: List[int]) -> Dict[str, Any]:
    n = len(dimensions)
    dp = [[0 for _ in range(n)] for _ in range(n)]
    split = [[-1 for _ in range(n)] for _ in range(n)]
    for length in range(2, n):
        for i in range(1, n - length + 2):
            j = i + length - 1
            dp[i][j] = math.inf
            for k in range(i, j):
                cost = dp[i][k] + dp[k + 1][j] + dimensions[i - 1] * dimensions[k] * dimensions[j]
                if cost < dp[i][j]:
                    dp[i][j] = cost
                    split[i][j] = k
    return {"cost": dp[1][n - 1], "table": dp, "split": split}


def is_safe(board: List[int], row: int, col: int) -> bool:
    for prev_row in range(row):
        if board[prev_row] == col or abs(board[prev_row] - col) == row - prev_row:
            return False
    return True


def solve_n_queens(n: int) -> Dict[str, Any]:
    if n <= 0:
        return {"solutions": [], "count": 0}
    board = [-1] * n
    solutions: List[List[int]] = []

    def backtrack(row: int):
        if row == n:
            solutions.append(board.copy())
            return
        for col in range(n):
            if is_safe(board, row, col):
                board[row] = col
                backtrack(row + 1)
                board[row] = -1

    backtrack(0)
    return {"solutions": solutions, "count": len(solutions)}


def hamiltonian_cycle(graph: Dict[str, Any]) -> Dict[str, Any]:
    vertices = graph.get("vertices", [])
    edges = graph.get("edges", [])
    adjacency = defaultdict(set)
    for u, v, *_rest in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    start = vertices[0] if vertices else None
    if start is None:
        return {"exists": False, "cycle": []}

    visited = {start}
    path = [start]

    def dfs(node: str):
        if len(path) == len(vertices):
            return node in adjacency and start in adjacency[node]
        for nxt in sorted(adjacency.get(node, set())):
            if nxt not in visited:
                visited.add(nxt)
                path.append(nxt)
                if dfs(nxt):
                    return True
                path.pop()
                visited.remove(nxt)
        return False

    exists = dfs(start)
    return {"exists": exists, "cycle": path if exists else []}


def tsp_branch_and_bound(graph: Dict[str, Any]) -> Dict[str, Any]:
    vertices = graph.get("vertices", [])
    edges = graph.get("edges", [])
    if not vertices:
        return {"cost": 0, "tour": []}
    dist = {(u, v): w for u, v, w in edges}
    for u, v, w in edges:
        dist[(v, u)] = w
    n = len(vertices)
    start = vertices[0]
    best_cost = math.inf
    best_path: List[str] = []
    visited = {start}

    def bound(path: List[str], current: str) -> float:
        remaining = [v for v in vertices if v not in path]
        if not remaining:
            return 0
        return min(dist.get((current, target), math.inf) for target in remaining)

    def dfs(current: str, total_cost: float, path: List[str]):
        nonlocal best_cost, best_path
        if len(path) == n:
            return_to_start = dist.get((current, start), math.inf)
            if return_to_start < math.inf:
                candidate_cost = total_cost + return_to_start
                if candidate_cost < best_cost:
                    best_cost = candidate_cost
                    best_path = path + [start]
            return
        for nxt in vertices:
            if nxt in visited:
                continue
            edge_cost = dist.get((current, nxt), math.inf)
            if edge_cost == math.inf:
                continue
            lower_bound = total_cost + edge_cost + bound(path + [nxt], nxt)
            if lower_bound >= best_cost:
                continue
            visited.add(nxt)
            dfs(nxt, total_cost + edge_cost, path + [nxt])
            visited.remove(nxt)

    dfs(start, 0.0, [start])
    return {"cost": best_cost if best_cost < math.inf else 0, "tour": best_path}


def run_scenario(scenario: Any) -> Dict[str, Any]:
    data = load_scenario(scenario)
    decision = detect_problem(data)
    start = time.perf_counter()
    tracemalloc.start()
    try:
        if decision["problem"] == "fractional_knapsack":
            result = fractional_knapsack(data.get("items", []), data.get("capacity", 0))
        elif decision["problem"] == "zero_one_knapsack":
            result = zero_one_knapsack(data.get("items", []), data.get("capacity", 0))
        elif decision["problem"] == "mst":
            result = minimum_spanning_tree(data.get("graph", {}), decision.get("algorithm", "prim"))
        elif decision["problem"] == "floyd_warshall":
            result = floyd_warshall(data.get("graph", {}))
        elif decision["problem"] == "matrix_chain":
            dims = data.get("matrix_dims", [])
            result = matrix_chain_multiplication(dims)
        elif decision["problem"] == "n_queens":
            n = int(data.get("n", 4))
            result = solve_n_queens(n)
        elif decision["problem"] == "hamiltonian":
            result = hamiltonian_cycle(data.get("graph", {}))
        elif decision["problem"] == "tsp":
            result = tsp_branch_and_bound(data.get("graph", {}))
        else:
            result = {"status": "not_implemented"}
        elapsed = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {
            "status": "ok",
            "decision": decision,
            "result": result,
            "runtime_seconds": round(elapsed, 6),
            "memory_bytes": peak,
        }
    except Exception as exc:  # pragma: no cover - defensive guard
        tracemalloc.stop()
        return {
            "status": "error",
            "decision": decision,
            "error": str(exc),
        }


def generate_architecture_diagram() -> str:
    return """flowchart LR
    A[Scenario / JSON Input] --> B[Problem Modeller]
    B --> C[Rule-based Decision Engine]
    C --> D[Algorithm / Data Structure Selection]
    D --> E[Execution]
    E --> F[Measurement and Analysis]
    F --> G[Explanation and Output]
"""


def build_report() -> str:
    return """
# DAA Decision Framework Report

## Architecture

```text
Scenario Input
    ↓
Feature Extraction
    ↓
Rule-based Decision Engine
    ↓
Algorithm / Data Structure Selection
    ↓
Execution + Measurement
    ↓
Explanation + Complexity Classification
```

## Scenario and objective
The framework reads a scenario expressed as structured data, identifies the entities, constraints, and optimization goal, and then maps it to an appropriate design-and-analysis-of-algorithms formulation. It handles graph, ordering, optimization, feasibility, and dynamic-programming problems under a single rule-based engine.

## Decision rules and thresholds
- Dense graph: if graph_density >= 0.4, prefer Prim for MST; otherwise choose Kruskal.
- Ordered searchable data: choose B-Tree for disk workloads and Red-Black Tree for in-memory workloads.
- Priority queue workload: if decrease_key_ratio > merge_ratio, prefer Fibonacci Heap; otherwise prefer Binomial Heap.
- Divisible items: if items_divisible is true, choose Fractional Knapsack; otherwise use 0/1 Knapsack.
- All-pairs shortest path: if all_pairs_needed is true, choose Floyd-Warshall.
- Matrix chain: if matrix dimensions are supplied, use matrix-chain dynamic programming.
- Feasibility search: if the task is to visit every vertex exactly once, use Hamiltonian backtracking.
- Placement constraints: use N-Queens style backtracking when conflict constraints are present.
- Complete tour: if the goal is a minimum complete tour, use TSP branch-and-bound.

## Why this algorithm was chosen
The framework does not hard-code a single answer for every input. Instead, it inspects the scenario features and compares the best matching DAA method against a meaningful alternative. For example:

- Prim vs Kruskal: dense graphs favour Prim; sparse graphs favour Kruskal.
- Fractional vs 0/1 Knapsack: divisible items allow greedy choice; indivisible items require DP.
- Fibonacci vs Binomial Heap: decrease-key-heavy workloads favour Fibonacci Heap; merge-heavy workloads favour Binomial Heap.
- B-Tree vs Red-Black Tree: disk-backed ordered data needs B-Tree; in-memory ordered data suits Red-Black Tree.

## Complexity classification
- MST: polynomial
- Fractional Knapsack: polynomial
- 0/1 Knapsack: pseudo-polynomial; decision version is NP-Complete
- TSP: NP-Hard optimization; decision version is NP-Complete
- Hamiltonian cycle: NP-Complete decision problem
- N-Queens: exponential worst-case search tree; not automatically NP-Complete under the usual formulation
- Floyd-Warshall: polynomial, O(V^3)
- Matrix-chain multiplication: polynomial dynamic-programming solution

## Measured runtime and memory
The framework measures runtime with time.perf_counter() and memory with tracemalloc. Each run returns a runtime_seconds value and a memory_bytes peak. These are used alongside theoretical complexity to explain why some problems scale differently as input size increases.

## What changes when the input changes
The framework is intentionally sensitive to the scenario features:
- Switching from sparse to dense graphs changes MST selection from Kruskal to Prim.
- Switching from divisible to indivisible items changes the solution from greedy to dynamic programming.
- Increasing the decrease-key ratio relative to the merge ratio shifts the heap choice from Binomial to Fibonacci.
- Larger n values create explosively larger search spaces for N-Queens, Hamiltonian, and TSP.

## Limitations and scalability notes
The framework is best for small to medium exact instances where the problem can be described clearly enough to identify a correct DAA formulation. NP-hard and NP-complete problems are handled exactly, but their combinatorial growth means they become impractical as n increases. The rule-based design is deterministic and transparent, which is valuable for teaching and comparison, but it is not a general-purpose intelligent optimizer.

## Validation
The framework is tested with pytest across detection logic, execution, and scenario-file handling. The test suite confirms that the main decision rules and solver calls work as intended.
"""


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the autonomous DAA decision framework.")
    parser.add_argument("scenario", nargs="?", help="Path to a JSON scenario file or inline JSON text")
    args = parser.parse_args()

    scenario = args.scenario or """
    {
      "kind": "mst",
      "graph_density": 0.9,
      "graph": {
        "vertices": ["A","B","C","D"],
        "edges": [["A","B",1],["A","C",2],["B","C",3],["B","D",4],["C","D",5],["A","D",6]]
      }
    }
    """
    result = run_scenario(scenario)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
