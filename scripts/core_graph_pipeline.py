#!/usr/bin/env python3
"""Shared tooling for building and validating the TENSOR Core graph from structured sources."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

DOMAINS = [
    "Application",
    "Cloud",
    "Email",
    "File",
    "Host",
    "Identity",
    "Network",
]

ARCHETYPES = [
    "detect",
    "validate",
    "classify",
    "scope",
    "correlate",
    "attribute",
    "impact",
    "terminal",
]
ARCHETYPE_ORDER = {value: index for index, value in enumerate(ARCHETYPES)}
EARLY_POSITIVE_ARCHETYPES = {"detect", "validate"}

DECISIONS = ["yes", "no", "unknown"]
DECISION_SET = set(DECISIONS)
DECISION_ORDER = {value: index for index, value in enumerate(DECISIONS)}
CROSS_DOMAIN_RATIO_MIN = 0.25
FANIN_DEFAULT_LIMIT = 8
FANIN_EXCEPTION_LIMIT = 12
# Terminal (sink) nodes can tolerate higher fan-in because they do not introduce new branching
# options for investigators; consolidating terminal nodes reduces graph surface area.
FANIN_TERMINAL_LIMIT = 24
# Versioned, identity-specific capacities for the general evidence questions.
# These hubs replace semantically unrelated load-balanced facet routes. They
# require explicit context adapters and independent target prerequisites, checked
# by restoration_assurance. No other node receives these prospective capacities.
GENERIC_HUB_LIMITS = {
    "Q85": 9, "Q86": 9, "Q152": 11, "Q153": 10, "Q154": 10, "Q156": 12,
    "Q159": 20, "Q161": 18, "Q184": 17, "Q190": 17, "Q223": 20, "Q233": 26,
    "Q245": 9, "Q256": 10, "Q279": 9, "Q299": 9, "Q323": 16,
    "Q345": 18, "Q346": 13, "Q348": 23, "Q356": 26, "Q379": 22,
    "Q417": 27, "Q425": 27, "Q426": 27, "Q430": 24, "Q439": 30, "Q440": 27,
    "Q492": 21, "Q493": 21, "Q506": 18, "Q507": 15, "Q508": 21, "Q509": 12, "Q581": 18,
}

NODE_ID_RE = re.compile(r"^Q[1-9]\d*$")
EDGE_ID_RE = re.compile(r"^(Q[1-9]\d*)-(yes|no|unknown)-(Q[1-9]\d*)$")
VERSION_RE = re.compile(r"^(\d+)\.(\d{8})([a-z]?)$")
QUESTION_PREFIXES = ("Is ", "Was ", "Did ", "Does ", "Were ", "Have ")

BANNED_TEXT_TERMS = (
    "ticket",
    "case management",
    "case-status",
    "case status",
    "escalate",
    "approval",
    "sla",
    "run query",
    "click",
    "dashboard",
    "console",
    "playbook",
    "workflow",
    "assign owner",
)

CORE_BANNED_SEMANTIC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Core must not pre-type investigations into incident categories.
    (re.compile(r"\bphishing\b", re.IGNORECASE), "incident-type term"),
    (re.compile(r"\bbec\b", re.IGNORECASE), "incident-type term"),
    (re.compile(r"\bbusiness\s+email\s+compromise\b", re.IGNORECASE), "incident-type term"),
    (re.compile(r"\bransomware\b", re.IGNORECASE), "incident-type term"),
    (re.compile(r"\bddos\b", re.IGNORECASE), "incident-type term"),
    (re.compile(r"\binsider\s+threat\b", re.IGNORECASE), "incident-type term"),
    (re.compile(r"\bincident\s+type\b", re.IGNORECASE), "case-typing term"),
    (re.compile(r"\bcase\s+type\b", re.IGNORECASE), "case-typing term"),
    (re.compile(r"\bactionable\s+investigation\s+category\b", re.IGNORECASE), "case-typing term"),
)

GENERIC_NUMERIC_LABEL_RE = re.compile(
    r"^(Application|Cloud|Email|File|Host|Identity|Network)\s+"
    r"(detect|validate|classify|scope|correlate|attribute|impact|terminal)\s+\d+$"
)


class ValidationError(Exception):
    """Raised when source or graph validation fails."""


def node_numeric_id(node_id: str) -> int:
    if not NODE_ID_RE.fullmatch(node_id):
        raise ValueError(f"Invalid node id: {node_id}")
    return int(node_id[1:])


def edge_sort_key(edge: dict[str, Any]) -> tuple[int, int, int]:
    return (
        node_numeric_id(edge["source"]),
        DECISION_ORDER[edge["decision"]],
        node_numeric_id(edge["target"]),
    )


def parse_version(version: str) -> tuple[int, str, str]:
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise ValidationError(
            f"Version {version!r} must match <MAJOR>.<YYYYMMDD>[REV], for example '0.20260206c'."
        )
    return (int(match.group(1)), match.group(2), match.group(3) or "")


def canonical_generated_at(version: str) -> str:
    _, yyyymmdd, _ = parse_version(version)
    year = yyyymmdd[0:4]
    month = yyyymmdd[4:6]
    day = yyyymmdd[6:8]
    # Deterministic timestamp derived from version date for reproducible builds.
    return f"{year}-{month}-{day}T00:00:00Z"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        raise ValidationError(f"Missing JSONL source file: {path}")

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Invalid JSON in {path}:{line_number}: {exc.msg}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ValidationError(
                f"Each JSONL row must be an object in {path}:{line_number}."
            )
        rows.append(parsed)

    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator_line, *body_lines])


def load_entry_config(path: Path) -> tuple[list[str], list[str]]:
    if not path.is_file():
        raise ValidationError(f"Missing entry config file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValidationError(f"Entry config {path} must be a JSON object.")

    entry_node_ids = payload.get("entryNodeIds")
    fanin_exception_node_ids = payload.get("fanInExceptionNodeIds", [])

    if not isinstance(entry_node_ids, list) or not all(isinstance(value, str) for value in entry_node_ids):
        raise ValidationError("entry_nodes.json must define entryNodeIds as an array of node id strings.")

    if not isinstance(fanin_exception_node_ids, list) or not all(
        isinstance(value, str) for value in fanin_exception_node_ids
    ):
        raise ValidationError("entry_nodes.json fanInExceptionNodeIds must be an array of node id strings.")

    return (entry_node_ids, fanin_exception_node_ids)


def validate_and_measure(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    entry_node_ids: list[str],
    fanin_exception_node_ids: list[str],
    *, policy: str = "current",
) -> tuple[list[str], list[str], dict[str, Any]]:
    if policy not in ("current", "legacy"):
        raise ValueError("Unknown graph authoring policy")
    errors: list[str] = []
    warnings: list[str] = []

    node_by_id: dict[str, dict[str, Any]] = {}
    category_counts: Counter[str] = Counter()
    archetype_counts: Counter[str] = Counter()
    domain_archetype_counts: dict[str, Counter[str]] = {
        domain: Counter() for domain in DOMAINS
    }

    allowed_node_keys = {"id", "text", "label", "category", "archetype", "extensions"}
    allowed_edge_keys = {"id", "source", "target", "decision", "label", "extensions"}

    for index, node in enumerate(nodes):
        context = f"nodes[{index}]"
        keys = set(node.keys())
        extra_keys = sorted(keys - allowed_node_keys)
        missing_keys = sorted({"id", "text", "label", "category", "archetype"} - keys)
        if missing_keys:
            errors.append(f"{context} missing required keys: {', '.join(missing_keys)}")
            continue
        if extra_keys:
            errors.append(f"{context} has unsupported keys: {', '.join(extra_keys)}")

        node_id = node["id"]
        if not isinstance(node_id, str) or not NODE_ID_RE.fullmatch(node_id):
            errors.append(f"{context}.id must match Q<number> without leading zeros.")
            continue
        if node_id in node_by_id:
            errors.append(f"Duplicate node id detected: {node_id}")
            continue

        text = node["text"]
        label = node["label"]
        category = node["category"]
        archetype = node["archetype"]

        if not isinstance(text, str) or not text.strip():
            errors.append(f"{context}.text must be a non-empty string.")
        else:
            if not text.endswith("?"):
                errors.append(f"{context}.text must be phrased as a question ending with '?'.")
            if not text.startswith(QUESTION_PREFIXES):
                errors.append(
                    f"{context}.text must start with one of {QUESTION_PREFIXES} to keep question form objective."
                )
            lowered = text.lower()
            banned_hits = [term for term in BANNED_TEXT_TERMS if term in lowered]
            if banned_hits:
                errors.append(
                    f"{context}.text contains workflow/tool language not allowed in Core: {', '.join(sorted(banned_hits))}"
                )

        if not isinstance(label, str) or not label.strip():
            errors.append(f"{context}.label must be a non-empty string.")
        else:
            if GENERIC_NUMERIC_LABEL_RE.fullmatch(label.strip()):
                errors.append(
                    f"{context}.label must not be a generic numeric template; use a domain-prefixed technical signal label (for example: 'Email: Attachment evidence - Collaboration artifacts')."
                )

        # Core vs Overlay semantic contract enforcement:
        # ban incident typing / case-typing semantics from Core node text/labels.
        if isinstance(text, str) and isinstance(label, str):
            haystack = f"{text}\n{label}"
            for pattern, pattern_kind in CORE_BANNED_SEMANTIC_PATTERNS:
                if pattern.search(haystack):
                    errors.append(
                        f"{context} contains {pattern_kind} not allowed in Core (move to overlays): {pattern.pattern!r}"
                    )

        if category not in DOMAINS:
            errors.append(f"{context}.category must be one of {sorted(DOMAINS)}.")
            continue
        if isinstance(label, str):
            expected_prefix = f"{category}:"
            if not label.strip().startswith(expected_prefix):
                errors.append(f"{context}.label must start with '{expected_prefix}' for graph readability.")

        if archetype not in ARCHETYPES:
            errors.append(f"{context}.archetype must be one of {ARCHETYPES}.")

        node_by_id[node_id] = {
            "id": node_id,
            "text": text,
            "label": label,
            "category": category,
            "archetype": archetype,
            **({"extensions": node["extensions"]} if "extensions" in node else {}),
        }
        category_counts[category] += 1
        if archetype in ARCHETYPES:
            archetype_counts[archetype] += 1
            domain_archetype_counts[category][archetype] += 1

    for domain in DOMAINS:
        if category_counts.get(domain, 0) == 0:
            errors.append(f"Graph must contain at least one node in domain '{domain}'.")

    edge_by_id: set[str] = set()
    outgoing: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    incoming_count: Counter[str] = Counter()
    cross_domain_edges = 0
    yes_progression_violations = 0
    early_positive_cross_domain_violations = 0

    for index, edge in enumerate(edges):
        context = f"edges[{index}]"
        keys = set(edge.keys())
        extra_keys = sorted(keys - allowed_edge_keys)
        missing_keys = sorted({"id", "source", "target", "decision"} - keys)
        if missing_keys:
            errors.append(f"{context} missing required keys: {', '.join(missing_keys)}")
            continue
        if extra_keys:
            errors.append(f"{context} has unsupported keys: {', '.join(extra_keys)}")

        edge_id = edge["id"]
        source = edge["source"]
        target = edge["target"]
        decision = edge["decision"]

        if not isinstance(edge_id, str) or not EDGE_ID_RE.fullmatch(edge_id):
            errors.append(f"{context}.id must match Q<source>-<decision>-Q<target> format.")
            continue

        if edge_id in edge_by_id:
            errors.append(f"Duplicate edge id detected: {edge_id}")
            continue
        edge_by_id.add(edge_id)

        if not isinstance(source, str) or source not in node_by_id:
            errors.append(f"{context}.source must reference an existing node id.")
            continue
        if not isinstance(target, str) or target not in node_by_id:
            errors.append(f"{context}.target must reference an existing node id.")
            continue
        if not isinstance(decision, str) or decision not in DECISION_SET:
            errors.append(f"{context}.decision must be one of {DECISIONS}.")
            continue

        if source == target:
            errors.append(f"{context} cannot be a self-loop ({source} -> {target}).")
            continue

        source_number = node_numeric_id(source)
        target_number = node_numeric_id(target)
        if policy == "legacy" and target_number <= source_number:
            errors.append(
                f"{context} must respect DAG ordering (target id must be greater than source id)."
            )

        source_node = node_by_id[source]
        target_node = node_by_id[target]
        source_archetype = source_node["archetype"]
        target_archetype = target_node["archetype"]
        source_category = source_node["category"]
        target_category = target_node["category"]

        if policy == "legacy" and decision == "yes":
            source_rank = ARCHETYPE_ORDER[source_archetype]
            target_rank = ARCHETYPE_ORDER[target_archetype]
            if target_rank < source_rank or target_rank > source_rank + 1:
                yes_progression_violations += 1
                errors.append(
                    f"{context} violates semantic progression: yes edges must stay at same archetype or advance by one "
                    f"(source={source_archetype}, target={target_archetype})."
                )

            if source_archetype in EARLY_POSITIVE_ARCHETYPES and source_category != target_category:
                early_positive_cross_domain_violations += 1
                errors.append(
                    f"{context} violates early-stage semantic coherence: yes edges from {source_archetype} must remain in-domain "
                    f"(source={source_category}, target={target_category})."
                )

        match = EDGE_ID_RE.fullmatch(edge_id)
        assert match is not None
        if (match.group(1), match.group(2), match.group(3)) != (source, decision, target):
            errors.append(
                f"{context} id tuple must match source/decision/target exactly for edge {edge_id}."
            )

        if policy == "legacy" and decision in outgoing[source]:
            errors.append(
                f"{context} violates deterministic branching: source {source} already has decision {decision}."
            )
            continue
        outgoing[source][decision].append(target)
        incoming_count[target] += 1

        if source_category != target_category:
            cross_domain_edges += 1

    edge_count = len(edge_by_id)

    nonterminal_nodes: list[str] = []
    terminal_nodes: list[str] = []
    branch_failures = 0
    for node_id in sorted(node_by_id, key=node_numeric_id):
        decisions = outgoing.get(node_id, {})
        if decisions:
            nonterminal_nodes.append(node_id)
            decision_keys = set(decisions)
            if decision_keys != DECISION_SET:
                branch_failures += 1
                errors.append(
                    f"Node {node_id} needs at least one route for each of yes/no/unknown; found {sorted(decision_keys)}."
                )
        else:
            terminal_nodes.append(node_id)

    if not terminal_nodes:
        errors.append("Graph must contain terminal nodes with zero outgoing edges.")

    for node_id, node in node_by_id.items():
        if node["archetype"] == "terminal" and outgoing.get(node_id):
            errors.append(f"Terminal question {node_id} cannot have outgoing routes.")
        if node["archetype"] != "terminal" and not outgoing.get(node_id):
            errors.append(f"Nonterminal question {node_id} has no declared routes.")

    if policy == "legacy" and edge_count != len(nonterminal_nodes) * 3:
        errors.append(
            "Edge cardinality mismatch: each non-terminal must contribute exactly three edges "
            f"(edges={edge_count}, nonterminals={len(nonterminal_nodes)})."
        )

    entry_unique = []
    seen_entries: set[str] = set()
    for value in entry_node_ids:
        if value in seen_entries:
            errors.append(f"entryNodeIds contains duplicate value: {value}")
            continue
        seen_entries.add(value)
        entry_unique.append(value)

    if not entry_unique:
        errors.append("entryNodeIds must include at least one valid entry node.")

    missing_entry_refs = [value for value in entry_unique if value not in node_by_id]
    if missing_entry_refs:
        errors.append(f"entryNodeIds references missing nodes: {', '.join(sorted(missing_entry_refs))}")

    entry_domain_coverage: dict[str, bool] = {}
    for domain in DOMAINS:
        entry_domain_coverage[domain] = any(
            node_by_id.get(node_id, {}).get("category") == domain for node_id in entry_unique
        )

    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {node_id: 0 for node_id in node_by_id}
    for source, decision_map in outgoing.items():
        for target in (target for targets in decision_map.values() for target in targets):
            adjacency[source].append(target)
            indegree[target] += 1

    reachable: set[str] = set()
    bfs_queue: deque[str] = deque()
    for entry in entry_unique:
        if entry in node_by_id and entry not in reachable:
            reachable.add(entry)
            bfs_queue.append(entry)

    while bfs_queue:
        current = bfs_queue.popleft()
        for nxt in adjacency.get(current, []):
            if nxt not in reachable:
                reachable.add(nxt)
                bfs_queue.append(nxt)

    if len(reachable) != len(node_by_id):
        missing = sorted(set(node_by_id) - reachable, key=node_numeric_id)
        preview = ", ".join(missing[:15])
        suffix = "..." if len(missing) > 15 else ""
        errors.append(
            f"All nodes must be reachable from entryNodeIds; missing {len(missing)} nodes ({preview}{suffix})."
        )

    indegree_copy = dict(indegree)
    topo_queue = deque(sorted([node_id for node_id, value in indegree_copy.items() if value == 0], key=node_numeric_id))
    visited = 0
    while topo_queue:
        current = topo_queue.popleft()
        visited += 1
        for nxt in adjacency.get(current, []):
            indegree_copy[nxt] -= 1
            if indegree_copy[nxt] == 0:
                topo_queue.append(nxt)

    dag_pass = visited == len(node_by_id)
    if policy == "legacy" and not dag_pass:
        errors.append("Graph must be acyclic (DAG). Cycle detected by topological sort.")

    fanin_exception_set = set(fanin_exception_node_ids)
    for node_id in fanin_exception_set:
        if node_id not in node_by_id:
            errors.append(f"fanInExceptionNodeIds references missing node: {node_id}")

    max_fanin = 0
    fanin_violations: list[str] = []
    fanin_exception_nodes_used: list[str] = []
    terminal_node_set = set(terminal_nodes)
    for node_id in sorted(node_by_id, key=node_numeric_id):
        fanin = incoming_count.get(node_id, 0)
        max_fanin = max(max_fanin, fanin)
        if node_id in terminal_node_set:
            limit = FANIN_TERMINAL_LIMIT
        else:
            limit = FANIN_EXCEPTION_LIMIT if node_id in fanin_exception_set else FANIN_DEFAULT_LIMIT
            hub = node_by_id[node_id].get("extensions", {}).get("tensor:genericEvidenceHub")
            if hub is not None:
                expected = {"profile": "tensor-restored-evidence/2", "maxFanIn": GENERIC_HUB_LIMITS.get(node_id),
                            "basis": "Explicit same-domain context adapters; target prerequisites are re-evaluated"}
                if node_id not in GENERIC_HUB_LIMITS or hub != expected:
                    errors.append(f"{node_id}: unrecognized generic evidence hub capacity")
                else:
                    limit = GENERIC_HUB_LIMITS[node_id]
            if node_id in fanin_exception_set and fanin > FANIN_DEFAULT_LIMIT:
                fanin_exception_nodes_used.append(node_id)
        if fanin > limit:
            fanin_violations.append(f"{node_id} (fanin={fanin}, limit={limit})")

    if fanin_violations:
        (errors if policy == "legacy" else warnings).append("Historical fan-in reference exceeded: " + ", ".join(fanin_violations[:25]))

    cross_domain_ratio = (cross_domain_edges / edge_count) if edge_count else 0.0
    if cross_domain_ratio < CROSS_DOMAIN_RATIO_MIN:
        warnings.append(
            f"Historical cross-domain reference ratio {cross_domain_ratio:.4f} is below {CROSS_DOMAIN_RATIO_MIN:.2f}; diagnostic only under the current graph assurance policy."
        )

    metrics: dict[str, Any] = {
        "nodeCount": len(node_by_id),
        "edgeCount": edge_count,
        "nonTerminalCount": len(nonterminal_nodes),
        "terminalCount": len(terminal_nodes),
        "entryCount": len(entry_unique),
        "entryNodeIds": sorted(entry_unique, key=node_numeric_id),
        "entryCoverageByDomain": entry_domain_coverage,
        "domainCounts": dict(sorted(category_counts.items())),
        "archetypeCounts": dict(sorted(archetype_counts.items())),
        "domainArchetypeMatrix": {
            domain: {archetype: domain_archetype_counts[domain].get(archetype, 0) for archetype in ARCHETYPES}
            for domain in DOMAINS
        },
        "crossDomainEdgeCount": cross_domain_edges,
        "crossDomainRatio": cross_domain_ratio,
        "crossDomainRatioMin": CROSS_DOMAIN_RATIO_MIN,
        "fanInDefaultLimit": FANIN_DEFAULT_LIMIT,
        "fanInExceptionLimit": FANIN_EXCEPTION_LIMIT,
        "fanInTerminalLimit": FANIN_TERMINAL_LIMIT,
        "maxFanIn": max_fanin,
        "fanInExceptionNodeIds": sorted(fanin_exception_set, key=node_numeric_id),
        "fanInExceptionNodesUsed": sorted(fanin_exception_nodes_used, key=node_numeric_id),
        "genericEvidenceHubLimits": {nid: GENERIC_HUB_LIMITS[nid] for nid in GENERIC_HUB_LIMITS
                                    if node_by_id.get(nid, {}).get("extensions", {}).get("tensor:genericEvidenceHub")},
        "branchDeterminism": {
            "requiredDecisions": DECISIONS,
            "violations": branch_failures,
            "meaning": "Outcome coverage; multiple targets per outcome are allowed. Selection is explicit, never inferred.",
            "multiRouteSourceCount": sum(any(len(targets) > 1 for targets in decisions.values()) for decisions in outgoing.values()),
        },
        "semanticRouting": {
            "yesProgressionViolations": yes_progression_violations,
            "earlyPositiveCrossDomainViolations": early_positive_cross_domain_violations,
            "earlyPositiveArchetypes": sorted(EARLY_POSITIVE_ARCHETYPES),
            "yesProgressionRule": "target_archetype_rank in [source_rank, source_rank+1]",
        },
        "dagPass": dag_pass,
        "reachableNodeCount": len(reachable),
        "allNodesReachable": len(reachable) == len(node_by_id),
    }

    return (errors, warnings, metrics)


def normalize_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for node in sorted(nodes, key=lambda item: node_numeric_id(item["id"])):
        payload = {
            "id": node["id"],
            "text": node["text"],
            "label": node["label"],
            "category": node["category"],
            "archetype": node["archetype"],
        }
        if "extensions" in node:
            payload["extensions"] = node["extensions"]
        normalized.append(payload)
    return normalized


def normalize_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for edge in sorted(edges, key=edge_sort_key):
        payload = {
            "id": edge["id"],
            "source": edge["source"],
            "target": edge["target"],
            "decision": edge["decision"],
        }
        if "label" in edge:
            payload["label"] = edge["label"]
        if "extensions" in edge:
            payload["extensions"] = edge["extensions"]
        normalized.append(payload)
    return normalized


def build_graph_payload(
    version: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    entry_node_ids: list[str],
    schema_version: str | None = None,
) -> dict[str, Any]:
    parse_version(version)
    parse_version(schema_version or version)

    payload = {
        "generatedAt": canonical_generated_at(version),
        "namespace": "tensor",
        "product": "core",
        "version": version,
        "schemaVersion": schema_version or version,
        "locale": "en-US",
        "entryNodeIds": sorted(dict.fromkeys(entry_node_ids), key=node_numeric_id),
        "nodes": normalize_nodes(nodes),
        "edges": normalize_edges(edges),
    }
    profiles = {edge.get("extensions", {}).get("tensor:investigativeLead", {}).get("profile") for edge in edges}
    profiles.discard(None)
    if profiles:
        if len(profiles) != 1 or not profiles <= {"tensor-investigative-routing/1", "tensor-investigative-routing/2"}:
            raise ValidationError("Unrecognized or mixed investigative routing profiles")
        payload["extensions"] = {"tensor:routingProfile": next(iter(profiles))}
        if profiles == {"tensor-investigative-routing/2"}:
            payload["extensions"]["tensor:semanticReview"] = "tensor-semantic-review/1"
    return payload


def build_quality_report_markdown(version: str, errors: list[str], warnings: list[str], metrics: dict[str, Any]) -> str:
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    status = "PASS" if not errors else "FAIL"

    sections: list[str] = []
    sections.append(f"# Core Graph Quality Report ({version})")
    sections.append("")
    sections.append(f"Generated: `{timestamp}`")
    sections.append(f"Status: **{status}**")
    sections.append("")

    summary_headers = ["Metric", "Value"]
    summary_rows = [
        ["Nodes", str(metrics.get("nodeCount", 0))],
        ["Edges", str(metrics.get("edgeCount", 0))],
        ["Non-terminal nodes", str(metrics.get("nonTerminalCount", 0))],
        ["Terminal nodes", str(metrics.get("terminalCount", 0))],
        ["Entry nodes", str(metrics.get("entryCount", 0))],
        ["Reachable nodes", str(metrics.get("reachableNodeCount", 0))],
        ["Cross-domain edges", str(metrics.get("crossDomainEdgeCount", 0))],
        ["Cross-domain ratio", f"{metrics.get('crossDomainRatio', 0.0):.4f}"],
        ["Max fan-in", str(metrics.get("maxFanIn", 0))],
    ]
    sections.append("## Summary")
    sections.append(render_markdown_table(summary_headers, summary_rows))
    sections.append("")

    sections.append("## Domain Counts")
    domain_rows = [[domain, str(metrics.get("domainCounts", {}).get(domain, 0))] for domain in DOMAINS]
    sections.append(render_markdown_table(["Domain", "Count"], domain_rows))
    sections.append("")

    sections.append("## Archetype Counts")
    archetype_rows = [[archetype, str(metrics.get("archetypeCounts", {}).get(archetype, 0))] for archetype in ARCHETYPES]
    sections.append(render_markdown_table(["Archetype", "Count"], archetype_rows))
    sections.append("")

    sections.append("## Entry Coverage By Domain")
    entry_rows = [
        [domain, "yes" if metrics.get("entryCoverageByDomain", {}).get(domain) else "no"]
        for domain in DOMAINS
    ]
    sections.append(render_markdown_table(["Domain", "Has Entry"], entry_rows))
    sections.append("")

    sections.append("## Checks")
    check_rows = [
        ["All nodes reachable from entries", "pass" if metrics.get("allNodesReachable") else "fail"],
        ["DAG", "pass" if metrics.get("dagPass") else "fail"],
        [
            "Historical cross-domain reference (diagnostic)",
            "met"
            if metrics.get("crossDomainRatio", 0.0) >= metrics.get("crossDomainRatioMin", CROSS_DOMAIN_RATIO_MIN)
            else "not met",
        ],
        [
            "Branch determinism violations",
            str(metrics.get("branchDeterminism", {}).get("violations", "n/a")),
        ],
        [
            "Yes-edge semantic progression violations",
            str(metrics.get("semanticRouting", {}).get("yesProgressionViolations", "n/a")),
        ],
        [
            "Early-stage cross-domain yes violations",
            str(metrics.get("semanticRouting", {}).get("earlyPositiveCrossDomainViolations", "n/a")),
        ],
    ]
    sections.append(render_markdown_table(["Check", "Result"], check_rows))
    sections.append("")

    if warnings:
        sections.append("## Warnings")
        for warning in warnings:
            sections.append(f"- {warning}")
        sections.append("")

    if errors:
        sections.append("## Errors")
        for error in errors:
            sections.append(f"- {error}")
        sections.append("")

    return "\n".join(sections).rstrip() + "\n"


def build_coverage_matrix_payload(version: str, metrics: dict[str, Any]) -> dict[str, Any]:
    domain_rows = []
    matrix = metrics.get("domainArchetypeMatrix", {})
    for domain in DOMAINS:
        row = {
            "domain": domain,
            "nodeCount": metrics.get("domainCounts", {}).get(domain, 0),
            "entryCoverage": bool(metrics.get("entryCoverageByDomain", {}).get(domain)),
            "archetypes": matrix.get(domain, {}),
        }
        domain_rows.append(row)

    return {
        "version": version,
        "generatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dimensions": [
            "Domain",
            "Archetype",
            "Entry Coverage",
            "Reachability",
            "Branch Completeness",
            "Cross-domain Pivots",
        ],
        "overall": {
            "nodeCount": metrics.get("nodeCount"),
            "edgeCount": metrics.get("edgeCount"),
            "crossDomainRatio": metrics.get("crossDomainRatio"),
            "allNodesReachable": metrics.get("allNodesReachable"),
            "branchViolations": metrics.get("branchDeterminism", {}).get("violations"),
        },
        "domains": domain_rows,
    }


def build_coverage_matrix_markdown(version: str, metrics: dict[str, Any]) -> str:
    sections: list[str] = []
    sections.append(f"# Core Coverage Matrix ({version})")
    sections.append("")

    headers = [
        "Domain",
        "Nodes",
        "Entry",
        *ARCHETYPES,
    ]

    rows: list[list[str]] = []
    matrix = metrics.get("domainArchetypeMatrix", {})
    for domain in DOMAINS:
        rows.append(
            [
                domain,
                str(metrics.get("domainCounts", {}).get(domain, 0)),
                "yes" if metrics.get("entryCoverageByDomain", {}).get(domain) else "no",
                *[str(matrix.get(domain, {}).get(archetype, 0)) for archetype in ARCHETYPES],
            ]
        )

    sections.append(render_markdown_table(headers, rows))
    sections.append("")
    sections.append("## Global Coverage Signals")
    global_rows = [
        ["All nodes reachable", "yes" if metrics.get("allNodesReachable") else "no"],
        ["DAG", "yes" if metrics.get("dagPass") else "no"],
        ["Cross-domain ratio", f"{metrics.get('crossDomainRatio', 0.0):.4f}"],
        ["Cross-domain minimum", f"{metrics.get('crossDomainRatioMin', CROSS_DOMAIN_RATIO_MIN):.2f}"],
        ["Branch violations", str(metrics.get("branchDeterminism", {}).get("violations", 0))],
    ]
    sections.append(render_markdown_table(["Signal", "Value"], global_rows))
    sections.append("")

    return "\n".join(sections).rstrip() + "\n"
