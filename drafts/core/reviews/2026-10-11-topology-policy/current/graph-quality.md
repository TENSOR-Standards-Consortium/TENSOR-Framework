# Core Graph Quality Report (0.20261011b)

Generated: `2026-10-11T17:43:33Z`
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
| Historical cross-domain reference (diagnostic) | not met |
| Branch determinism violations | 0 |
| Yes-edge semantic progression violations | 0 |
| Early-stage cross-domain yes violations | 0 |

## Warnings
- Historical cross-domain reference ratio 0.0000 is below 0.25; diagnostic only under the current graph assurance policy.
- Historical diagnostic thresholds not met: cross_domain_pivots, overall_score, robustness_score, routing_centralization, routing_score, targeted_resilience. Values remain visible; no score was recalibrated and this is not release authorization.


## Assessment boundary

Structural and simulated authoring checks; not release conformance or investigative effectiveness.

- `drafts/core/tensor.core.graph.json`: SHA-256 `8b83f19f83d7d796c96b404d37f4ae093d36415b35123602133f34cad5c172be`
- `drafts/core/source/entry_nodes.json`: SHA-256 `f4c50d88d48478047a25fd8bda7a3897b9b9a2cde8344a5590f025d3ab06625a`
- `drafts/core/entry-evidence-criteria.json`: SHA-256 `0595cdd6a27c44ca87839981a2b4b93d51452a234a7af8d400da68c900cf1e49`
- `drafts/core/scenarios/entry-evidence-cases.json`: SHA-256 `13541a42427aa3b61a1bd2ae58e1913dbd04d40049085c1826ef503dc4026f69`
- `standards/graph-assurance-policy.md`: SHA-256 `bd45e7caa0c6a63d23d25e0efc7d50f2c1e3d1fd5a6622749e963237ed3c242b`
- `scripts/graph_assurance_policy.py`: SHA-256 `395562a580510d3f55f4e8a8ee56e30af61c1d1452151b0b202d535c85dddc4a`
- `scripts/core_graph_pipeline.py`: SHA-256 `eea70a4dc645ed9c0b336dbe06daa39b7a672cda6e9a21bdd5978b48320fc452`
- `scripts/core_graph_math_assurance.py`: SHA-256 `ac5c3e22f6914584261e5a26c0bbae284d4651d201979e56ba50cac4026f7d87`
- `scripts/evaluate_entry_scenarios.py`: SHA-256 `fa2380d410f427ce049281e8db4fddd9f954921224f2bbbfa87064c5120aafea`
- `scripts/lint_core_graph_quality.py`: SHA-256 `ba64c3033f1b36088769f8172ffe9f18cf859a6aa63a92e43fc9550d6e6afa34`
