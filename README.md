# TENSOR Framework repository

Welcome to the public home of the **TENSOR Framework**. This repository holds the working source (“drafts”) and the immutable versioned releases of the Framework’s core definitions as well as optional extensions provided by the community.

## What is TENSOR?

* **TENSOR Framework** – A graph based security operations methodology that models every security fact as time‑series data. It aims to give analysts an extensible, technology‑neutral way to capture, correlate and respond to events.
* **TENSOR Standards Consortium** – A volunteer community that stewards the Framework, defines version policy and reviews proposed extensions. The group is currently organising and has not yet been incorporated.

## Repository layout

```
TENSOR-Framework/
├── drafts/                 # files that humans edit
│   ├── core/               # canonical schema + graph
│   ├── extensions/         # consortium‑maintained add‑ons
│   ├── vendors/<vendor>/<pack>/
│   └── orgs/<org>/<module>/
│       └── tensor.<...>.(schema|graph).json
└── releases/               # immutable snapshots (add manually for now)
    ├── core/v<VER>/
    ├── extensions/<ext>/v<VER>/
    ├── vendors/<vendor>/<pack>/v<VER>/
    └── orgs/<org>/<module>/v<VER>/
        └── tensor.<...>.(schema|graph).json
```

### Version string

`<VER>` follows `MAJOR.YYYYMMDD[letter]` (example: `1.20250910`). The same string appears inside each JSON as `"tensorVersion"` and in the Git tag `core-v1.20250910` or `cloud-v1.20250712`.

### File‑name conventions

| Draft files                                | Purpose                                          |
| ------------------------------------------ | ------------------------------------------------ |
| `tensor.<namespace>.<package>.schema.json` | JSON Schema that extends Core.                   |
| `tensor.<namespace>.<package>.graph.json`  | Graph‑ontology file connecting the new concepts. |

| Release snapshots *(inside `releases/…/v<VER>/`)* | Purpose                              |
| ------------------------------------------------- | ------------------------------------ |
| `tensor.<namespace>.<package>.schema.json`        | Immutable schema for version `<VER>` |
| `tensor.<namespace>.<package>.graph.json`         | Immutable graph for version `<VER>`  |

* **`<namespace>`** = `core`, an official extension name (`cloud`), a vendor slug (`crowdstrike`), or an org slug (`acmebank`).
* **`<package>`**   = specific pack or module (`xdr`, `fraud`, etc.).
* File names never contain the version string — versioning is conveyed by the enclosing `v<VER>` folder or by adding `. <VER>.json` if you prefer flat snapshots later.

`<VER>` follows `MAJOR.YYYYMMDD[letter]` (example: `1.20250910`). The same string appears inside each JSON as `"tensorVersion"` and in the Git tag `core-v1.20250910` or `cloud-v1.20250712`.

### Editing basics

1. Make changes only inside `drafts/`.
2. Update `"tensorVersion"` in both the schema and graph when you make a release breaking change (increment `MAJOR`) or a non‑breaking improvement (same `MAJOR`, new date).
3. When you create a release, copy the entire draft folder into `releases/<…>/v<VER>/` and tag the commit manually. (Automation will be added later.)

### Contributing extensions

* **Official extensions** live under `drafts/extensions/` and mirror Core rules.
* **Vendor packs** must sit one directory deeper under `drafts/vendors/<vendor>/<pack>/`.
* **Org overlays** follow the same pattern in `drafts/orgs/<org>/<module>/`.

Each layer supplies its own schema and graph file that extend, but do not modify, the Core definitions.

For detailed contribution guidelines, version policy and governance minutes see the forthcoming `CONTRIBUTING.md` and `GOVERNANCE.md` documents.
