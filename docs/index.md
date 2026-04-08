---
layout: home
hero:
  name: dwg2json
  text: DWG to Canonical JSON
  tagline: Open-source DWG semantic deparser with xref-bound composition semantics
  image:
    src: /logo.svg
    alt: dwg2json
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/VicLuZY/dwg2json

features:
  - icon: 📄
    title: One DWG In, One JSON Out
    details: Every parse produces exactly one canonical JSON file per root DWG. No sidecar files, no multi-output bundles.
  - icon: 🔗
    title: Xref Composition
    details: External references are treated as bound composition dependencies. Host and xref geometry are placed into shared coordinate frames.
  - icon: ⚠️
    title: Missing Xref Tracking
    details: Missing, unresolved, and broken xrefs are explicitly reported in completeness fields, missing-reference records, and warnings.
  - icon: 📊
    title: Confidence Heuristics
    details: A monotonic confidence score aggregates penalties for missing xrefs, parse failures, cycles, and unsupported content.
  - icon: 🔌
    title: Pluggable Backends
    details: Decode behind a stable DwgBackend interface. LibreDWG + ezdxf ships built-in. Swap or extend without changing the pipeline.
  - icon: 💻
    title: CLI & Python API
    details: Typer-based CLI for parse, introspection, schema dump, and validation. Dwg2JsonParser for programmatic use.
---
