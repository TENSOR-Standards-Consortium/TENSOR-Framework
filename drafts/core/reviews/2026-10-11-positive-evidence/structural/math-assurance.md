# Core Math Assurance (0.20261011b)

Generated: `2026-10-11T17:05:34Z`

## Scorecard
| Metric | Value |
| --- | --- |
| Overall score | 70.33 |
| Coverage score | 100.00 |
| Routing score | 80.00 |
| Information score | 0.00 |
| Robustness score | 81.63 |

## Publish Gates
Overall: **FAIL**

| Gate | Metric | Rule | Value | Result |
| --- | --- | --- | --- | --- |
| dag_pass | graph_theory.dagPass | == True | True | pass |
| full_reachability | graph_theory.reachableRatio | >= 1.0 | 1 | pass |
| branch_totality | graph_theory.branchCompletenessRatio | >= 1.0 | 1 | pass |
| cross_domain_pivots | quality.crossDomainRatio | >= 0.25 | 0 | fail |
| coverage_score | optimization.coverageScore | >= 100.0 | 100 | pass |
| routing_score | optimization.routingScore | >= 100.0 | 80 | fail |
| robustness_score | optimization.robustnessScore | >= 85.0 | 81.6327 | fail |
| targeted_resilience | robustness.targetedReachabilityAt5Percent | >= 0.85 | 0.816327 | fail |
| routing_centralization | centrality.betweennessCentralization | <= 0.02 | 0.029056 | fail |
| information_gain | information_theory.negativeInformationGainNodeCount | <= 0 | 0 | pass |
| overall_score | optimization.overallScore | >= 80.0 | 70.32654 | fail |

## Recommendations
- Current optimization profile is balanced; continue trend monitoring across releases.

## Theory Coverage
| Theory | Purpose |
| --- | --- |
| Graph Theory | Structural soundness: DAG, reachability, deterministic decision routing. |
| Matrix Theory | Coverage completeness and balance across Domain x Archetype. |
| Set Cover / Hitting Set | Minimal entry-path basis required to cover investigative feature space. |
| Markov Chain | Expected routing length and absorbing-outcome distribution under branch probabilities. |
| Information Theory | Uncertainty reduction and information gain across investigation decisions. |
| Flow / Cut Theory | Bottleneck and fault-tolerance identification via connectivity cuts. |
| Centrality Theory | Routing concentration and over-dependence detection. |
| Robustness / Percolation | Resilience under random and adversarial node removals. |
| Multi-objective Optimization | Unified scorecard for coverage, routing, robustness, and information quality. |
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
