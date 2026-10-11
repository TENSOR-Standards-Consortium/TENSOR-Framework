# Core Math Assurance (0.20261011a)

Generated: `2026-10-11T16:12:34Z`

## Scorecard
| Metric | Value |
| --- | --- |
| Overall score | 95.09 |
| Coverage score | 100.00 |
| Routing score | 100.00 |
| Information score | 100.00 |
| Robustness score | 75.43 |

## Publish Gates
Overall: **FAIL**

| Gate | Metric | Rule | Value | Result |
| --- | --- | --- | --- | --- |
| dag_pass | graph_theory.dagPass | == True | True | pass |
| full_reachability | graph_theory.reachableRatio | >= 1.0 | 1 | pass |
| branch_totality | graph_theory.branchCompletenessRatio | >= 1.0 | 1 | pass |
| cross_domain_pivots | quality.crossDomainRatio | >= 0.25 | 0.531469 | pass |
| coverage_score | optimization.coverageScore | >= 100.0 | 100 | pass |
| routing_score | optimization.routingScore | >= 100.0 | 100 | pass |
| robustness_score | optimization.robustnessScore | >= 85.0 | 75.4286 | fail |
| targeted_resilience | robustness.targetedReachabilityAt5Percent | >= 0.85 | 0.754286 | fail |
| routing_centralization | centrality.betweennessCentralization | <= 0.02 | 0.026993 | fail |
| information_gain | information_theory.negativeInformationGainNodeCount | <= 0 | 0 | pass |
| overall_score | optimization.overallScore | >= 80.0 | 95.08572 | pass |

## Recommendations
- Increase alternate pathways around central pivots to improve targeted-failure resilience.

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
| matrixRank | 6 |
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
| expectedStepsFromEntriesMean | 2.226337 |
| expectedStepsFromEntriesP90 | 2.22588 |
| absorptionDomainEntropy | 2.806633 |

### Information Theory
| Metric | Value |
| --- | --- |
| meanInformationGain | 0.817634 |
| negativeInformationGainNodeCount | 0 |

### Flow / Cut Theory
| Metric | Value |
| --- | --- |
| entryToTerminalEdgeConnectivity | 21 |
| entryToTerminalMinCutEdgeCount | 21 |

### Centrality Theory
| Metric | Value |
| --- | --- |
| betweennessCentralization | 0.026993 |
| betweennessGini | 0.480064 |

### Robustness / Percolation
| Metric | Value |
| --- | --- |
| targetedReachabilityAt5Percent | 0.754286 |

### Multi-objective Optimization
| Metric | Value |
| --- | --- |
| overallScore | 95.08572 |

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
| triangulationNodeRatio | 0.797203 |

### Directed Topology Proxies
| Metric | Value |
| --- | --- |
| mergeNodeCount | 67 |
| diamondMotifCount | 104 |


## Assessment boundary

Structural and simulated authoring checks; not release conformance or investigative effectiveness.

- `drafts/core/tensor.core.graph.json`: SHA-256 `ed390a26b887e560f2224bbd577ba282e2fc331bb5c1293f6002413da7a72a0d`
- `drafts/core/source/entry_nodes.json`: SHA-256 `b9601ac3d2ca1a2d4b62ea823ad60b46d4acfe5b68534aae04db24a6ac51d20c`
