"""Versioned authoring acceptance, separate from historical topology diagnostics.

This evaluates the dated graph's evidence profile, not the separate Core record
contract. Passing is author-side evidence; it never authorizes publication.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json

from core_graph_pipeline import DOMAINS
from evaluate_entry_scenarios import expand_suite, references, run_cases

POLICY_ID = "tensor-graph-assurance/3"
STRUCTURAL_IDS = {"full_reachability", "branch_totality", "coverage_score"}
DIAGNOSTIC_IDS = {"dag_pass", "cross_domain_pivots", "routing_score", "robustness_score", "targeted_resilience",
                  "routing_centralization", "information_gain", "overall_score"}
EVIDENCE_IDS = ("evidence_cards", "evidence_transitions", "scenario_agreement", "scenario_coverage")
ROLE_RULES = {
    "entry": ("detect", "primary-match"), "alternate": ("detect", "independent-match"),
    "primaryValidation": ("validate", "primary-validation"),
    "independentValidation": ("validate", "independent-validation"),
    "classification": ("classify", "hypothesis-test"), "scope": ("scope", "scope-bound"),
    "correlation": ("correlate", "relationship-test"), "attribution": ("attribute", "source-test"),
    "impact": ("impact", "effect-test"), "exclusion": ("terminal", "bounded-exclusion"),
    "unresolved": ("terminal", "unresolved-stop"), "refuted": ("terminal", "refuted-stop"),
    "assessed": ("terminal", "findings-stop"),
}


def gate(gate_id, errors, status=None):
    return {"id": gate_id, "passed": not errors, "status": status or ("pass" if not errors else "fail"),
            "evidence": errors or ["Required checks passed"], "blocking": True}


def build_acceptance(authoring_errors, reference, evidence_gates=None):
    """Fail closed on missing checks or an unreviewed reference-gate catalog."""
    legacy = reference.get("gates", [])
    ids = [g["id"] for g in legacy]
    catalog_ok = set(ids) == STRUCTURAL_IDS | DIAGNOSTIC_IDS and len(ids) == len(set(ids))
    gates = [gate("graph_authoring", list(authoring_errors)),
             gate("policy_catalog", [] if catalog_ok else ["Reference gate catalog changed; review the policy classification"])]
    gates += [{**g, "blocking": True, "status": "pass" if g["passed"] else "fail"}
              for g in legacy if g["id"] in STRUCTURAL_IDS]
    supplied = {g["id"]: g for g in evidence_gates or []}
    if len(supplied) != len(evidence_gates or []) or set(supplied) - set(EVIDENCE_IDS):
        gates.append(gate("evidence_catalog", ["Evidence gate catalog is invalid"]))
    gates += [supplied.get(gid, gate(gid, ["Exact evidence package has not been evaluated"], "notRun")) for gid in EVIDENCE_IDS]
    failed = [g["id"] for g in gates if g["passed"] is not True]
    return {"policy": POLICY_ID, "allPassed": not failed, "failedGateIds": failed, "gates": gates,
            "scope": "Author-side graph structure and bounded evidence-profile acceptance; not investigative effectiveness, independent review or release authorization"}


def assess_evidence(graph, graph_sha256, criteria, suite):
    if "semanticReview" in criteria:
        from semantic_graph_review import assess as semantic_assess
        try:
            return semantic_assess(graph, graph_sha256, criteria, suite)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError) as exc:
            return [gate(gid, [f"Reviewed evidence package cannot be evaluated: {exc}"]) for gid in EVIDENCE_IDS]
    if "routingProfile" in criteria:
        from investigative_routing import continuation_edges, assess_routes
        projection = {**graph, "edges": continuation_edges(graph)}
        old_criteria = {k: v for k, v in criteria.items() if k != "routingProfile"}
        projected_sha = sha256(json.dumps(projection, sort_keys=True).encode()).hexdigest()
        old_criteria["graphSha256"] = projected_sha
        gates = assess_evidence(projection, projected_sha, old_criteria, suite)
        route_errors = assess_routes(graph, criteria)
        if (criteria.get("graphSha256") != graph_sha256 or criteria.get("graphVersion") != graph["version"]):
            route_errors.append("Routing profile does not pin the exact active graph bytes and version")
            next(g for g in gates if g["id"] == "evidence_cards").update(passed=False, status="fail", evidence=["Evidence criteria must pin the exact active graph bytes and version"])
        target = next(g for g in gates if g["id"] == "evidence_transitions")
        if route_errors:
            target.update(passed=False, status="fail", evidence=route_errors+target["evidence"])
        return gates
    if "restoration" not in criteria:
        return _assess_base(graph, graph_sha256, criteria, suite)
    try:
        from restoration_assurance import assess
        base_ids = set(criteria["restoration"]["baseNodeIds"])
        projection = {**graph, "nodes": [n for n in graph["nodes"] if n["id"] in base_ids],
                      "edges": [e for e in graph["edges"] if e["source"] in base_ids],
                      "entryNodeIds": [d["entry"] for d in criteria["domains"].values()]}
        # This digest identifies the in-memory projection, never the full graph.
        projection_sha = sha256(json.dumps(projection, sort_keys=True).encode()).hexdigest()
        projected_criteria = {**criteria, "nodes": {nid: c for nid, c in criteria["nodes"].items() if nid in base_ids}, "graphSha256": projection_sha}
        base_gates = _assess_base(projection, projection_sha, projected_criteria, suite)
        errors = assess(graph, criteria, suite)
        if (criteria.get("graphSha256") != graph_sha256 or criteria.get("graphVersion") != graph["version"]
                or criteria.get("schemaVersion") != graph["schemaVersion"] or set(criteria["nodes"]) != {n["id"] for n in graph["nodes"]}):
            errors[0].append("Full evidence package does not pin the exact graph bytes/version/schema and every question")
        return [gate(gid, ([] if base_gates[i]["passed"] else base_gates[i]["evidence"])+errors[i]) for i, gid in enumerate(EVIDENCE_IDS)]
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        return [gate(gid, [f"Composite evidence package cannot be evaluated: {exc}"]) for gid in EVIDENCE_IDS]


def _assess_base(graph, graph_sha256, criteria, suite):
    """Check the actual evidence cards, every transition, and supplied scenarios."""
    card_errors, route_errors, scenario_errors, coverage_errors = [], [], [], []
    try:
        nodes = {n["id"]: n for n in graph["nodes"]}
        cards, domains = criteria["nodes"], criteria["domains"]
        if (criteria.get("graphSha256") != graph_sha256 or criteria.get("graphVersion") != graph["version"]
                or criteria.get("schemaVersion") != graph["schemaVersion"]):
            card_errors.append("Evidence criteria do not pin the exact graph bytes, version and schema identity")
        if set(cards) != set(nodes) or set(domains) != set(DOMAINS):
            card_errors.append("Every active question and all seven domains need evidence cards")
        required = {"questionId", "boundSubjects", "timeInterval", "evidenceReferences", "method", "answer", "rationale", "limitations"}
        expected_roles = {}
        for name, domain in domains.items():
            if not references(domain.get("bindings")):
                card_errors.append(f"{name}: subject bindings must be explicit")
            for role in ROLE_RULES:
                ids = domain[role]
                ids = ids if isinstance(ids, list) else [ids]
                if not ids or len(ids) != len(set(ids)):
                    card_errors.append(f"{name}: {role} IDs are missing or ambiguous")
                for nid in ids:
                    if nid in expected_roles:
                        card_errors.append(f"{nid}: duplicated role binding")
                    expected_roles[nid] = (name, role)
            if len(domain["classification"]) != len(domain["scope"]) or len(domain["classification"]) not in (1, 2):
                card_errors.append(f"{name}: primary/independent hypothesis and scope bindings must correspond")
        if set(expected_roles) != set(nodes):
            card_errors.append("Domain role bindings must cover every active question exactly once")
        if set(graph["entryNodeIds"]) != {d["entry"] for d in domains.values()}:
            card_errors.append("Graph entries must match the explicit evidence-profile entries")
        for nid, node in nodes.items():
            card = cards[nid]
            domain_name, role = expected_roles[nid]
            archetype, rule = ROLE_RULES[role]
            annotation = node.get("extensions", {}).get("tensor:evidenceCriteria", {})
            if (card["domain"] != domain_name or node["category"] != domain_name or card["role"] != role
                    or node["archetype"] != archetype or card["rule"] != rule
                    or card["predicate"] != node["text"] or card["boundSubjectFields"] != domains[domain_name]["bindings"]
                    or not required <= set(card["requiredAssessmentRecord"])
                    or annotation != {"document": "entry-evidence-criteria.json", "version": graph["version"], "nodeId": nid}):
                card_errors.append(f"{nid}: evidence card, role or version annotation disagrees with the graph")
            answers = criteria["rules"][rule]
            if set(answers) != {"yes", "no", "unknown"} or not all(isinstance(v, str) and v.strip() for v in answers.values()):
                card_errors.append(f"{nid}: yes/no/unknown evidence criteria must be explicit")

        expected_edges = {}
        def bind(source, yes, no, unknown):
            for answer, target in zip(("yes", "no", "unknown"), (yes, no, unknown)):
                expected_edges[(source, answer)] = target

        for domain in domains.values():
            unresolved = domain["unresolved"]
            bind(domain["entry"], domain["primaryValidation"], domain["exclusion"], domain["alternate"])
            bind(domain["alternate"], domain["independentValidation"], unresolved, unresolved)
            bind(domain["primaryValidation"], domain["classification"][0], unresolved, unresolved)
            bind(domain["independentValidation"], domain["classification"][-1], unresolved, unresolved)
            for classification, scope in zip(domain["classification"], domain["scope"]):
                bind(classification, scope, domain["refuted"], unresolved)
                bind(scope, domain["correlation"], unresolved, unresolved)
            for role, target_role in (("correlation", "attribution"), ("attribution", "impact"), ("impact", "assessed")):
                target = domain[target_role]
                bind(domain[role], target, target, target)
        actual_edges = {(e["source"], e["decision"]): e["target"] for e in graph["edges"]}
        if actual_edges != expected_edges or len(actual_edges) != len(graph["edges"]):
            differences = set(actual_edges) ^ set(expected_edges)
            differences |= {k for k in actual_edges.keys() & expected_edges.keys() if actual_edges[k] != expected_edges[k]}
            route_errors.append(f"Unsupported hypothesis, context, uncertainty or ending transitions: {sorted(differences)}")

        results = run_cases(graph, criteria, suite)
        cases = expand_suite(suite)["cases"]
        if not results or any(not result["passed"] for result in results):
            scenario_errors.append("Scenarios are empty or disagree with their explicitly declared traces/states")
        seen = defaultdict(set)
        stage_seen = defaultdict(set)
        for case, result in zip(cases, results):
            for step in result["trace"]:
                seen[step["nodeId"]].add(step["answer"])
                stage_seen[(case["domain"], cards[step["nodeId"]]["role"])].add(step["answer"])
        for nid, card in cards.items():
            if card["role"] in ("entry", "classification") and seen[nid] != {"yes", "no", "unknown"}:
                coverage_errors.append(f"{nid}: entry/classification needs evidence cases for yes/no/unknown")
        for name in domains:
            for role in ("scope", "correlation", "attribution", "impact"):
                if stage_seen[(name, role)] != {"yes", "no", "unknown"}:
                    coverage_errors.append(f"{name}/{role}: all three assessments need scenario coverage")
        for name in domains:
            public = [(case, result) for case, result in zip(cases, results)
                      if case["domain"] == name and case.get("evidenceKind") == "public-report-only"]
            if not public or any(r["state"] != "unresolved" or r["trace"][0]["answer"] != "unknown" for _, r in public):
                coverage_errors.append(f"{name}: retain an unresolved public-report case with missing victim evidence")
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        message = f"Evidence package cannot be evaluated: {exc}"
        card_errors.append(message)
        route_errors.append(message)
        scenario_errors.append(message)
        coverage_errors.append(message)
    return [gate(gid, errors) for gid, errors in zip(EVIDENCE_IDS, (card_errors, route_errors, scenario_errors, coverage_errors))]
