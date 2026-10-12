"""Acceptance for the additive evidence profile; never independent review."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from restored_evidence import STAGES, run_cases
from core_graph_pipeline import GENERIC_HUB_LIMITS

ROOT = Path(__file__).resolve().parents[1]


def assess(graph, criteria, suite):
    errors = [[], [], [], []]
    cards_error, routes_error, cases_error, coverage_error = errors
    profile = criteria["restoration"]
    ids = set(profile["restoredNodeIds"])
    nodes = {n["id"]: n for n in graph["nodes"]}
    cards = criteria["nodes"]
    published = ROOT / "releases/core/graphs/v0.20260206e/tensor.core.graph.json"
    if (profile["profile"] != "tensor-restored-evidence/2" or profile["sourceSha256"] != sha256(published.read_bytes()).hexdigest()
            or profile["sourceVersion"] != json.loads(published.read_text())["version"]):
        cards_error.append("Restoration must pin the unchanged exact original release")
    original = {n["id"]: n for n in json.loads(published.read_text())["nodes"]}
    base = set(profile["baseNodeIds"])
    prior_bytes = (ROOT / "drafts/core/reviews/2026-10-12-restoration/prior-draft.graph.json").read_bytes()
    prior = json.loads(prior_bytes)
    if sha256(prior_bytes).hexdigest() != "8b83f19f83d7d796c96b404d37f4ae093d36415b35123602133f34cad5c172be":
        cards_error.append("Prior repair snapshot must remain byte-for-byte intact")
    if base != {n["id"] for n in prior["nodes"]} or ids != set(original) - base or ids & base or set(nodes) != ids | base:
        cards_error.append("The full original inventory and all prior repairs must be retained exactly once")
    for previous in prior["nodes"]:
        if any(nodes[previous["id"]].get(k) != previous.get(k) for k in ("text", "label", "category", "archetype")):
            cards_error.append(f"{previous['id']}: restoration changed a previously repaired predicate")
        nid = previous["id"]
        hub = nodes[nid].get("extensions", {}).get("tensor:genericEvidenceHub")
        expected_hub = {"profile": "tensor-restored-evidence/2", "maxFanIn": GENERIC_HUB_LIMITS[nid],
                        "basis": "Explicit same-domain context adapters; target prerequisites are re-evaluated"} if nid in GENERIC_HUB_LIMITS else None
        if hub != expected_hub:
            cards_error.append(f"{nid}: generic hub capacity must match the explicit reviewed policy")
    for nid in ids:
        n, card = nodes[nid], cards[nid]
        source = original[nid]
        from restore_original_questions import classify, PREDICATES, RULES, PREREQUISITES
        facet, kind, _ = classify(source)
        if (card.get("role") != "restored" or card.get("sourceFacet") != facet or card.get("assessmentKind") != kind
                or card.get("stage") != source["archetype"] or n["archetype"] != source["archetype"]
                or card.get("resumePrerequisites") != PREREQUISITES[source["archetype"]]
                or card.get("domain") != source["category"] or n["category"] != source["category"]
                or card.get("predicate") != n["text"] or n["text"] != PREDICATES[kind].format(facet=facet)
                or card.get("rule") != "restored-"+kind
                or criteria["rules"].get(card["rule"]) != dict(zip(("yes", "no", "unknown"), RULES[kind]))
                or card.get("boundSubjectFields") != criteria["domains"][n["category"]]["bindings"]
                or not {"questionId", "boundSubjects", "timeInterval", "evidenceReferences", "method", "answer", "rationale", "limitations"} <= set(card.get("requiredAssessmentRecord", []))
                or n.get("extensions", {}).get("tensor:evidenceCriteria") != {"document": "entry-evidence-criteria.json", "version": graph["version"], "nodeId": nid}
                or n.get("extensions", {}).get("tensor:sourceQuestion") != {"version": profile["sourceVersion"], "sha256": profile["sourceSha256"], "nodeId": nid}):
            cards_error.append(f"{nid}: original source, bounded predicate, criteria or context disagrees")
    incoming = {e["target"] for e in graph["edges"]}
    expected_entries = {d["entry"] for d in criteria["domains"].values()} | (ids - incoming)
    if set(graph["entryNodeIds"]) != expected_entries or set(profile["resumeEntryIds"]) != ids - incoming:
        routes_error.append("Entries must be the seven repaired roots and explicit unlinked supplementary resumption roots")
    branches = defaultdict(dict)
    for edge in graph["edges"]:
        if edge["source"] not in ids:
            if edge["target"] in ids:
                routes_error.append("The proven base paths must not silently enter a supplemental predicate")
            continue
        source, target = nodes[edge["source"]], nodes[edge["target"]]
        branches[source["id"]][edge["decision"]] = target["id"]
        if source["category"] != target["category"]:
            routes_error.append(f"{edge['id']}: unsupported domain pivot")
        if target["id"] in base:
            role = {"validate": "primaryValidation", "classify": "classification", "scope": "scope", "correlate": "correlation",
                    "attribute": "attribution", "impact": "impact"}.get(target["archetype"])
            expected_target = criteria["domains"][source["category"]].get(role)
            if isinstance(expected_target, list):
                expected_target = expected_target[0]
            adapter = {"profile": profile["profile"], "focus": cards[source["id"]]["sourceFacet"],
                       "preserve": ["domain", "bindings", "interval", "hypothesisId", "priorAnswers"], "recheckPrerequisites": True}
            if target["id"] != expected_target or edge.get("extensions", {}).get("tensor:contextAdapter") != adapter:
                routes_error.append(f"{edge['id']}: generic continuation must explicitly preserve the full source context")
        elif target["archetype"] != "terminal" and cards[target["id"]]["sourceFacet"] != cards[source["id"]]["sourceFacet"]:
            routes_error.append(f"{edge['id']}: unrelated fixed-facet continuation")
        if not edge.get("extensions", {}).get("tensor:routeBasis"):
            routes_error.append(f"{edge['id']}: independent target assessment/retention basis is missing")
        optional = cards[source["id"]]["assessmentKind"] in ("baseline", "corroboration", "additional-entities", "dependencies")
        if not optional and edge["decision"] in ("no", "unknown") and source["archetype"] in ("detect", "validate", "classify", "scope") and target["archetype"] != "terminal":
            routes_error.append(f"{edge['id']}: unsupported hypothesis or scope must stop without a downstream finding")
        if target["archetype"] != "terminal" and STAGES.index(target["archetype"]) != STAGES.index(source["archetype"])+1:
            routes_error.append(f"{edge['id']}: restored assessments must advance one stage")
    for nid in ids:
        if (nodes[nid]["archetype"] in ("correlate", "attribute", "impact") or cards[nid]["assessmentKind"] in
                ("baseline", "corroboration", "additional-entities", "dependencies")) and len(set(branches[nid].values())) != 1:
            routes_error.append(f"{nid}: negative/unknown relation, source or effect answers must be retained on the same qualified continuation")
    results = run_cases(graph, criteria, suite)
    if not results or any(not r["passed"] for r in results):
        cases_error.append("Restored node/path evidence cases disagree with explicit expectations")
    seen = defaultdict(set)
    if len({c["id"] for c in suite["restoredCases"]}) != len(suite["restoredCases"]):
        coverage_error.append("Restored scenario IDs must be unique")
    for case in suite["restoredCases"]:
        seen[case["nodeId"]].add(case["expectedAnswer"])
    if set(seen) != ids or any(seen[nid] != {"yes", "no", "unknown"} for nid in ids):
        coverage_error.append("Every restored question needs positive, negative and unknown evidence cases")
    path_domains = {case["domain"] for case in suite.get("restoredPaths", [])}
    if path_domains != set(criteria["domains"]):
        coverage_error.append("Every domain needs explicitly expected supplementary route scenarios")
    return errors
