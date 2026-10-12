#!/usr/bin/env python3
"""Reproducible author review and repair of every original question; draft only.

This applies explicit editorial decisions to the published prompt families and
records each ID's source, issues, repair and evidence tests. It is not independent
semantic approval, and duplicate wording is never treated as equivalence.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

from core_graph_pipeline import build_graph_payload, validate_and_measure, GENERIC_HUB_LIMITS
from evaluate_entry_scenarios import expand_suite
from restored_evidence import STAGES

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "drafts/core/reviews/2026-10-12-restoration"
VERSION = "0.20261012b"
APPLICABILITY = {
    "Identity": "A named principal/action and bounded record; credential ownership, authorization and human intent require separate evidence/profiles.",
    "Host": "A named host/process event; state-only changes without a process binding need an additional public event profile.",
    "Network": "A named endpoint pair and communication; configuration-only or sensor-coverage claims need an additional public event profile.",
    "Cloud": "A named tenant/resource/operation; the base path describes control-plane activity. Data-plane access and state-only events need a separately reviewed public event profile.",
    "Email": "A named message/mailbox delivery context; mailbox-rule creation, mailbox access and collaboration actions without a message need an additional public event profile.",
    "Application": "A named application/request context; background configuration, session-only and autonomous state changes without a request need an additional public event profile.",
    "File": "A named file/system presence context; deletion, historical lineage and unavailable-content propositions need an additional public event profile. Same file on another system is a distinct declared context.",
}
PRIOR_PINS = {"prior-draft.graph.json": "8b83f19f83d7d796c96b404d37f4ae093d36415b35123602133f34cad5c172be",
              "prior-criteria.json": "0595cdd6a27c44ca87839981a2b4b93d51452a234a7af8d400da68c900cf1e49",
              "prior-scenarios.json": "13541a42427aa3b61a1bd2ae58e1913dbd04d40049085c1826ef503dc4026f69"}
PREREQUISITES = {"detect": [], "validate": ["matching-record"], "classify": ["matching-record", "validated-event"],
    "scope": ["matching-record", "validated-event", "supported-hypothesis"],
    "correlate": ["matching-record", "validated-event", "supported-hypothesis", "bounded-scope"],
    "attribute": ["matching-record", "validated-event", "supported-hypothesis", "bounded-scope"],
    "impact": ["matching-record", "validated-event", "supported-hypothesis", "bounded-scope"], "terminal": ["retained-assessment-record"]}
FACETS = ("control-plane actions", "content lineage", "process ancestry", "execution lineage",
          "collaboration artifacts", "session anomalies", "privileged access events", "transport metadata",
          "data access traces", "authentication pathways", "workload identity context", "message delivery paths",
          "artifact provenance", "endpoint state changes", "network pivots", "api invocation patterns")


def encoded(data):
    return (json.dumps(data, indent=2, ensure_ascii=True) + "\n").encode()


def load(path):
    return json.loads(path.read_text())


def classify(node):
    """Recognize all source families explicitly. Unknown source prose fails closed."""
    text, stage = node["text"].lower(), node["archetype"]
    facets = [f for f in FACETS if f in text]
    if len(facets) != 1:
        raise ValueError(f"{node['id']}: ambiguous or unrecognized evidence facet")
    if stage == "detect" and ("was observed in" in text or "present in collected evidence" in text):
        kind, issues = "event-match", ["Event and evidence scope were implicit", "A negative search must not imply event absence"]
    elif stage == "validate":
        if "trusted baselines" in text:
            kind = "baseline"
        elif "independent evidence sources" in text or "corroborating records" in text:
            kind = "corroboration"
        elif "authentic telemetry" in text:
            kind = "provenance"
        else:
            raise ValueError(node)
        issues = ["Validation basis, subject/time and rejection criteria were unspecified", "Source copies and trusted labels do not establish independent truth"]
    elif stage == "classify" and any(s in text for s in ("adversarial intent", "actionable investigation category", "benign activity, policy violation, or malicious behavior", "sufficient confidence")):
        kind, issues = "hypothesis", ["Intent, categorical verdict or undefined confidence was not an operational predicate", "One falsifiable technical hypothesis must be separated from policy and human intent"]
    elif stage == "scope":
        if "upstream and downstream dependencies" in text:
            kind = "dependencies"
        elif "additional assets" in text or "expanded to include connected evidence" in text:
            kind = "additional-entities"
        elif "materially affected entities" in text:
            kind = "scope-bound"
        else:
            raise ValueError(node)
        issues = ["Scope expansion did not state inclusion/exclusion evidence or unknown entities", "Affected-population completeness and dependency direction cannot be assumed"]
    elif stage == "correlate":
        if "timeline correlation" in text:
            kind = "temporal"
        elif any(s in text for s in ("multi-source correlation", "at least one other domain", "pivoted indicators")):
            kind = "identifier-relation"
        else:
            raise ValueError(node)
        issues = ["Relation endpoints and discriminating method were implicit", "Coincidence or a shared identifier does not establish causation"]
    elif stage == "attribute":
        if "repeatable adversary objective or technique pattern" in text or "behavioral patterns" in text:
            kind = "behavior-pattern"
        elif "objective hypothesis" in text or "common intent" in text:
            kind = "technical-source"
        else:
            raise ValueError(node)
        issues = ["Human/adversary intent or undefined attribution confidence exceeded the supplied evidence", "Technical source or behavior pattern requires a discriminator and competing explanations"]
    elif stage == "impact" and any(s in text for s in ("mission or business exposure", "measurable operational or data risk", "confidentiality, integrity, or availability impact", "downstream security impacts")):
        kind = "additional-impact" if "beyond currently scoped entities" in text or "across additional affected assets" in text else "metric-change"
        issues = ["Effect, exposure and realized business harm were conflated or unbounded", "Comparable metric, units, time, affected subjects and baseline were unspecified"]
    elif stage == "terminal" and any(s in text for s in ("hypothesis", "residual uncertainty", "terminal assessment", "terminal criteria")):
        kind, issues = "retention", ["Terminal wording could imply investigation closure", "Negative/unknown answers, alternatives and evidence limitations must remain separate"]
    else:
        raise ValueError(f"Unrecognized original prompt: {node}")
    return facets[0], kind, issues


PREDICATES = {
    "event-match": "Does the examined {facet} evidence contain a record matching every bound subject and the bound event within the stated time interval?",
    "baseline": "Does the validated {facet} event satisfy the declared operational comparator for the same bound subjects and time interval?",
    "corroboration": "Does separately originating validated {facet} evidence agree on the declared discriminator for the same bound event, subjects and time interval?",
    "provenance": "Does the selected {facet} event record have a cited acceptable provenance and event-interpretation basis for the bound subjects and time interval?",
    "hypothesis": "Does the validated {facet} event satisfy the declared criterion for one named technical hypothesis, with competing explanations assessed in the bound context?",
    "scope-bound": "Were evidence-backed inclusions, exclusions and unknown entity dispositions for the {facet} hypothesis recorded within the bound subjects and time interval?",
    "additional-entities": "Were additional named entities included in the bounded {facet} scope using cited evidence, with exclusions and unknowns retained?",
    "dependencies": "Does the bounded {facet} scope include an explicitly evidenced upstream or downstream dependency with named validated endpoints and direction?",
    "temporal": "Does the independently validated {facet} endpoint pair meet the declared temporal-coincidence tolerance after accounting for both source clock uncertainties?",
    "identifier-relation": "Does the separately validated {facet} endpoint pair share the declared assessed identifier within explicit subject and time bounds?",
    "technical-source": "Does the assessed {facet} discriminator support the named technical source under its declared criterion, with competing explanations retained?",
    "behavior-pattern": "Does the validated {facet} event satisfy the declared technical behavior-pattern discriminator with alternative explanations retained?",
    "metric-change": "Did the named {facet} technical metric change against a comparable baseline for the explicitly bound effect subjects, units and observation times?",
    "additional-impact": "Did a separately bound additional subject linked to the {facet} event show a named technical metric change against its own comparable baseline and units?",
    "retention": "Were the bounded domain assessments and open {facet} questions retained with separate answers, evidence references and limitations, without asserting investigation closure?",
}
RULES = {
    "event-match": ("A record matches all bound subject fields and interval in the examined facet material.", "The declared available-material search completed without a matching record; event absence remains unproved.", "Bindings, search, time or material counterevidence remain unresolved."),
    "baseline": ("Accepted event provenance plus an applicable named operational comparator and assessed discriminator satisfy the criterion.", "The validated discriminator contradicts the named comparator; this can motivate investigation and does not refute the event.", "Record, comparator applicability, method, fact or its assessment basis is incomplete; rejected event provenance cannot test the comparator."),
    "corroboration": ("Matching independently originating validated records agree on assessed event discriminators; rejected copies cannot hide a valid witness.", "All assessed eligible independent discriminators contradict this event corroboration; this is not event exclusion.", "Independent material is missing, copied, unvalidated, context-mismatched, lacks a discriminator, or accepted witnesses disagree."),
    "provenance": ("The matching selected record has accepted provenance and interpretation assessments with origin and cited basis.", "A cited provenance or interpretation assessment rejects the record for this proposition; the event may still have occurred.", "Matching context, assessment basis or material contradiction is unresolved."),
    "hypothesis": ("The validated event satisfies one explicit technical hypothesis criterion; assessed alternatives are retained.", "The assessed discriminator contradicts that exact hypothesis; no alternative or benignness is implied.", "Hypothesis, operational criterion, alternatives, validation or bound context is incomplete."),
    "scope-bound": ("Source entity inclusion, evidence-backed dispositions and unknowns are recorded; population completeness is not asserted.", "The proposed scope explicitly excludes the retained hypothesis source subject.", "Inclusions, exclusions, evidence, bounds or supported hypothesis are missing, or completeness is asserted."),
    "additional-entities": ("A valid bounded scope includes at least one evidenced entity other than the source subject.", "The valid proposed scope includes no additional entity, or explicitly excludes the source subject.", "Entity dispositions, evidence or prerequisite hypothesis/scope cannot be assessed."),
    "dependencies": ("Full validated endpoint bindings, a shared assessed dependency-relation ID, assessed direction on both endpoints and evidenced target inclusion support the documented relation.", "Assessed full endpoints, relation ID or direction contradict the proposed dependency, or its source/target is excluded from scope.", "Dependency relation, direction, full endpoint validation/inclusion, bounds or prerequisite scope is incomplete; endpoint identities or coincidence alone are insufficient."),
    "temporal": ("Both clock intervals lie wholly within the bound investigation interval and their largest timestamp separation is within the declared tolerance.", "Both clock intervals lie within the investigation interval and their smallest separation exceeds the declared tolerance.", "Clock bounds cross the investigation boundary or overlap the coincidence threshold; endpoint provenance/context, tolerance or prerequisites may be incomplete."),
    "identifier-relation": ("Separately validated endpoints share a typed assessed identifier; causation remains separate.", "Typed assessed identifiers contradict this declared relation only.", "Endpoint provenance, context, discriminator, method or prerequisite scope is incomplete; copied records cannot corroborate."),
    "technical-source": ("A typed assessed discriminator satisfies the named technical-source criterion with alternatives retained; actor identity/intent is separate.", "The discriminator contradicts this technical source only.", "Source criterion, validation, alternatives, context or prerequisite scope is incomplete."),
    "behavior-pattern": ("The assessed event discriminator satisfies the named technical behavior-pattern criterion with alternatives retained.", "The discriminator contradicts that named technical pattern only.", "Pattern identity, operational criterion, alternatives, event validation or prerequisite scope is incomplete."),
    "metric-change": ("Assessed numeric observations differ on the same metric, units and ordered times within the bound effect context; no cause/loss is inferred.", "Comparable assessed observations are unchanged on this named metric only.", "Comparable baseline, observed value, metric, units, provenance, effect subject or prerequisite scope is incomplete."),
    "additional-impact": ("A validated explicitly linked additional subject has its own bound comparable observations showing a metric change.", "That additional subject's bound comparable observations show no change on the named metric.", "The additional subject, assessed link, own metric baseline, units, context or provenance is unresolved."),
    "retention": ("Every retained answer preserves the exact subjects, interval and hypothesis with question, method, rationale, references and limitations; preceding answers remain separate and focus is evidenced as assessed or explicitly open.", "A required assessment in this bound record is known missing or a preceding answer is dropped/changed.", "Retention bounds, version, row context, evidence basis or focus disposition is unresolved, answers conflict, or closure is asserted."),
}


def fixture(domain, facet, kind, seeds):
    case = deepcopy(seeds[domain])
    for key in ("id", "expectedTrace", "expectedState"):
        case.pop(key, None)
    case["focus"] = facet
    case["evidenceKind"] = "authored-normalized-fixture"
    record = case["primary"]["records"][0]
    record["clockUncertaintySeconds"] = 1
    record["evidenceFacet"] = facet
    def setfact(record, key, value):
        record["facts"][key] = {"value": value, "method": "explicit authored fixture discriminator", "assessment": "accepted", "evidenceRefs": [record["id"]]}
    setfact(record, "event.id", "authored-event:42")
    setfact(record, "pattern.id", "authored-pattern:42")
    a = case["analysis"]
    a["baseline"] = {**{k: deepcopy(a["hypothesis"][k]) for k in ("subjects", "interval", "hypothesisId")},
        "comparatorId": "authored-operational-baseline", "evidenceRefs": [record["id"]], "criterion": deepcopy(a["hypothesis"]["criterion"])}
    other = deepcopy(record)
    other.update(id=record["id"]+":independent", origin="separate-authored-origin")
    case["primaryOrigin"] = record["origin"]
    case["independent"] = {"accessible": True, "searched": True, "records": [other]}
    target = a["correlation"]["targetRecord"]
    target["clockUncertaintySeconds"] = 1
    if kind in ("additional-entities", "additional-impact", "dependencies"):
        first_field = next(iter(a["correlation"]["targetSubjects"]))
        a["correlation"]["targetSubjects"][first_field] += ":additional"
        target["subjects"] = deepcopy(a["correlation"]["targetSubjects"])
    if kind == "temporal":
        target["eventTime"] = record["eventTime"]
        a["correlation"].update(relationKind="bounded-time-coincidence", toleranceSeconds=5)
    source_subject = case["bindings"][case["bindingFields"][0]] if "bindingFields" in case else next(iter(case["bindings"].values()))
    target_subject = next(iter(a["correlation"]["targetSubjects"].values()))
    a["scope"]["entities"][0]["subjects"] = deepcopy(case["bindings"])
    if a["correlation"]["targetDomain"] != domain or a["correlation"]["targetSubjects"] != case["bindings"]:
        a["scope"]["entities"].append({"domain": a["correlation"]["targetDomain"], "subjectId": target_subject,
            "subjects": deepcopy(a["correlation"]["targetSubjects"]), "disposition": "included", "evidenceRefs": [target["id"]]})
    a["dependency"] = {**deepcopy(a["correlation"]), "claimKind": "documented-dependency", "direction": "upstream"}
    setfact(record, "dependency.source", source_subject)
    setfact(a["dependency"]["targetRecord"], "dependency.target", target_subject)
    for endpoint in (record, a["dependency"]["targetRecord"]):
        for field, value in case["bindings"].items():
            setfact(endpoint, "dependency.source."+field, value)
        for field, value in a["dependency"]["targetSubjects"].items():
            setfact(endpoint, "dependency.target."+field, value)
        setfact(endpoint, "dependency.relationId", "authored:documented-dependency:42")
        setfact(endpoint, "dependency.direction", "upstream")
    a["pattern"] = {**deepcopy(a["hypothesis"]), "patternId": "authored-pattern:42", "claimKind": "technical-behavior-pattern",
        "evidenceRefs": [record["id"]], "criterion": {"fact": "pattern.id", "equals": "authored-pattern:42", "method": "compare declared technical pattern discriminator"}}
    additional = deepcopy(case)
    additional["domain"] = a["correlation"]["targetDomain"]
    additional["bindings"] = deepcopy(a["correlation"]["targetSubjects"])
    additional["analysis"]["hypothesis"]["subjects"] = deepcopy(additional["bindings"])
    additional["analysis"]["impact"]["subjects"] = deepcopy(additional["bindings"])
    effect_target = deepcopy(target)
    for key, value in record["facts"].items():
        if key.startswith("effect."):
            effect_target["facts"][key] = deepcopy(value)
    a["additionalEffect"] = {**deepcopy(a["correlation"]), "targetRecord": effect_target, "assessment": additional}
    if kind != "additional-impact":
        a.pop("additionalEffect")
    case["retention"] = {"subjects": deepcopy(case["bindings"]), "interval": deepcopy(case["interval"]),
        "graphVersion": VERSION, "closesInvestigation": False, "focusDispositions": {f: "open" for f in FACETS},
        "assessments": [{"nodeId": seeds[domain]["expectedTrace"][0][0], "answer": "unknown", "method": "retain authored observation", "evidenceRefs": [record["id"]],
            "subjects": deepcopy(case["bindings"]), "interval": deepcopy(case["interval"]), "hypothesisId": a["hypothesis"]["hypothesisId"],
            "rationale": "Source observation remains bounded", "limitations": ["Authored fixture, not independently obtained incident evidence"]}]}
    return case


def variant(case, kind, outcome):
    c = deepcopy(case)
    record, a = c["primary"]["records"][0], c["analysis"]
    if outcome == "yes":
        return c
    if outcome == "unknown":
        c["materialConflict"] = True
        return c
    if kind == "event-match":
        c["primary"]["records"] = []
    elif kind in ("baseline", "provenance"):
        if kind == "baseline":
            record["facts"][a["baseline"]["criterion"]["fact"]]["value"] = "contradicts-comparator"
        else:
            record["provenanceAssessment"] = "rejected"
    elif kind == "corroboration":
        c["independent"]["records"][0]["facts"]["event.id"]["value"] = "different-event"
    elif kind == "hypothesis":
        record["facts"][a["hypothesis"]["criterion"]["fact"]]["value"] = "contradicts-hypothesis"
    elif kind in ("scope-bound", "additional-entities"):
        if kind == "scope-bound":
            a["scope"]["entities"][0]["disposition"] = "excluded"
        else:
            a["scope"]["entities"] = a["scope"]["entities"][:1]
    elif kind == "dependencies":
        a["dependency"]["targetRecord"]["facts"]["dependency.target"]["value"] = "different-endpoint"
    elif kind == "temporal":
        a["correlation"]["targetRecord"]["eventTime"] = "2026-10-01T10:40:00Z"
    elif kind == "identifier-relation":
        a["correlation"]["targetRecord"]["facts"][a["correlation"]["targetFact"]]["value"] = "different-identifier"
    elif kind == "technical-source":
        record["facts"][a["attribution"]["criterion"]["fact"]]["value"] = "different-source"
    elif kind == "behavior-pattern":
        record["facts"]["pattern.id"]["value"] = "different-pattern"
    elif kind == "metric-change":
        record["facts"][a["impact"]["observedFact"]]["value"] = record["facts"][a["impact"]["baselineFact"]]["value"]
    elif kind == "additional-impact":
        extra = a["additionalEffect"]
        impact = extra["assessment"]["analysis"]["impact"]
        extra["targetRecord"]["facts"][impact["observedFact"]]["value"] = extra["targetRecord"]["facts"][impact["baselineFact"]]["value"]
    elif kind == "retention":
        c["retention"]["knownMissing"] = True
    else:
        raise ValueError(kind)
    return c


def build():
    for filename, digest in PRIOR_PINS.items():
        if sha256((REVIEW / filename).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Prior evidence snapshot changed: {filename}")
    original_path = ROOT / "releases/core/graphs/v0.20260206e/tensor.core.graph.json"
    original = load(original_path)
    base, criteria, suite = [load(REVIEW / name) for name in ("prior-draft.graph.json", "prior-criteria.json", "prior-scenarios.json")]
    base_ids = {n["id"] for n in base["nodes"]}
    source_sha = sha256(original_path.read_bytes()).hexdigest()
    if source_sha != "dfc3f1a965c01b6f7ade253e426e69abcbad688fab20d9d00065d71c777c010c":
        raise ValueError("Published source changed")
    seeds = {c["domain"]: c for c in expand_suite(suite)["cases"] if c["id"] == c["domain"].lower()+"-supported-record"}
    groups = defaultdict(list)
    duplicates = defaultdict(list)
    for n in original["nodes"]:
        duplicates[n["text"]].append(n["id"])
    cards, rows, nodes = criteria["nodes"], [], deepcopy(base["nodes"])
    criteria["graphVersion"] = suite["graphVersion"] = VERSION
    for node in nodes:
        node["extensions"]["tensor:evidenceCriteria"]["version"] = VERSION
    for n in original["nodes"]:
        facet, kind, issues = classify(n)
        retained = n["id"] in base_ids
        active = next((node for node in nodes if node["id"] == n["id"]), None)
        if not retained:
            active = {"id": n["id"], "category": n["category"], "archetype": n["archetype"],
                "text": PREDICATES[kind].format(facet=facet), "label": f"{n['category']}: {facet.capitalize()} · {kind.replace('-', ' ')}",
                "extensions": {"tensor:evidenceCriteria": {"document": "entry-evidence-criteria.json", "version": VERSION, "nodeId": n["id"]},
                    "tensor:sourceQuestion": {"version": original["version"], "sha256": source_sha, "nodeId": n["id"]}}}
            nodes.append(active)
            cards[n["id"]] = {"domain": n["category"], "role": "restored", "stage": n["archetype"], "rule": "restored-"+kind,
                "assessmentKind": kind, "sourceFacet": facet, "boundSubjectFields": criteria["domains"][n["category"]]["bindings"],
                "requiredAssessmentRecord": deepcopy(cards["Q1"]["requiredAssessmentRecord"]), "predicate": active["text"],
                "resumePrerequisites": PREREQUISITES[n["archetype"]]}
            groups[n["category"], facet, n["archetype"]].append(n["id"])
        changed = n["text"] != active["text"]
        rows.append({"sourceId": n["id"], "sourceCategory": n["category"], "sourceArchetype": n["archetype"], "sourceText": n["text"],
            "sourceFacet": facet, "assessmentKind": kind, "sourceDuplicateIds": duplicates[n["text"]], "issues": issues,
            "disposition": "retain-existing-evidence-repair" if retained else "restore-with-evidence-repair", "semanticReview": "author-reviewed-agent-audit-external-review-pending",
            "applicabilityLimitations": [APPLICABILITY[n["category"]]],
            "agentReviewRef": "reviews/2026-10-12-independent-review/README.md",
            "targetId": n["id"], "targetText": active["text"], "textChanged": changed,
            "meaningChange": "The retained parameterized question is broader than the original facet wording. Bind this original facet when exercising its source capability; ID retention alone is not equivalence." if retained else
                "Replace implicit context, confidence, policy/intent or closure claims with the declared bounded technical assessment. This is an editorially revised capability, not an equivalence assertion.",
            "targetDefinitionRefs": [f"tensor.core.graph.json#/nodes/{n['id']}", f"entry-evidence-criteria.json#/nodes/{n['id']}"],
            "scenarioRefs": [c["id"] for c in expand_suite(suite)["cases"] if any(t[0] == n["id"] for t in c["expectedTrace"])] if retained else
                [f"{n['id']}-{a}" for a in ("yes", "no", "unknown")]})
    for kind, values in RULES.items():
        criteria["rules"]["restored-"+kind] = dict(zip(("yes", "no", "unknown"), values))
    restored_ids = {n["id"] for n in nodes} - base_ids
    edges = deepcopy(base["edges"])
    inbound = Counter(e["target"] for e in edges)
    terminals = {d: [n["id"] for n in nodes if n["category"] == d and n["archetype"] == "terminal" and n["id"] in restored_ids] for d in criteria["domains"]}
    by_id = {n["id"]: n for n in nodes}
    # The base questions explicitly parameterize event/hypothesis evidence. They
    # are valid adapters; an unrelated fixed source facet is not a substitute.
    generic_roles = {"validate": "primaryValidation", "classify": "classification", "scope": "scope",
                     "correlate": "correlation", "attribute": "attribution", "impact": "impact"}
    optional = {"baseline", "corroboration", "additional-entities", "dependencies"}
    def ending(n, cost=1):
        # All supplementary terminal predicates retain qualified records, with focus gaps explicit.
        candidates = [x for x in terminals[n["category"]] if inbound[x] <= 24-cost]
        same = [x for x in candidates if cards[x]["sourceFacet"] == cards[n["id"]]["sourceFacet"]]
        chosen = min(same or candidates, key=lambda x: (inbound[x], int(x[1:])))
        return chosen
    for n in sorted((n for n in nodes if n["id"] in restored_ids and n["archetype"] != "terminal"), key=lambda n: (STAGES.index(n["archetype"]), int(n["id"][1:]))):
        stage, facet = n["archetype"], cards[n["id"]]["sourceFacet"]
        next_stage = STAGES[STAGES.index(stage)+1]
        common = stage in ("correlate", "attribute", "impact") or cards[n["id"]]["assessmentKind"] in optional
        cost = 3 if common else 1
        candidates = [x for x in groups.get((n["category"], facet, next_stage), []) if inbound[x]+cost <= (24 if next_stage == "terminal" else 8)]
        successor = min(candidates, key=lambda x: (inbound[x], int(x[1:]))) if candidates else None
        if successor is None and next_stage == "terminal":
            successor = ending(n, cost)
        if successor is None and next_stage != "terminal":
            successor = criteria["domains"][n["category"]][generic_roles[next_stage]]
            if isinstance(successor, list):
                successor = successor[0]
        for decision in ("yes", "no", "unknown"):
            target = successor if successor and (decision == "yes" or common) else ending(n)
            if target in restored_ids and inbound[target] >= (24 if by_id[target]["archetype"] == "terminal" else 8):
                target = ending(n)
            inbound[target] += 1
            adapter = target in base_ids
            edges.append({"id": f"{n['id']}-{decision}-{target}", "source": n["id"], "target": target, "decision": decision,
                "extensions": {"tensor:routeBasis": "Resume the parameterized base question with the unchanged source facet, complete subjects, interval and hypothesis; recheck target prerequisites and retain all source answers" if adapter else
                    "Assess the same-facet next proposition independently; retain exact subjects, interval and hypothesis, with no inherited target answer" if by_id[target]["archetype"] != "terminal" else
                    "Retain separate source answers and limitations; explicitly record any terminal-focus question still open. This ends this route only",
                    **({"tensor:contextAdapter": {"profile": "tensor-restored-evidence/2", "focus": facet, "preserve": ["domain", "bindings", "interval", "hypothesisId", "priorAnswers"], "recheckPrerequisites": True}} if adapter else {})}})
    entries = base["entryNodeIds"] + sorted(restored_ids - {e["target"] for e in edges}, key=lambda s: int(s[1:]))
    for nid, capacity in GENERIC_HUB_LIMITS.items():
        by_id[nid]["extensions"]["tensor:genericEvidenceHub"] = {"profile": "tensor-restored-evidence/2", "maxFanIn": capacity,
            "basis": "Explicit same-domain context adapters; target prerequisites are re-evaluated"}
    graph = build_graph_payload(VERSION, sorted(nodes, key=lambda n: int(n["id"][1:])), edges, entries, base["schemaVersion"])
    errors, _, _ = validate_and_measure(graph["nodes"], edges, entries, set())
    if errors:
        raise ValueError(errors)
    criteria["graphSha256"] = sha256(encoded(graph)).hexdigest()
    criteria["restoration"] = {"profile": "tensor-restored-evidence/2", "baseNodeIds": sorted(base_ids, key=lambda s: int(s[1:])),
        "restoredNodeIds": sorted(restored_ids, key=lambda s: int(s[1:])), "resumeEntryIds": entries[7:],
        "sourceVersion": original["version"], "sourceSha256": source_sha,
        "reviewDocument": "reviews/2026-10-12-restoration/analysis.json", "sourceQuestionCount": 588,
        "scope": "Author-reviewed source-family repairs with separate AI-assisted routing and evidence challenge. External semantic approval and equivalent investigative coverage remain unproved. Explicit general-question adapters preserve focus, hypothesis and full context; target prerequisites are rechecked.", "eventProfileLimitations": APPLICABILITY}
    suite["restoredCases"], suite["restoredPaths"], suite["restoredFixtures"] = [], [], {}
    def delta(base, changed, path=None):
        path = path or []
        if base == changed:
            return []
        if isinstance(base, list) and isinstance(changed, list) and len(base) == len(changed):
            return [edit for i, (a, b) in enumerate(zip(base, changed)) for edit in delta(a, b, path+[i])]
        if isinstance(base, dict) and isinstance(changed, dict):
            edits = [{"op": "remove", "path": path+[k]} for k in base if k not in changed]
            for k, value in changed.items():
                if k not in base:
                    edits.append({"op": "set", "path": path+[k], "value": deepcopy(value)})
                else:
                    edits += delta(base[k], value, path+[k])
            return edits
        return [{"op": "set", "path": path, "value": deepcopy(changed)}]
    for nid in sorted(restored_ids, key=lambda s: int(s[1:])):
        card = cards[nid]
        c = fixture(card["domain"], card["sourceFacet"], card["assessmentKind"], seeds)
        ref = card["domain"]+":"+card["assessmentKind"]
        suite["restoredFixtures"].setdefault(ref, deepcopy(c))
        for outcome in ("yes", "no", "unknown"):
            suite["restoredCases"].append({"id": f"{nid}-{outcome}", "nodeId": nid, "evidenceRef": ref,
                "evidenceEdits": delta(suite["restoredFixtures"][ref], variant(c, card["assessmentKind"], outcome)), "expectedAnswer": outcome})
    cases = {c["id"]: c for c in suite["restoredCases"]}
    successors = {(e["source"], e["decision"]): e["target"] for e in edges}
    for domain in criteria["domains"]:
        entry = min((nid for nid in entries if nid in restored_ids and cards[nid]["domain"] == domain and cards[nid]["stage"] == "detect"), key=lambda s: int(s[1:]))
        for initial in ("yes", "no", "unknown"):
            trace, current = [], entry
            while True:
                outcome = initial if current == entry else "yes"
                trace.append([current, outcome])
                if by_id[current]["archetype"] == "terminal":
                    break
                current = successors[current, outcome]
            evidence_by_node = {}
            for nid, outcome in trace:
                # Use a single source focus throughout; adapters never replace it
                # with the base node's historical source facet.
                facet = cards[entry]["sourceFacet"]
                if nid in restored_ids:
                    c = deepcopy(cases[f"{nid}-{outcome}"])
                else:
                    kind = {"primaryValidation": "provenance", "classification": "hypothesis", "scope": "scope-bound",
                            "correlation": "identifier-relation", "attribution": "technical-source", "impact": "metric-change",
                            "assessed": "retention", "unresolved": "retention", "refuted": "retention"}[cards[nid]["role"]]
                    example = fixture(domain, facet, kind, seeds)
                    ref = domain+":base:"+kind
                    suite["restoredFixtures"].setdefault(ref, deepcopy(example))
                    c = {"nodeId": nid, "evidenceRef": ref, "evidenceEdits": delta(suite["restoredFixtures"][ref], example)}
                if by_id[nid]["archetype"] == "terminal":
                    c["evidenceEdits"].append({"op": "set", "path": ["focus"], "value": facet})
                    retained = [{"nodeId": source, "answer": a, "method": "retain independent supplied assessment", "evidenceRefs": ["authored:route-observation"],
                        "subjects": deepcopy(seeds[domain]["bindings"]), "interval": deepcopy(seeds[domain]["interval"]), "hypothesisId": seeds[domain]["analysis"]["hypothesis"]["hypothesisId"],
                        "rationale": "Retain the declared bounded assessment and its limitation", "limitations": ["Author-side example; no verified incident evidence"]} for source, a in trace[:-1]]
                    c["evidenceEdits"].append({"op": "set", "path": ["retention", "assessments"], "value": retained})
                    if cards[nid]["role"] == "assessed":
                        prerequisites = []
                        for prerequisite in (criteria["domains"][domain]["classification"][0], criteria["domains"][domain]["scope"][0]):
                            prerequisites.append({**deepcopy(retained[0]), "nodeId": prerequisite, "answer": "yes",
                                "method": "Separately rechecked supplied matching record, accepted provenance, explicit hypothesis and bounded scope",
                                "rationale": "A prerequisite assessment, distinct from the optional question's retained answer"})
                        c["evidenceEdits"].append({"op": "set", "path": ["retention", "prerequisiteAssessments"], "value": prerequisites})
                evidence_by_node[nid] = c
            suite["restoredPaths"].append({"id": f"{domain.lower()}-restored-route-{initial}", "domain": domain, "entry": entry,
                "evidenceKind": "authored-normalized-fixture", "evidenceByNode": evidence_by_node, "expectedTrace": trace})
    original_edges = defaultdict(list)
    for e in original["edges"]:
        original_edges[e["source"]].append(e)
    original_nodes = {n["id"]: n for n in original["nodes"]}
    positions = {n["id"]: i for i, n in enumerate(graph["nodes"])}
    for row in rows:
        nid = row["sourceId"]
        row["targetDefinitionRefs"][0] = f"tensor.core.graph.json#/nodes/{positions[nid]}"
        row["sourceRoutes"] = [{"decision": e["decision"], "targetId": e["target"], "targetDomain": original_nodes[e["target"]]["category"],
            "targetStage": original_nodes[e["target"]]["archetype"]} for e in original_edges[nid]]
        if any(r["targetDomain"] != row["sourceCategory"] for r in row["sourceRoutes"]):
            row["issues"].append("Original route crossed domain without an explicit bound evidentiary relationship")
        if any(STAGES.index(r["targetStage"]) > STAGES.index(row["sourceArchetype"])+1 for r in row["sourceRoutes"] if r["decision"] == "yes"):
            row["issues"].append("Original positive route bypassed an intervening evidence stage")
        row["targetRoutes"] = [{"decision": e["decision"], "targetId": e["target"]} for e in edges if e["source"] == nid]
        if nid in restored_ids:
            row["scenarioRefs"] += [c["id"] for c in suite["restoredPaths"] if any(s[0] == nid for s in c["expectedTrace"])]
    analysis = {"format": "tensor-original-question-author-review", "version": 1, "graphVersion": VERSION, "graphSha256": criteria["graphSha256"],
        "author": "TENSOR Standards Consortium authoring workstream", "reviewDate": "2026-10-12", "method": "Explicit source-family analysis and per-ID accounting, followed by separate AI-assisted route review and independently authored seven-domain evidence tests. No external reviewer sign-off.", "challengeReview": "reviews/2026-10-12-independent-review/README.md",
        "source": {"path": str(original_path.relative_to(ROOT)), "sha256": source_sha, "version": original["version"]},
        "scope": "All 588 original IDs reviewed against explicit source prompt families. These are author editorial dispositions, not independent approval or an equivalence proof. No original bytes or schema changed.",
        "summary": {"originalQuestions": len(rows), "distinctSourcePrompts": len(duplicates), "repeatedPromptGroups": sum(len(v)>1 for v in duplicates.values()),
            "retainedPriorRepairs": len(base_ids & {n["id"] for n in original["nodes"]}), "restoredQuestions": len(restored_ids), "repairQuestions": len(base_ids - {n["id"] for n in original["nodes"]}),
            "independentlyApprovedDispositions": 0, "assessmentKinds": dict(sorted(Counter(r["assessmentKind"] for r in rows).items()))}, "questions": rows}
    return graph, criteria, suite, analysis


def main():
    graph, criteria, suite, analysis = build()
    outputs = {ROOT/"drafts/core/tensor.core.graph.json": graph, ROOT/"drafts/core/entry-evidence-criteria.json": criteria,
        ROOT/"drafts/core/scenarios/entry-evidence-cases.json": suite, REVIEW/"analysis.json": analysis,
        ROOT/"drafts/core/source/entry_nodes.json": {"version": VERSION, "entryNodeIds": graph["entryNodeIds"], "fanInExceptionNodeIds": []}}
    byte_outputs = {p: encoded(data) for p, data in outputs.items()}
    byte_outputs[ROOT/"drafts/core/source/nodes.jsonl"] = b"".join((json.dumps(n, ensure_ascii=True)+"\n").encode() for n in graph["nodes"])
    byte_outputs[ROOT/"drafts/core/source/edges.jsonl"] = b"".join((json.dumps(e, ensure_ascii=True)+"\n").encode() for e in graph["edges"])
    for path, data in byte_outputs.items():
        if "--check" in sys.argv:
            if path.read_bytes() != data:
                raise SystemExit(f"Restoration output is stale: {path.relative_to(ROOT)}")
        else:
            path.write_bytes(data)
    print(f"Author review: 588 original IDs; active draft {len(graph['nodes'])} questions, {len(graph['edges'])} routes, {len(graph['entryNodeIds'])} explicit entries. Independent approval remains pending.")


if __name__ == "__main__":
    main()
