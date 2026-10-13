# TENSOR Core Compatibility Policy

## Scope and governance
- `releases/core/**` is the normative Core release surface for machine consumers.
- Core investigative semantics are governed by the TENSOR standards process and must stay vendor-neutral.
- Vendor, product, and organization-specific logic must be implemented as overlays in extension layers (`extensions/`, `vendors/`, `orgs/`) and must not rewrite Core meaning.

## Layer model
- **Core layer**: canonical, stable investigative primitives and relationships.
- **Overlay layers**: additive constraints, fields, mappings, and workflow data for extensions/vendors/orgs.
- Overlay layers may reference Core nodes/edges and add metadata, but they cannot remove or redefine Core semantics.
- Core releases must provide explicit investigation entry points (`entryNodeIds`), and Core nodes must be reachable from at least one entry point.
- Core is a routing/semantic backplane; concrete vendor investigative workflows are overlay responsibilities.
- Extension metadata keys in Core (`extensions`) must be namespaced (`<namespace>:<field>`). Non-namespaced business/process fields belong in overlays.
- Published graph versions retain their original topology and validation contract. The working draft supports several targets per `yes/no/unknown` outcome, cross-domain leads, convergence and cycles with fresh question instances. A decision records explicit selections; matching guards do not automatically traverse every route. Terminal questions have no outgoing routes.
- Core node archetype taxonomy is fixed for v0.20260206c+ and evolves per release notes (v0.20260206e+: `detect`, `validate`, `classify`, `scope`, `correlate`, `attribute`, `impact`, `terminal`).
- In Core, `terminal` denotes path termination semantics, not case workflow closure semantics.

## Versioning
- Version format: `<MAJOR>.<YYYYMMDD>[letter]`.
- Non-breaking Core changes publish a new date/revision within the current major.
- Breaking Core changes increment `MAJOR` and publish updated schema + graph artifacts.
- Release metadata is published in `releases/manifest.json`; `latest*` pointers identify the default client target.

## Compatibility expectations
- The routing repair is an unpublished draft behavior change using the unchanged graph schema. Consumers that assume one target per outcome or an acyclic graph must adapt before adopting it. A schema-valid file alone does not establish behavioral compatibility. No `latest` pointer or released artifact is advanced by this repair; release versioning and migration remain subject to review.
- Clients that pin explicit versions (`graphVersion`, `schemaVersion`) must receive immutable artifacts.
- `latest/` files are convenience pointers and always mirror the versions declared by `releases/manifest.json`.
- Backward-compatible fields should be additive and optional whenever possible.

## Deprecation policy
- A deprecated Core element must be marked in release notes before removal in a later major.
- Deprecated elements remain available for at least one subsequent non-breaking release cycle.
- Removals/behavioral changes require a major version bump and explicit migration notes.

## Conformance
- Release contract conformance fixtures are in `standards/conformance/`.
- CI must validate manifest shape, version formatting, latest pointer integrity, and checksum integrity before merge.
- For releases `>= v0.20260206d`, CI also requires mathematical assurance artifacts per version plus `latest` and `history` math report pointers under `releases/core/reports/`.
