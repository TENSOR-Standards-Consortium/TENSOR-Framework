# Core Math Assurance (0.20261011b)

Generated: `2026-10-11T17:43:33Z`

## Scorecard
| Metric | Value |
| --- | --- |
| Overall score | 70.33 |
| Coverage score | 100.00 |
| Routing score | 80.00 |
| Information score | 0.00 |
| Robustness score | 81.63 |

## Authoring Acceptance
Structure and supplied evidence-profile checks only; not release authorization or independent investigative validation.
Overall: **PASS**

| Gate | Metric | Rule | Value | Result |
| --- | --- | --- | --- | --- |
| graph_authoring |  | pass | True | pass |
| policy_catalog |  | pass | True | pass |
| dag_pass | graph_theory.dagPass | == True | True | pass |
| full_reachability | graph_theory.reachableRatio | >= 1.0 | 1 | pass |
| branch_totality | graph_theory.branchCompletenessRatio | >= 1.0 | 1 | pass |
| coverage_score | optimization.coverageScore | >= 100.0 | 100 | pass |
| evidence_cards |  | pass | True | pass |
| evidence_transitions |  | pass | True | pass |
| scenario_agreement |  | pass | True | pass |
| scenario_coverage |  | pass | True | pass |

## Historical Reference Thresholds (diagnostic)
Original values and thresholds are retained; unmet reference thresholds do not block current authoring acceptance. See standards/graph-assurance-policy.md.
| Reference | Value | Rule | Met |
| --- | --- | --- | --- |
| dag_pass | True | == True | True |
| full_reachability | 1.0 | >= 1.0 | True |
| branch_totality | 1.0 | >= 1.0 | True |
| cross_domain_pivots | 0.0 | >= 0.25 | False |
| coverage_score | 100.0 | >= 100.0 | True |
| routing_score | 80.0 | >= 100.0 | False |
| robustness_score | 81.6327 | >= 85.0 | False |
| targeted_resilience | 0.816327 | >= 0.85 | False |
| routing_centralization | 0.029056 | <= 0.02 | False |
| information_gain | 0 | <= 0 | True |
| overall_score | 70.32654 | >= 80.0 | False |

## Recommendations
- Use explicit evidence cards, safe transition checks and discriminating scenarios for authoring acceptance; topology scores do not establish investigative quality.
- Review high-betweenness questions and removal sensitivity for maintenance impact; never bypass required evidence validation to improve a score.

## Theory Coverage
| Theory | Purpose |
| --- | --- |
| Graph Theory | Structural soundness: DAG, reachability, deterministic decision routing. |
| Matrix Theory | Coverage completeness and balance across Domain x Archetype. |
| Set Cover / Hitting Set | Minimal entry-path basis required to cover investigative feature space. |
| Markov Chain | Expected routing length and absorbing-outcome distribution under branch probabilities. |
| Information Theory | Terminal-domain label entropy under uniform branches; not evidentiary uncertainty reduction. |
| Flow / Cut Theory | Bottleneck and fault-tolerance identification via connectivity cuts. |
| Centrality Theory | Shortest-path betweenness and maximum share of total betweenness; not normalized Freeman graph centralization. |
| Robustness / Percolation | Synthetic reachability after deleting questions; not missing-evidence handling or permission to bypass a prerequisite. |
| Multi-objective Optimization | Historical weighted proxy scorecard; uncalibrated and not an acceptance criterion. |
| Formal Methods Checks | Machine-checkable invariants for safety and liveness-style properties. |
| Bayesian / Causal Readiness | Readiness proxies for probabilistic confidence and causal interpretation overlays. |
| Directed Topology Proxies | Higher-order path-complex and merge-pattern shape indicators. |

## Key Metrics
### Graph Theory
| Metric | Value |
| --- | --- |
| branchCompletenessRatio | 1 |
| reachableRatio | 1 |
| rootCount | 7 |
| dagPass | True |

### Matrix Theory
| Metric | Value |
| --- | --- |
| matrixRank | 2 |
| nonZeroCellRatio | 1 |

### Set Cover / Hitting Set
| Metric | Value |
| --- | --- |
| configuredEntryCount | 7 |
| minimalEntrySetSizeByGreedy | 7 |
| entryCoverageRatio | 1 |

### Markov Chain
| Metric | Value |
| --- | --- |
| expectedStepsFromEntriesMean | 2.024691 |
| expectedStepsFromEntriesP90 | 2.024691 |
| absorptionDomainEntropy | 2.807355 |

### Information Theory
| Metric | Value |
| --- | --- |
| meanInformationGain | 0 |
| negativeInformationGainNodeCount | 0 |

### Flow / Cut Theory
| Metric | Value |
| --- | --- |
| entryToTerminalEdgeConnectivity | 21 |
| entryToTerminalMinCutEdgeCount | 21 |

### Centrality Theory
| Metric | Value |
| --- | --- |
| betweennessCentralization | 0.029056 |
| betweennessGini | 0.504854 |

### Robustness / Percolation
| Metric | Value |
| --- | --- |
| targetedReachabilityAt5Percent | 0.816327 |

### Multi-objective Optimization
| Metric | Value |
| --- | --- |
| overallScore | 70.32654 |

### Formal Methods Checks
| Metric | Value |
| --- | --- |
| AG_branchTotality | True |
| AG_acyclic | True |
| AG_entryEventuallyTerminal | True |

### Bayesian / Causal Readiness
| Metric | Value |
| --- | --- |
| fullArchetypeChainDomainCount | 7 |
| triangulationNodeRatio | 0 |

### Directed Topology Proxies
| Metric | Value |
| --- | --- |
| mergeNodeCount | 41 |
| diamondMotifCount | 605 |


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
