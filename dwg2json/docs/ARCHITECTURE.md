# dwg2json architecture

## Design center

One root DWG in.
One canonical JSON out.

## Two-layer truth model

### Source truth

Each DWG source is preserved as a source-local record with its own entities, blocks, layers, layouts, warnings, and raw xref declarations.

### Composition truth

A composition binds host and xref sources together in the same coordinate frame so downstream reasoning can operate on the combined scene.

## Why xref binding is first-class

An overlay may be meaningless by itself.
A background xref may carry the spatial anchors.
The parser therefore has to express the composed view, not just the isolated files.

## Missing dependency model

Broken xrefs are normal.
The canonical JSON must preserve that fact.

Consequences:
- xref graph still records the dependency
- source record still exists
- source parse status becomes missing or unresolved
- composition completeness becomes partial
- top-level completeness becomes partial or incomplete
