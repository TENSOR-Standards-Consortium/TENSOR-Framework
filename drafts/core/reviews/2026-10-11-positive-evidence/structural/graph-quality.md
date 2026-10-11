# Core Graph Quality Report (0.20261011b)

Generated: `2026-10-11T17:03:03Z`
Status: **PASS**

## Summary
| Metric | Value |
| --- | --- |
| Nodes | 103 |
| Edges | 225 |
| Non-terminal nodes | 75 |
| Terminal nodes | 28 |
| Entry nodes | 7 |
| Reachable nodes | 103 |
| Cross-domain edges | 0 |
| Cross-domain ratio | 0.0000 |
| Max fan-in | 12 |

## Domain Counts
| Domain | Count |
| --- | --- |
| Application | 15 |
| Cloud | 15 |
| Email | 15 |
| File | 15 |
| Host | 15 |
| Identity | 13 |
| Network | 15 |

## Archetype Counts
| Archetype | Count |
| --- | --- |
| detect | 14 |
| validate | 14 |
| classify | 13 |
| scope | 13 |
| correlate | 7 |
| attribute | 7 |
| impact | 7 |
| terminal | 28 |

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
| Cross-domain ratio >= threshold | fail |
| Branch determinism violations | 0 |
| Yes-edge semantic progression violations | 0 |
| Early-stage cross-domain yes violations | 0 |

## Warnings
- Cross-domain edge ratio 0.0000 is below required minimum 0.25.
- Synthetic optimization gates failed: cross_domain_pivots, routing_score, robustness_score, targeted_resilience, routing_centralization, overall_score. Original gate failures remain in math-assurance; this is not publication approval.


## Assessment boundary

Structural and simulated authoring checks; not release conformance or investigative effectiveness.

- `drafts/core/tensor.core.graph.json`: SHA-256 `7d64a8fdf2d33861e6a06cfcb7daea8435cb5ed74acbb1df8b55ee60588b7101`
- `drafts/core/source/entry_nodes.json`: SHA-256 `f4c50d88d48478047a25fd8bda7a3897b9b9a2cde8344a5590f025d3ab06625a`
