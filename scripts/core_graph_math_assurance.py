#!/usr/bin/env python3
"""Mathematical assurance reporting for the TENSOR Core graph."""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core_graph_pipeline import ARCHETYPES, CROSS_DOMAIN_RATIO_MIN, DECISIONS, DOMAINS, parse_version
from graph_assurance_policy import build_acceptance


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _round(value: float, digits: int = 6) -> float:
    return float(round(value, digits))


def _entropy(probabilities: list[float]) -> float:
    total = sum(probabilities)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in probabilities:
        if value <= 0:
            continue
        p = value / total
        entropy -= p * math.log2(p)
    return entropy


def _gini(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    total = sum(sorted_values)
    if total == 0:
        return 0.0
    cumulative = 0.0
    for idx, value in enumerate(sorted_values, start=1):
        cumulative += idx * value
    return _safe_div((2 * cumulative), (n * total)) - _safe_div((n + 1), n)


def _matrix_rank(matrix: list[list[float]], epsilon: float = 1e-10) -> int:
    if not matrix:
        return 0
    rows = len(matrix)
    cols = len(matrix[0]) if matrix[0] else 0
    rank = 0
    pivot_row = 0
    # Work on a copy to preserve caller-owned data.
    data = [row[:] for row in matrix]

    for col in range(cols):
        pivot = None
        for row in range(pivot_row, rows):
            if abs(data[row][col]) > epsilon:
                pivot = row
                break
        if pivot is None:
            continue

        data[pivot_row], data[pivot] = data[pivot], data[pivot_row]
        pivot_value = data[pivot_row][col]

        for j in range(col, cols):
            data[pivot_row][j] /= pivot_value

        for row in range(rows):
            if row == pivot_row:
                continue
            factor = data[row][col]
            if abs(factor) <= epsilon:
                continue
            for j in range(col, cols):
                data[row][j] -= factor * data[pivot_row][j]

        rank += 1
        pivot_row += 1
        if pivot_row == rows:
            break

    return rank


def _topological_order(node_ids: list[str], adjacency: dict[str, list[str]], indegree: dict[str, int]) -> list[str]:
    queue: deque[str] = deque(sorted([nid for nid in node_ids if indegree.get(nid, 0) == 0], key=_node_num))
    order: list[str] = []
    indegree_copy = dict(indegree)

    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for target in adjacency.get(node_id, []):
            indegree_copy[target] -= 1
            if indegree_copy[target] == 0:
                queue.append(target)

    if len(order) != len(node_ids):
        # Cyclic definitions have no topological order; bounded diagnostics use stable ID order.
        return sorted(node_ids, key=_node_num)

    return order


def _node_num(node_id: str) -> int:
    return int(node_id[1:])


def _brandes_betweenness(node_ids: list[str], adjacency: dict[str, list[str]]) -> dict[str, float]:
    betweenness = {node_id: 0.0 for node_id in node_ids}

    for source in node_ids:
        predecessors: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        sigma = {node_id: 0.0 for node_id in node_ids}
        distance = {node_id: -1 for node_id in node_ids}

        sigma[source] = 1.0
        distance[source] = 0

        queue: deque[str] = deque([source])
        stack: list[str] = []

        while queue:
            vertex = queue.popleft()
            stack.append(vertex)
            for neighbor in adjacency.get(vertex, []):
                if distance[neighbor] < 0:
                    queue.append(neighbor)
                    distance[neighbor] = distance[vertex] + 1
                if distance[neighbor] == distance[vertex] + 1:
                    sigma[neighbor] += sigma[vertex]
                    predecessors[neighbor].append(vertex)

        dependency = {node_id: 0.0 for node_id in node_ids}
        while stack:
            vertex = stack.pop()
            for predecessor in predecessors[vertex]:
                if sigma[vertex] == 0:
                    continue
                dependency[predecessor] += (sigma[predecessor] / sigma[vertex]) * (1.0 + dependency[vertex])
            if vertex != source:
                betweenness[vertex] += dependency[vertex]

    node_count = len(node_ids)
    normalization = (node_count - 1) * (node_count - 2)
    if normalization > 0:
        for node_id in node_ids:
            betweenness[node_id] /= normalization

    return betweenness


def _reachable_ratio(
    entry_ids: list[str],
    adjacency: dict[str, list[str]],
    removed_nodes: set[str],
    all_nodes: set[str],
) -> float:
    remaining_nodes = [node_id for node_id in all_nodes if node_id not in removed_nodes]
    if not remaining_nodes:
        return 0.0

    reachable: set[str] = set()
    queue: deque[str] = deque()
    for entry_id in entry_ids:
        if entry_id in removed_nodes:
            continue
        if entry_id in all_nodes and entry_id not in reachable:
            reachable.add(entry_id)
            queue.append(entry_id)

    while queue:
        node_id = queue.popleft()
        for target in adjacency.get(node_id, []):
            if target in removed_nodes:
                continue
            if target not in reachable:
                reachable.add(target)
                queue.append(target)

    return _safe_div(len(reachable), len(remaining_nodes))


def _dinic_max_flow(
    node_ids: list[str],
    edge_pairs: list[tuple[str, str]],
    entry_ids: list[str],
    terminal_ids: list[str],
) -> tuple[int, int]:
    source = "__source__"
    sink = "__sink__"
    all_ids = [source, sink, *node_ids]

    index = {node_id: idx for idx, node_id in enumerate(all_ids)}
    graph: list[list[list[int]]] = [[] for _ in all_ids]

    def add_edge(from_id: str, to_id: str, capacity: int) -> None:
        u = index[from_id]
        v = index[to_id]
        graph[u].append([v, capacity, len(graph[v])])
        graph[v].append([u, 0, len(graph[u]) - 1])

    large_capacity = max(1, len(edge_pairs) + 1)

    for from_id, to_id in edge_pairs:
        add_edge(from_id, to_id, 1)

    for entry_id in entry_ids:
        if entry_id in index:
            add_edge(source, entry_id, large_capacity)

    for terminal_id in terminal_ids:
        if terminal_id in index:
            add_edge(terminal_id, sink, large_capacity)

    source_idx = index[source]
    sink_idx = index[sink]
    node_count = len(all_ids)

    max_flow = 0
    while True:
        level = [-1] * node_count
        queue: deque[int] = deque([source_idx])
        level[source_idx] = 0

        while queue:
            u = queue.popleft()
            for v, cap, _ in graph[u]:
                if cap > 0 and level[v] < 0:
                    level[v] = level[u] + 1
                    queue.append(v)

        if level[sink_idx] < 0:
            break

        work = [0] * node_count

        def dfs(u: int, flow: int) -> int:
            if u == sink_idx:
                return flow
            while work[u] < len(graph[u]):
                edge = graph[u][work[u]]
                v, cap, rev = edge
                if cap > 0 and level[v] == level[u] + 1:
                    pushed = dfs(v, min(flow, cap))
                    if pushed > 0:
                        edge[1] -= pushed
                        graph[v][rev][1] += pushed
                        return pushed
                work[u] += 1
            return 0

        while True:
            pushed = dfs(source_idx, 10**9)
            if pushed == 0:
                break
            max_flow += pushed

    # Min-cut size from residual graph.
    reachable = [False] * node_count
    queue = deque([source_idx])
    reachable[source_idx] = True
    while queue:
        u = queue.popleft()
        for v, cap, _ in graph[u]:
            if cap > 0 and not reachable[v]:
                reachable[v] = True
                queue.append(v)

    min_cut_edges = 0
    for from_id, to_id in edge_pairs:
        if reachable[index[from_id]] and not reachable[index[to_id]]:
            min_cut_edges += 1

    return (max_flow, min_cut_edges)


def _all_paths_count(adjacency: dict[str, list[str]], topological_order: list[str], max_length: int) -> dict[int, int]:
    counts_by_length: dict[int, dict[str, int]] = {
        length: {node_id: 0 for node_id in topological_order} for length in range(1, max_length + 1)
    }

    for node_id in reversed(topological_order):
        counts_by_length[1][node_id] = len(adjacency.get(node_id, []))

    for length in range(2, max_length + 1):
        for node_id in reversed(topological_order):
            total = 0
            for target in adjacency.get(node_id, []):
                total += counts_by_length[length - 1][target]
            counts_by_length[length][node_id] = total

    return {length: sum(node_counts.values()) for length, node_counts in counts_by_length.items()}


def _evaluate_publish_gates(
    quality_metrics: dict[str, Any],
    graph_theory_metrics: dict[str, Any],
    centrality_metrics: dict[str, Any],
    robustness_metrics: dict[str, Any],
    information_metrics: dict[str, Any],
    optimization_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Historical reference thresholds only; retained without recalibration."""
    overall_score_min = 80.0
    coverage_score_min = 100.0
    routing_score_min = 100.0
    robustness_score_min = 85.0
    targeted_reachability_min = 0.85
    betweenness_centralization_max = 0.02
    negative_information_gain_max = 0

    reachable_ratio = float(graph_theory_metrics.get("reachableRatio", 0.0))
    branch_completeness_ratio = float(graph_theory_metrics.get("branchCompletenessRatio", 0.0))

    gates = [
        {
            "id": "dag_pass",
            "description": "Graph remains acyclic.",
            "metric": "graph_theory.dagPass",
            "operator": "==",
            "threshold": True,
            "value": bool(graph_theory_metrics.get("dagPass", False)),
        },
        {
            "id": "full_reachability",
            "description": "All nodes are reachable from configured entries.",
            "metric": "graph_theory.reachableRatio",
            "operator": ">=",
            "threshold": 1.0,
            "value": _round(reachable_ratio),
        },
        {
            "id": "branch_totality",
            "description": "Every non-terminal covers yes/no/unknown; multiple targets per outcome are allowed.",
            "metric": "graph_theory.branchCompletenessRatio",
            "operator": ">=",
            "threshold": 1.0,
            "value": _round(branch_completeness_ratio),
        },
        {
            "id": "cross_domain_pivots",
            "description": "Cross-domain pivot ratio meets minimum standard.",
            "metric": "quality.crossDomainRatio",
            "operator": ">=",
            "threshold": _round(CROSS_DOMAIN_RATIO_MIN),
            "value": _round(float(quality_metrics.get("crossDomainRatio", 0.0))),
        },
        {
            "id": "coverage_score",
            "description": "Domain x archetype coverage remains complete.",
            "metric": "optimization.coverageScore",
            "operator": ">=",
            "threshold": _round(coverage_score_min),
            "value": _round(float(optimization_metrics.get("coverageScore", 0.0))),
        },
        {
            "id": "routing_score",
            "description": "Routing integrity score remains maximal.",
            "metric": "optimization.routingScore",
            "operator": ">=",
            "threshold": _round(routing_score_min),
            "value": _round(float(optimization_metrics.get("routingScore", 0.0))),
        },
        {
            "id": "robustness_score",
            "description": "Overall robustness score stays above baseline.",
            "metric": "optimization.robustnessScore",
            "operator": ">=",
            "threshold": _round(robustness_score_min),
            "value": _round(float(optimization_metrics.get("robustnessScore", 0.0))),
        },
        {
            "id": "targeted_resilience",
            "description": "Reachability under 5% targeted removal stays above baseline.",
            "metric": "robustness.targetedReachabilityAt5Percent",
            "operator": ">=",
            "threshold": _round(targeted_reachability_min),
            "value": _round(float(robustness_metrics.get("targetedReachabilityAt5Percent", 0.0))),
        },
        {
            "id": "routing_centralization",
            "description": "Betweenness centralization stays below concentration threshold.",
            "metric": "centrality.betweennessCentralization",
            "operator": "<=",
            "threshold": _round(betweenness_centralization_max),
            "value": _round(float(centrality_metrics.get("betweennessCentralization", 0.0))),
        },
        {
            "id": "information_gain",
            "description": "No nodes regress to negative information gain.",
            "metric": "information_theory.negativeInformationGainNodeCount",
            "operator": "<=",
            "threshold": negative_information_gain_max,
            "value": int(information_metrics.get("negativeInformationGainNodeCount", 0)),
        },
        {
            "id": "overall_score",
            "description": "Composite optimization score remains publishable.",
            "metric": "optimization.overallScore",
            "operator": ">=",
            "threshold": _round(overall_score_min),
            "value": _round(float(optimization_metrics.get("overallScore", 0.0))),
        },
    ]

    for gate in gates:
        operator = gate["operator"]
        threshold = gate["threshold"]
        value = gate["value"]
        if operator == ">=":
            gate["passed"] = bool(value >= threshold)
        elif operator == "<=":
            gate["passed"] = bool(value <= threshold)
        elif operator == "==":
            gate["passed"] = bool(value == threshold)
        else:
            gate["passed"] = False

    failed_gate_ids = [gate["id"] for gate in gates if not gate["passed"]]
    return {
        "allPassed": len(failed_gate_ids) == 0,
        "failedGateIds": failed_gate_ids,
        "gates": gates,
    }


def build_math_assurance_payload(
    version: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    entry_node_ids: list[str],
    quality_metrics: dict[str, Any],
) -> dict[str, Any]:
    parse_version(version)

    node_by_id = {node["id"]: node for node in nodes}
    node_ids = sorted(node_by_id.keys(), key=_node_num)
    all_nodes = set(node_ids)

    outgoing_decisions: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    adjacency: dict[str, list[str]] = defaultdict(list)
    reverse_adjacency: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {node_id: 0 for node_id in node_ids}

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        decision = edge["decision"]
        outgoing_decisions[source][decision].append(target)
        adjacency[source].append(target)
        reverse_adjacency[target].append(source)
        indegree[target] = indegree.get(target, 0) + 1

    terminals = [node_id for node_id in node_ids if len(outgoing_decisions.get(node_id, {})) == 0]
    nonterminals = [node_id for node_id in node_ids if len(outgoing_decisions.get(node_id, {})) > 0]
    topological_order = _topological_order(node_ids, adjacency, indegree)

    domain_index = {domain: idx for idx, domain in enumerate(DOMAINS)}
    archetype_index = {archetype: idx for idx, archetype in enumerate(ARCHETYPES)}

    # 1) Graph theory
    branch_complete = 0
    deterministic_conflicts = 0
    for node_id in nonterminals:
        decision_map = outgoing_decisions.get(node_id, {})
        if set(decision_map.keys()) == set(DECISIONS):
            branch_complete += 1
        for decision in DECISIONS:
            if decision not in decision_map:
                deterministic_conflicts += 1

    roots = [node_id for node_id in node_ids if indegree.get(node_id, 0) == 0]

    graph_theory_metrics = {
        "nodeCount": len(node_ids),
        "edgeCount": len(edges),
        "rootCount": len(roots),
        "terminalCount": len(terminals),
        "nonTerminalCount": len(nonterminals),
        "branchCompletenessRatio": _round(_safe_div(branch_complete, max(1, len(nonterminals)))),
        "deterministicDecisionGapCount": deterministic_conflicts,
        "reachableRatio": _round(_safe_div(quality_metrics.get("reachableNodeCount", 0), max(1, len(node_ids)))),
        "dagPass": bool(quality_metrics.get("dagPass", False)),
    }

    # 2) Matrix theory coverage
    matrix: list[list[float]] = [[0.0 for _ in ARCHETYPES] for _ in DOMAINS]
    for node in nodes:
        matrix[domain_index[node["category"]]][archetype_index[node["archetype"]]] += 1.0

    nonzero_cells = 0
    for row in matrix:
        for value in row:
            if value > 0:
                nonzero_cells += 1

    row_entropy: dict[str, float] = {}
    col_entropy: dict[str, float] = {}

    for domain, idx in domain_index.items():
        entropy = _entropy(matrix[idx])
        row_entropy[domain] = _round(_safe_div(entropy, math.log2(len(ARCHETYPES))))

    for archetype, idx in archetype_index.items():
        column = [matrix[row_idx][idx] for row_idx in range(len(DOMAINS))]
        entropy = _entropy(column)
        col_entropy[archetype] = _round(_safe_div(entropy, math.log2(len(DOMAINS))))

    matrix_theory_metrics = {
        "matrixRows": len(DOMAINS),
        "matrixColumns": len(ARCHETYPES),
        "matrixRank": _matrix_rank(matrix),
        "nonZeroCellRatio": _round(_safe_div(nonzero_cells, len(DOMAINS) * len(ARCHETYPES))),
        "rowEntropyNormalized": row_entropy,
        "columnEntropyNormalized": col_entropy,
    }

    # 3) Set cover / hitting set (entry minimization for domain-archetype coverage)
    universe = {
        (node["category"], node["archetype"])
        for node in nodes
    }

    entry_sets: dict[str, set[tuple[str, str]]] = {}
    for entry_id in entry_node_ids:
        if entry_id not in node_by_id:
            continue
        visited: set[str] = set([entry_id])
        queue: deque[str] = deque([entry_id])
        covered: set[tuple[str, str]] = set()
        while queue:
            current = queue.popleft()
            current_node = node_by_id[current]
            covered.add((current_node["category"], current_node["archetype"]))
            for target in adjacency.get(current, []):
                if target not in visited:
                    visited.add(target)
                    queue.append(target)
        entry_sets[entry_id] = covered

    greedy_selected: list[str] = []
    covered_pairs: set[tuple[str, str]] = set()
    remaining_entries = set(entry_sets.keys())
    while covered_pairs != universe and remaining_entries:
        best_entry = None
        best_gain = -1
        for entry_id in sorted(remaining_entries, key=_node_num):
            gain = len(entry_sets[entry_id] - covered_pairs)
            if gain > best_gain:
                best_gain = gain
                best_entry = entry_id
        if best_entry is None or best_gain <= 0:
            break
        greedy_selected.append(best_entry)
        covered_pairs |= entry_sets[best_entry]
        remaining_entries.remove(best_entry)

    set_cover_metrics = {
        "universeSize": len(universe),
        "configuredEntryCount": len(entry_node_ids),
        "minimalEntrySetSizeByGreedy": len(greedy_selected),
        "greedyEntrySet": greedy_selected,
        "entryCoverageRatio": _round(_safe_div(len(covered_pairs), max(1, len(universe)))),
        "entryRedundancyRatio": _round(1.0 - _safe_div(len(greedy_selected), max(1, len(entry_node_ids)))),
    }

    # 4) Markov chain analysis (uniform branch probabilities)
    decision_probability = {"yes": 1.0 / 3.0, "no": 1.0 / 3.0, "unknown": 1.0 / 3.0}

    expected_steps = {node_id: 0.0 for node_id in node_ids}
    terminal_domain_distribution = {node_id: [0.0 for _ in DOMAINS] for node_id in node_ids}
    for node_id in terminals:
        terminal_domain_distribution[node_id][domain_index[node_by_id[node_id]["category"]]] = 1.0
    # Exact DAG diagnostic; for cyclic definitions this is an explicitly bounded
    # 64-step random-walk proxy, not a termination or investigation claim.
    rounds = 1 if quality_metrics.get("dagPass") else 64
    for _ in range(rounds):
        previous_steps = dict(expected_steps)
        previous_distributions = {nid: list(d) for nid, d in terminal_domain_distribution.items()}
        for node_id in reversed(topological_order):
            if node_id in terminals:
                continue
            decisions = outgoing_decisions[node_id]
            available = [decision for decision in DECISIONS if decision in decisions]
            total_weight = sum(decision_probability[decision] for decision in available)
            if not total_weight:
                continue
            step_expectation, distribution = 1.0, [0.0 for _ in DOMAINS]
            for decision in available:
                targets = decisions[decision]
                weight = decision_probability[decision] / total_weight / len(targets)
                for target in targets:
                    step_expectation += weight * (expected_steps if rounds == 1 else previous_steps)[target]
                    for idx, value in enumerate((terminal_domain_distribution if rounds == 1 else previous_distributions)[target]):
                        distribution[idx] += weight * value
            expected_steps[node_id] = step_expectation
            terminal_domain_distribution[node_id] = distribution

    entry_expected_steps = [expected_steps[entry_id] for entry_id in entry_node_ids if entry_id in expected_steps]
    if entry_expected_steps:
        sorted_steps = sorted(entry_expected_steps)
        markov_expected_median = sorted_steps[len(sorted_steps) // 2]
        markov_expected_p90 = sorted_steps[int(0.9 * (len(sorted_steps) - 1))]
    else:
        markov_expected_median = 0.0
        markov_expected_p90 = 0.0

    aggregate_entry_distribution = [0.0 for _ in DOMAINS]
    valid_entries = [entry_id for entry_id in entry_node_ids if entry_id in terminal_domain_distribution]
    if valid_entries:
        for entry_id in valid_entries:
            distribution = terminal_domain_distribution[entry_id]
            for idx, value in enumerate(distribution):
                aggregate_entry_distribution[idx] += value
        aggregate_entry_distribution = [value / len(valid_entries) for value in aggregate_entry_distribution]

    markov_metrics = {
        "decisionProbabilityModel": decision_probability,
        "scope": "Topology diagnostic only: uniform outcomes, uniform target choice within an outcome; does not model concurrent selection.",
        "boundedWalkHorizon": None if rounds == 1 else 64,
        "expectedStepsFromEntriesMean": _round(_safe_div(sum(entry_expected_steps), max(1, len(entry_expected_steps)))),
        "expectedStepsFromEntriesMedian": _round(markov_expected_median),
        "expectedStepsFromEntriesP90": _round(markov_expected_p90),
        "absorptionDomainDistribution": {
            domain: _round(aggregate_entry_distribution[domain_index[domain]]) for domain in DOMAINS
        },
        "absorptionDomainEntropy": _round(_entropy(aggregate_entry_distribution)),
    }

    # 5) Information theory (uncertainty reduction)
    node_entropy: dict[str, float] = {
        node_id: _entropy(terminal_domain_distribution[node_id]) for node_id in node_ids
    }

    info_gain_values: list[float] = []
    negative_info_gain_nodes: list[str] = []
    for node_id in nonterminals:
        decisions = outgoing_decisions[node_id]
        available = [decision for decision in DECISIONS if decision in decisions]
        total_weight = sum(decision_probability[decision] for decision in available)
        expected_child_entropy = 0.0
        for decision in available:
            weight = decision_probability[decision] / total_weight
            expected_child_entropy += weight * sum(node_entropy[target] for target in decisions[decision]) / len(decisions[decision])
        info_gain = node_entropy[node_id] - expected_child_entropy
        info_gain_values.append(info_gain)
        if info_gain < -1e-9:
            negative_info_gain_nodes.append(node_id)

    sorted_info = sorted(info_gain_values)
    information_metrics = {
        "entryEntropy": _round(_safe_div(sum(node_entropy.get(entry_id, 0.0) for entry_id in valid_entries), max(1, len(valid_entries)))),
        "meanInformationGain": _round(_safe_div(sum(info_gain_values), max(1, len(info_gain_values)))),
        "medianInformationGain": _round(sorted_info[len(sorted_info) // 2] if sorted_info else 0.0),
        "p90InformationGain": _round(sorted_info[int(0.9 * (len(sorted_info) - 1))] if sorted_info else 0.0),
        "negativeInformationGainNodeCount": len(negative_info_gain_nodes),
        "negativeInformationGainSample": sorted(negative_info_gain_nodes, key=_node_num)[:10],
    }

    # 6) Flow and cut theory
    edge_pairs = [(edge["source"], edge["target"]) for edge in edges]
    max_flow, min_cut_edge_count = _dinic_max_flow(node_ids, edge_pairs, valid_entries, terminals)

    undirected_neighbors: dict[str, set[str]] = defaultdict(set)
    for source, target in edge_pairs:
        undirected_neighbors[source].add(target)
        undirected_neighbors[target].add(source)

    # Articulation points via Tarjan on undirected projection.
    articulation_points: set[str] = set()
    discovery: dict[str, int] = {}
    low: dict[str, int] = {}
    time_counter = 0

    def dfs_articulation(current: str, parent: str | None) -> None:
        nonlocal time_counter
        discovery[current] = time_counter
        low[current] = time_counter
        time_counter += 1
        children = 0

        for neighbor in sorted(undirected_neighbors.get(current, []), key=_node_num):
            if neighbor == parent:
                continue
            if neighbor not in discovery:
                children += 1
                dfs_articulation(neighbor, current)
                low[current] = min(low[current], low[neighbor])
                if parent is not None and low[neighbor] >= discovery[current]:
                    articulation_points.add(current)
            else:
                low[current] = min(low[current], discovery[neighbor])

        if parent is None and children > 1:
            articulation_points.add(current)

    for node_id in node_ids:
        if node_id not in discovery:
            dfs_articulation(node_id, None)

    flow_cut_metrics = {
        "entryToTerminalEdgeConnectivity": max_flow,
        "entryToTerminalMinCutEdgeCount": min_cut_edge_count,
        "articulationPointCountUndirectedProjection": len(articulation_points),
        "articulationPointSample": sorted(articulation_points, key=_node_num)[:10],
    }

    # 7) Centrality theory
    betweenness = _brandes_betweenness(node_ids, adjacency)
    sorted_betweenness = sorted(betweenness.items(), key=lambda item: (-item[1], _node_num(item[0])))

    centrality_metrics = {
        "betweennessTop10": [
            {
                "nodeId": node_id,
                "category": node_by_id[node_id]["category"],
                "archetype": node_by_id[node_id]["archetype"],
                "score": _round(score),
            }
            for node_id, score in sorted_betweenness[:10]
        ],
        "betweennessCentralization": _round(
            _safe_div(sorted_betweenness[0][1] if sorted_betweenness else 0.0, sum(score for _, score in sorted_betweenness))
        ),
        "betweennessGini": _round(_gini([score for _, score in sorted_betweenness])),
    }

    # 8) Robustness / percolation
    candidate_targeted = [
        node_id
        for node_id, _ in sorted_betweenness
        if node_id not in set(valid_entries)
    ]

    fractions = [0.01, 0.03, 0.05, 0.1]
    randomizer = random.Random(42)

    targeted_curve: list[dict[str, Any]] = []
    random_curve: list[dict[str, Any]] = []

    for fraction in fractions:
        removal_count = max(1, int(round(len(node_ids) * fraction)))

        targeted_removed = set(candidate_targeted[:removal_count])
        targeted_ratio = _reachable_ratio(valid_entries, adjacency, targeted_removed, all_nodes)
        targeted_curve.append(
            {
                "fractionRemoved": fraction,
                "removedCount": removal_count,
                "reachableRatio": _round(targeted_ratio),
            }
        )

        random_trials = 25
        trial_values: list[float] = []
        for _ in range(random_trials):
            removed = set(randomizer.sample(node_ids, k=min(removal_count, len(node_ids))))
            trial_values.append(_reachable_ratio(valid_entries, adjacency, removed, all_nodes))

        mean_value = _safe_div(sum(trial_values), max(1, len(trial_values)))
        variance = _safe_div(sum((value - mean_value) ** 2 for value in trial_values), max(1, len(trial_values)))
        random_curve.append(
            {
                "fractionRemoved": fraction,
                "removedCount": removal_count,
                "reachableRatioMean": _round(mean_value),
                "reachableRatioStdDev": _round(math.sqrt(variance)),
            }
        )

    targeted_at_5 = next((item["reachableRatio"] for item in targeted_curve if abs(item["fractionRemoved"] - 0.05) < 1e-9), 0.0)

    robustness_metrics = {
        "targetedRemovalCurve": targeted_curve,
        "randomRemovalCurve": random_curve,
        "targetedReachabilityAt5Percent": _round(targeted_at_5),
    }

    # 9) Multi-objective optimization scorecard
    coverage_score = 100.0 * matrix_theory_metrics["nonZeroCellRatio"]
    routing_score = 100.0 * (
        0.35 * graph_theory_metrics["branchCompletenessRatio"]
        + 0.35 * graph_theory_metrics["reachableRatio"]
        + 0.20 * min(1.0, _safe_div(quality_metrics.get("crossDomainRatio", 0.0), quality_metrics.get("crossDomainRatioMin", 0.25)))
        + 0.10 * (1.0 if graph_theory_metrics["dagPass"] else 0.0)
    )

    entry_entropy = information_metrics["entryEntropy"]
    info_score = 100.0 * min(1.0, _safe_div(max(0.0, information_metrics["meanInformationGain"]), max(1e-9, entry_entropy)))
    robustness_score = 100.0 * robustness_metrics["targetedReachabilityAt5Percent"]

    overall_score = 0.30 * coverage_score + 0.30 * routing_score + 0.20 * info_score + 0.20 * robustness_score

    # Numerical formulas above are preserved for comparisons with prior receipts.
    # Interpretation and current acceptance no longer treat these scores as proof.
    recommendations: list[str] = [
        "Use explicit evidence cards, safe transition checks and discriminating scenarios for authoring acceptance; topology scores do not establish investigative quality.",
        "Review high-betweenness questions and removal sensitivity for maintenance impact; never bypass required evidence validation to improve a score.",
    ]
    if matrix_theory_metrics["nonZeroCellRatio"] < 1.0:
        recommendations.append("Add nodes for missing Domain x Archetype cells to maintain complete investigative coverage.")
    if graph_theory_metrics["rootCount"] > len(valid_entries):
        recommendations.append("Reduce implicit roots by connecting isolated chains to explicit entry pathways.")

    optimization_metrics = {
        "coverageScore": _round(coverage_score),
        "routingScore": _round(routing_score),
        "informationScore": _round(info_score),
        "robustnessScore": _round(robustness_score),
        "overallScore": _round(overall_score),
        "recommendations": recommendations,
    }

    publish_gates = _evaluate_publish_gates(
        quality_metrics=quality_metrics,
        graph_theory_metrics=graph_theory_metrics,
        centrality_metrics=centrality_metrics,
        robustness_metrics=robustness_metrics,
        information_metrics=information_metrics,
        optimization_metrics=optimization_metrics,
    )

    # 10) Formal-method style property checks
    terminal_archetypes = {"terminal"}
    terminal_archetype_nodes = {
        node_id for node_id in node_ids if node_by_id[node_id]["archetype"] in terminal_archetypes
    }
    can_reach_terminal: dict[str, bool] = {node_id: False for node_id in node_ids}

    terminal_queue = deque(terminal_archetype_nodes)
    for node_id in terminal_archetype_nodes: can_reach_terminal[node_id] = True
    while terminal_queue:
        target = terminal_queue.popleft()
        for source in reverse_adjacency.get(target, []):
            if not can_reach_terminal[source]:
                can_reach_terminal[source] = True
                terminal_queue.append(source)

    formal_metrics = {
        "AG_branchTotality": graph_theory_metrics["branchCompletenessRatio"] == 1.0,
        "AG_acyclic": graph_theory_metrics["dagPass"],
        "AG_reachabilityFromEntries": graph_theory_metrics["reachableRatio"] == 1.0,
        "AG_entryEventuallyTerminal": all(can_reach_terminal.get(entry_id, False) for entry_id in valid_entries),
        "AG_terminalsAreTerminalArchetype": all(
            node_by_id[node_id]["archetype"] in terminal_archetypes for node_id in terminals
        ),
    }

    # 11) Bayesian / causal readiness proxies
    domain_archetype_presence = {
        domain: {
            archetype: matrix[domain_index[domain]][archetype_index[archetype]] > 0
            for archetype in ARCHETYPES
        }
        for domain in DOMAINS
    }
    full_chain_domains = [
        domain for domain in DOMAINS if all(domain_archetype_presence[domain][archetype] for archetype in ARCHETYPES)
    ]

    triangulation_nodes = 0
    corroborated_nodes = 0
    corroboration_candidates = 0
    causal_progression_edges = 0

    for node_id in nonterminals:
        target_domains = {node_by_id[target]["category"] for targets in outgoing_decisions[node_id].values() for target in targets}
        if len(target_domains) >= 2:
            triangulation_nodes += 1

    for node_id in node_ids:
        node = node_by_id[node_id]
        if node["archetype"] in {"classify", "scope", "correlate", "attribute"}:
            corroboration_candidates += 1
            source_domains = {node_by_id[source]["category"] for source in reverse_adjacency.get(node_id, [])}
            if len(source_domains) >= 2:
                corroborated_nodes += 1

    for edge in edges:
        source_arch = node_by_id[edge["source"]]["archetype"]
        target_arch = node_by_id[edge["target"]]["archetype"]
        if archetype_index[target_arch] >= archetype_index[source_arch]:
            causal_progression_edges += 1

    bayesian_causal_metrics = {
        "fullArchetypeChainDomainCount": len(full_chain_domains),
        "fullArchetypeChainDomains": full_chain_domains,
        "triangulationNodeRatio": _round(_safe_div(triangulation_nodes, max(1, len(nonterminals)))),
        "crossSourceCorroborationRatio": _round(_safe_div(corroborated_nodes, max(1, corroboration_candidates))),
        "causalProgressionEdgeRatio": _round(_safe_div(causal_progression_edges, max(1, len(edges)))),
    }

    # 12) Directed topology / path-complex proxies
    path_counts = _all_paths_count(adjacency, topological_order, max_length=4)

    merge_nodes = 0
    merge_nodes_cross_domain = 0
    for node_id in node_ids:
        incoming_sources = reverse_adjacency.get(node_id, [])
        if len(incoming_sources) >= 2:
            merge_nodes += 1
            source_domains = {node_by_id[source]["category"] for source in incoming_sources}
            if len(source_domains) >= 2:
                merge_nodes_cross_domain += 1

    diamond_motifs = 0
    for source in node_ids:
        two_step_targets: Counter[str] = Counter()
        for mid in adjacency.get(source, []):
            for target in adjacency.get(mid, []):
                two_step_targets[target] += 1
        for count in two_step_targets.values():
            if count >= 2:
                diamond_motifs += count * (count - 1) // 2

    path_topology_metrics = {
        "directedPathCounts": {
            f"length{length}": path_counts.get(length, 0) for length in range(1, 5)
        },
        "pathGrowthRatios": {
            "l2_over_l1": _round(_safe_div(path_counts.get(2, 0), max(1, path_counts.get(1, 0)))),
            "l3_over_l2": _round(_safe_div(path_counts.get(3, 0), max(1, path_counts.get(2, 0)))),
            "l4_over_l3": _round(_safe_div(path_counts.get(4, 0), max(1, path_counts.get(3, 0)))),
        },
        "mergeNodeCount": merge_nodes,
        "crossDomainMergeNodeCount": merge_nodes_cross_domain,
        "diamondMotifCount": diamond_motifs,
    }

    theories = [
        {
            "id": "graph_theory",
            "name": "Graph Theory",
            "purpose": "Structural soundness: DAG, reachability, deterministic decision routing.",
            "metrics": graph_theory_metrics,
        },
        {
            "id": "matrix_theory",
            "name": "Matrix Theory",
            "purpose": "Coverage completeness and balance across Domain x Archetype.",
            "metrics": matrix_theory_metrics,
        },
        {
            "id": "set_cover",
            "name": "Set Cover / Hitting Set",
            "purpose": "Minimal entry-path basis required to cover investigative feature space.",
            "metrics": set_cover_metrics,
        },
        {
            "id": "markov_chain",
            "name": "Markov Chain",
            "purpose": "Expected routing length and absorbing-outcome distribution under branch probabilities.",
            "metrics": markov_metrics,
        },
        {
            "id": "information_theory",
            "name": "Information Theory",
            "purpose": "Terminal-domain label entropy under uniform branches; not evidentiary uncertainty reduction.",
            "metrics": information_metrics,
        },
        {
            "id": "flow_cut",
            "name": "Flow / Cut Theory",
            "purpose": "Bottleneck and fault-tolerance identification via connectivity cuts.",
            "metrics": flow_cut_metrics,
        },
        {
            "id": "centrality",
            "name": "Centrality Theory",
            "purpose": "Shortest-path betweenness and maximum share of total betweenness; not normalized Freeman graph centralization.",
            "metrics": centrality_metrics,
        },
        {
            "id": "robustness",
            "name": "Robustness / Percolation",
            "purpose": "Synthetic reachability after deleting questions; not missing-evidence handling or permission to bypass a prerequisite.",
            "metrics": robustness_metrics,
        },
        {
            "id": "optimization",
            "name": "Multi-objective Optimization",
            "purpose": "Historical weighted proxy scorecard; uncalibrated and not an acceptance criterion.",
            "metrics": optimization_metrics,
        },
        {
            "id": "formal_methods",
            "name": "Formal Methods Checks",
            "purpose": "Machine-checkable invariants for safety and liveness-style properties.",
            "metrics": formal_metrics,
        },
        {
            "id": "bayesian_causal",
            "name": "Bayesian / Causal Readiness",
            "purpose": "Readiness proxies for probabilistic confidence and causal interpretation overlays.",
            "metrics": bayesian_causal_metrics,
        },
        {
            "id": "directed_topology",
            "name": "Directed Topology Proxies",
            "purpose": "Higher-order path-complex and merge-pattern shape indicators.",
            "metrics": path_topology_metrics,
        },
    ]

    return {
        "version": version,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "overallScore": _round(overall_score),
            "coverageScore": _round(coverage_score),
            "routingScore": _round(routing_score),
            "informationScore": _round(info_score),
            "robustnessScore": _round(robustness_score),
            "recommendations": recommendations,
        },
        "theories": theories,
        "monitoring": {
            "artifactPathTemplate": "releases/core/reports/v<VER>/math-assurance.json",
            "latestArtifactPath": "releases/core/reports/latest/math-assurance.json",
            "historyArtifactPath": "releases/core/reports/history/math-assurance-history.json",
            "manifestLookup": "releases/manifest.json -> latestGraphVersion",
            "legacyReferenceThresholds": publish_gates,
            "publishGates": build_acceptance([], publish_gates),
        },
    }


def build_math_assurance_markdown(payload: dict[str, Any]) -> str:
    version = payload.get("version", "unknown")
    summary = payload.get("summary", {})
    theories = payload.get("theories", [])

    sections: list[str] = []
    sections.append(f"# Core Math Assurance ({version})")
    sections.append("")
    sections.append(f"Generated: `{payload.get('generatedAt', '')}`")
    sections.append("")

    sections.append("## Scorecard")
    sections.append("| Metric | Value |")
    sections.append("| --- | --- |")
    sections.append(f"| Overall score | {summary.get('overallScore', 0):.2f} |")
    sections.append(f"| Coverage score | {summary.get('coverageScore', 0):.2f} |")
    sections.append(f"| Routing score | {summary.get('routingScore', 0):.2f} |")
    sections.append(f"| Information score | {summary.get('informationScore', 0):.2f} |")
    sections.append(f"| Robustness score | {summary.get('robustnessScore', 0):.2f} |")
    sections.append("")

    monitoring = payload.get("monitoring", {})
    publish_gates = monitoring.get("publishGates", {}) if isinstance(monitoring, dict) else {}
    if isinstance(publish_gates, dict):
        sections.append("## Authoring Acceptance")
        sections.append("Structure and supplied evidence-profile checks only; not release authorization or independent investigative validation.")
        sections.append(f"Overall: **{'PASS' if publish_gates.get('allPassed') else 'FAIL'}**")
        sections.append("")
        sections.append("| Gate | Metric | Rule | Value | Result |")
        sections.append("| --- | --- | --- | --- | --- |")
        for gate in publish_gates.get("gates", []):
            if not isinstance(gate, dict):
                continue
            value = gate.get("value", gate.get("passed"))
            if isinstance(value, float):
                value_rendered = f"{value:.6f}".rstrip("0").rstrip(".")
            else:
                value_rendered = str(value)
            sections.append(
                "| "
                + " | ".join(
                    [
                        str(gate.get("id", "")),
                        str(gate.get("metric", "")),
                        f"{gate.get('operator', '')} {gate.get('threshold', '')}" if "operator" in gate else str(gate.get("status", "notRun")),
                        value_rendered,
                        "pass" if gate.get("passed") else "fail",
                    ]
                )
                + " |"
            )
        sections.append("")

    reference = monitoring.get("legacyReferenceThresholds", {})
    sections.append("## Historical Reference Thresholds (diagnostic)")
    sections.append("Original values and thresholds are retained; unmet reference thresholds do not block current authoring acceptance. See standards/graph-assurance-policy.md.")
    sections.append("| Reference | Value | Rule | Met |")
    sections.append("| --- | --- | --- | --- |")
    for item in reference.get("gates", []):
        sections.append(f"| {item['id']} | {item['value']} | {item['operator']} {item['threshold']} | {item['passed']} |")
    sections.append("")

    sections.append("## Recommendations")
    for recommendation in summary.get("recommendations", []):
        sections.append(f"- {recommendation}")
    sections.append("")

    sections.append("## Theory Coverage")
    sections.append("| Theory | Purpose |")
    sections.append("| --- | --- |")
    for theory in theories:
        sections.append(f"| {theory.get('name', '')} | {theory.get('purpose', '')} |")
    sections.append("")

    sections.append("## Key Metrics")
    key_map = {
        "Graph Theory": ["branchCompletenessRatio", "reachableRatio", "rootCount", "dagPass"],
        "Matrix Theory": ["matrixRank", "nonZeroCellRatio"],
        "Set Cover / Hitting Set": ["configuredEntryCount", "minimalEntrySetSizeByGreedy", "entryCoverageRatio"],
        "Markov Chain": ["expectedStepsFromEntriesMean", "expectedStepsFromEntriesP90", "absorptionDomainEntropy"],
        "Information Theory": ["meanInformationGain", "negativeInformationGainNodeCount"],
        "Flow / Cut Theory": ["entryToTerminalEdgeConnectivity", "entryToTerminalMinCutEdgeCount"],
        "Centrality Theory": ["betweennessCentralization", "betweennessGini"],
        "Robustness / Percolation": ["targetedReachabilityAt5Percent"],
        "Multi-objective Optimization": ["overallScore"],
        "Formal Methods Checks": ["AG_branchTotality", "AG_acyclic", "AG_entryEventuallyTerminal"],
        "Bayesian / Causal Readiness": ["fullArchetypeChainDomainCount", "triangulationNodeRatio"],
        "Directed Topology Proxies": ["mergeNodeCount", "diamondMotifCount"],
    }

    for theory in theories:
        theory_name = theory.get("name", "")
        metrics = theory.get("metrics", {})
        keys = key_map.get(theory_name, [])
        if not keys:
            continue
        sections.append(f"### {theory_name}")
        sections.append("| Metric | Value |")
        sections.append("| --- | --- |")
        for key in keys:
            value = metrics.get(key)
            if isinstance(value, float):
                rendered = f"{value:.6f}".rstrip("0").rstrip(".")
            else:
                rendered = json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
            sections.append(f"| {key} | {rendered} |")
        sections.append("")

    return "\n".join(sections).rstrip() + "\n"


def build_math_assurance_history_payload(reports_root: Path) -> dict[str, Any]:
    version_entries: list[dict[str, Any]] = []

    for report_path in sorted(reports_root.glob("v*/math-assurance.json")):
        version = report_path.parent.name[1:] if report_path.parent.name.startswith("v") else report_path.parent.name
        try:
            parse_version(version)
        except Exception:
            continue

        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        summary = payload.get("summary", {})
        theories = payload.get("theories", [])
        theory_index = {theory.get("id"): theory.get("metrics", {}) for theory in theories if isinstance(theory, dict)}
        monitoring = payload.get("monitoring", {}) if isinstance(payload.get("monitoring"), dict) else {}
        publish_gates = (
            monitoring.get("publishGates")
            if isinstance(monitoring.get("publishGates"), dict)
            else {}
        )
        failed_gate_ids = publish_gates.get("failedGateIds", [])
        if not isinstance(failed_gate_ids, list):
            failed_gate_ids = []

        graph_metrics = theory_index.get("graph_theory", {})
        robustness_metrics = theory_index.get("robustness", {})
        info_metrics = theory_index.get("information_theory", {})

        version_entries.append(
            {
                "version": version,
                "generatedAt": payload.get("generatedAt"),
                "overallScore": summary.get("overallScore", 0.0),
                "coverageScore": summary.get("coverageScore", 0.0),
                "routingScore": summary.get("routingScore", 0.0),
                "informationScore": summary.get("informationScore", 0.0),
                "robustnessScore": summary.get("robustnessScore", 0.0),
                "reachableRatio": graph_metrics.get("reachableRatio", 0.0),
                "branchCompletenessRatio": graph_metrics.get("branchCompletenessRatio", 0.0),
                "targetedReachabilityAt5Percent": robustness_metrics.get("targetedReachabilityAt5Percent", 0.0),
                "meanInformationGain": info_metrics.get("meanInformationGain", 0.0),
                "publishReady": publish_gates.get("allPassed"),
                "failedGateCount": len(failed_gate_ids),
                "failedGateIds": failed_gate_ids,
            }
        )

    version_entries.sort(key=lambda item: parse_version(item["version"]))

    deltas: list[dict[str, Any]] = []
    for idx in range(1, len(version_entries)):
        previous = version_entries[idx - 1]
        current = version_entries[idx]
        deltas.append(
            {
                "fromVersion": previous["version"],
                "toVersion": current["version"],
                "overallScoreDelta": _round(current["overallScore"] - previous["overallScore"]),
                "coverageScoreDelta": _round(current["coverageScore"] - previous["coverageScore"]),
                "routingScoreDelta": _round(current["routingScore"] - previous["routingScore"]),
                "informationScoreDelta": _round(current["informationScore"] - previous["informationScore"]),
                "robustnessScoreDelta": _round(current["robustnessScore"] - previous["robustnessScore"]),
            }
        )

    return {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series": version_entries,
        "deltas": deltas,
    }


def build_math_assurance_history_markdown(payload: dict[str, Any]) -> str:
    series = payload.get("series", [])
    deltas = payload.get("deltas", [])

    sections: list[str] = []
    sections.append("# Core Math Assurance History")
    sections.append("")
    sections.append(f"Generated: `{payload.get('generatedAt', '')}`")
    sections.append("")

    sections.append("## Release Series")
    sections.append(
        "| Version | Overall | Coverage | Routing | Information | Robustness | Reachability | Branch Completeness | Publish Ready | Failed Gates |"
    )
    sections.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for item in series:
        publish_ready = item.get("publishReady")
        publish_ready_rendered = "yes" if publish_ready is True else ("no" if publish_ready is False else "n/a")
        sections.append(
            "| "
            + " | ".join(
                [
                    item.get("version", ""),
                    f"{item.get('overallScore', 0):.2f}",
                    f"{item.get('coverageScore', 0):.2f}",
                    f"{item.get('routingScore', 0):.2f}",
                    f"{item.get('informationScore', 0):.2f}",
                    f"{item.get('robustnessScore', 0):.2f}",
                    f"{item.get('reachableRatio', 0):.4f}",
                    f"{item.get('branchCompletenessRatio', 0):.4f}",
                    publish_ready_rendered,
                    str(item.get("failedGateCount", 0)),
                ]
            )
            + " |"
        )

    sections.append("")
    sections.append("## Deltas")
    sections.append("| From | To | Overall delta | Coverage delta | Routing delta | Information delta | Robustness delta |")
    sections.append("| --- | --- | --- | --- | --- | --- | --- |")

    for delta in deltas:
        sections.append(
            "| "
            + " | ".join(
                [
                    delta.get("fromVersion", ""),
                    delta.get("toVersion", ""),
                    f"{delta.get('overallScoreDelta', 0):+.2f}",
                    f"{delta.get('coverageScoreDelta', 0):+.2f}",
                    f"{delta.get('routingScoreDelta', 0):+.2f}",
                    f"{delta.get('informationScoreDelta', 0):+.2f}",
                    f"{delta.get('robustnessScoreDelta', 0):+.2f}",
                ]
            )
            + " |"
        )

    sections.append("")
    return "\n".join(sections).rstrip() + "\n"
