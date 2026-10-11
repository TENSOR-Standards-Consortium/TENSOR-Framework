# Core Graph Quality Report (0.20261011a)

Generated: `2026-10-11T16:12:34Z`
Status: **PASS**

## Summary
| Metric | Value |
| --- | --- |
| Nodes | 184 |
| Edges | 429 |
| Non-terminal nodes | 143 |
| Terminal nodes | 41 |
| Entry nodes | 7 |
| Reachable nodes | 184 |
| Cross-domain edges | 228 |
| Cross-domain ratio | 0.5315 |
| Max fan-in | 11 |

## Domain Counts
| Domain | Count |
| --- | --- |
| Application | 28 |
| Cloud | 27 |
| Email | 29 |
| File | 22 |
| Host | 29 |
| Identity | 25 |
| Network | 24 |

## Archetype Counts
| Archetype | Count |
| --- | --- |
| detect | 14 |
| validate | 14 |
| classify | 13 |
| scope | 13 |
| correlate | 25 |
| attribute | 38 |
| impact | 26 |
| terminal | 41 |

## Entry Coverage By Domain
| Domain | Has Entry |
| --- | --- |
| Application | yes |
| Cloud | yes |
| Email | yes |
| File | yes |
| Host | yes |
| Identity | yes |
| Network | yes |

## Checks
| Check | Result |
| --- | --- |
| All nodes reachable from entries | pass |
| DAG | pass |
| Cross-domain ratio >= threshold | pass |
| Branch determinism violations | 0 |
| Yes-edge semantic progression violations | 0 |
| Early-stage cross-domain yes violations | 0 |

## Warnings
- Synthetic optimization gates failed: robustness_score, targeted_resilience, routing_centralization. Original gate failures remain in math-assurance; this is not publication approval.


## Assessment boundary

Structural and simulated authoring checks; not release conformance or investigative effectiveness.

- `drafts/core/tensor.core.graph.json`: SHA-256 `ed390a26b887e560f2224bbd577ba282e2fc331bb5c1293f6002413da7a72a0d`
- `drafts/core/source/entry_nodes.json`: SHA-256 `b9601ac3d2ca1a2d4b62ea823ad60b46d4acfe5b68534aae04db24a6ac51d20c`
