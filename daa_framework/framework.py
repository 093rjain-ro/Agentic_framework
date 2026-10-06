from __future__ import annotations

import json
import math
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


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
        "red_black_tree": {"complexity": "polynomial", "class": "polynomial"},
        "b_tree": {"complexity": "polynomial", "class": "polynomial"},
        "binomial_heap": {"complexity": "polynomial", "class": "polynomial"},
        "fibonacci_heap": {"complexity": "polynomial", "class": "polynomial"},
        "mst": {"complexity": "polynomial", "class": "polynomial"},
        "floyd_warshall": {"complexity": "polynomial", "class": "polynomial"},
        "fractional_knapsack": {"complexity": "polynomial", "class": "polynomial"},
        "zero_one_knapsack": {"complexity": "pseudo_polynomial", "class": "pseudo_polynomial"},
        "matrix_chain": {"complexity": "polynomial", "class": "polynomial"},
        "hamiltonian": {"complexity": "np_complete", "class": "np_complete"},
        "n_queens": {"complexity": "exponential", "class": "exponential"},
        "tsp": {"complexity": "np_hard", "class": "np_hard"},
    }
    return mapping.get(problem_name, {"complexity": "unknown", "class": "unknown"})


def detect_problem(scenario: Any) -> Dict[str, Any]:
    data = load_scenario(scenario)
    graph = data.get("graph") or {}
    graph_density = data.get("graph_density")
    if graph_density is None and isinstance(graph, dict):
        graph_density = compute_graph_density(graph)

    kind = str(data.get("kind", "")).lower()
    if kind in {"ordered_search", "ordered_searchable_data", "red_black_tree", "b_tree"}:
        if data.get("storage") == "disk" or data.get("disk_based"):
            return {
                "problem": "b_tree",
                "algorithm": "b_tree",
                "reason": "Disk-resident ordered data needs high fan-out index blocks to reduce page reads.",
                "complexity": classify_problem("b_tree"),
            }
        return {
            "problem": "red_black_tree",
            "algorithm": "red_black_tree",
            "reason": "In-memory ordered search with mixed insert/delete/lookups fits a balance-maintaining tree.",
            "complexity": classify_problem("red_black_tree"),
        }

    if kind in {"priority_queue", "mergeable_priority", "priority_workload"} or data.get("needs_mergeable_priority"):
        ratio = data.get("decrease_key_ratio", 0)
        merge_ratio = data.get("merge_ratio", 0)
        if ratio > merge_ratio:
            return {
                "problem": "fibonacci_heap",
                "algorithm": "fibonacci_heap",
                "reason": "Many decrease-key operations make Fibonacci Heap attractive because decrease-key is amortized O(1).",
                "complexity": classify_problem("fibonacci_heap"),
            }
        return {
            "problem": "binomial_heap",
            "algorithm": "binomial_heap",
            "reason": "A merge-heavy workload benefits from Binomial Heap's efficient union and simpler structure.",
            "complexity": classify_problem("binomial_heap"),
        }

    if kind in {"tsp", "traveling_salesperson", "traveling_salesman"} or data.get("return_to_start"):
        return {
            "problem": "tsp",
            "algorithm": "branch_and_bound",
            "reason": "The objective is a minimum complete tour, which is a classic TSP optimization problem and exact solvers use branch-and-bound.",
            "complexity": classify_problem("tsp"),
        }

    if kind in {"mst", "minimum_spanning_tree"} or graph:
        if graph_density is not None and graph_density >= 0.5:
            preferred = data.get("preferred_algorithm", "prim")
            return {
                "problem": "mst",
                "algorithm": preferred,
                "reason": "Dense graph makes Prim efficient with adjacency matrix or dense-based implementation.",
                "complexity": classify_problem("mst"),
            }
        preferred = data.get("preferred_algorithm", "kruskal")
        return {
            "problem": "mst",
            "algorithm": preferred,
            "reason": "Sparse edge set benefits from Kruskal's edge sorting and union-find structure.",
            "complexity": classify_problem("mst"),
        }

    if kind in {"floyd_warshall", "all_pairs_shortest_path"} or data.get("all_pairs_needed"):
        return {
            "problem": "floyd_warshall",
            "algorithm": "floyd_warshall",
            "reason": "The problem needs all-pairs shortest path costs in a dense graph; Floyd-Warshall is appropriate.",
            "complexity": classify_problem("floyd_warshall"),
        }

    if kind in {"knapsack", "fractional_knapsack"} or "items_divisible" in data:
        if data.get("items_divisible"):
            return {
                "problem": "fractional_knapsack",
                "algorithm": "fractional_knapsack",
                "reason": "Fractional items can be split, so the greedy ratio-based strategy is exact.",
                "complexity": classify_problem("fractional_knapsack"),
            }
        return {
            "problem": "zero_one_knapsack",
            "algorithm": "zero_one_knapsack",
            "reason": "Indivisible items require item-level decisions, so dynamic programming is the correct exact approach.",
            "complexity": classify_problem("zero_one_knapsack"),
        }

    if kind in {"matrix_chain", "matrix_chain_multiplication"} or data.get("matrix_dims"):
        return {
            "problem": "matrix_chain",
            "algorithm": "matrix_chain_multiplication",
            "reason": "Matrix dimensions specify a chain with different parenthesization costs; DP finds the best order.",
            "complexity": classify_problem("matrix_chain"),
        }

    if kind in {"hamiltonian", "hamiltonian_cycle"} or data.get("must_visit_each_vertex"):
        return {
            "problem": "hamiltonian",
            "algorithm": "backtracking",
            "reason": "Feasibility requires visiting each vertex exactly once, which is a classical backtracking search.",
            "complexity": classify_problem("hamiltonian"),
        }

    if kind in {"n_queen", "nqueens", "n_queens", "conflict_free_placement"} or data.get("grid_conflict_constraints"):
        return {
            "problem": "n_queens",
            "algorithm": "backtracking",
            "reason": "Mutually conflicting placements on a grid are modeled as non-attacking positions with a backtracking search.",
            "complexity": classify_problem("n_queens"),
        }

    if data.get("storage") == "disk":
        return {
            "problem": "b_tree",
            "algorithm": "b_tree",
            "reason": "This is a disk-based ordered search problem.",
            "complexity": classify_problem("b_tree"),
        }

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

The framework accepts a scenario, extracts problem features, selects a DAA formulation, runs the algorithm, measures performance, and explains the decision.

## Decision rules
- Ordered data + disk -> B-Tree
- Ordered data + memory -> Red-Black Tree
- Merge-heavy priority queue -> Binomial Heap
- Frequent decrease-key workload -> Fibonacci Heap
- Dense graph -> Prim
- Sparse graph -> Kruskal
- Divisible items -> Fractional Knapsack
- Indivisible items -> 0/1 Knapsack
- All-pairs cost -> Floyd-Warshall
- Matrix chain -> Dynamic programming
- Feasibility of visiting all vertices -> Hamiltonian backtracking
- Placement constraints -> N-Queen style backtracking
- Complete tour minimization -> TSP with branch and bound

## Complexity classification
- MST: polynomial
- Fractional Knapsack: polynomial
- 0/1 Knapsack: pseudo-polynomial / decision NP-Complete
- TSP: NP-Hard optimization; decision NP-Complete
- Hamiltonian cycle: NP-Complete decision
- N-Queen: exponential search, not automatically NP-Complete
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
