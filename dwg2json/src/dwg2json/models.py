"""Canonical data models for dwg2json.

Every JSON output produced by the package is a serialisation of
``DwgJsonDocument``.  Pydantic v2 is used for schema enforcement,
serialisation, and eventual JSON-Schema generation.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "BoundingBox",
    "BlockDefinition",
    "Composition",
    "CompletenessReport",
    "DwgJsonDocument",
    "Entity",
    "InterpretationConfidence",
    "Layer",
    "Layout",
    "MissingReference",
    "ParseOptions",
    "ParseResult",
    "ParserInfo",
    "SourceBinding",
    "SourceDocument",
    "WarningRecord",
    "XrefBindingMetadata",
    "XrefGraph",
    "XrefGraphEdge",
    "XrefGraphNode",
]

# ---------------------------------------------------------------------------
# Shared type aliases (Literal unions used as enums)
# ---------------------------------------------------------------------------

InterpretationStatus = Literal["complete", "partial", "degraded", "failed"]
ParseStatus = Literal["parsed", "partial", "unresolved", "missing", "failed"]
XrefMode = Literal["attach", "overlay", "unknown"]
CompletenessStatus = Literal["complete", "partial", "incomplete"]
CompositionCompleteness = Literal["complete", "partial", "missing_dependencies"]
Severity = Literal["info", "warning", "error"]
MissingXrefPolicy = Literal["record", "error"]
MissingSeverity = Literal["critical", "high", "medium", "low"]

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


class BoundingBox(BaseModel):
    min_x: float
    min_y: float
    min_z: float = 0.0
    max_x: float
    max_y: float
    max_z: float = 0.0


class Point3D(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


# ---------------------------------------------------------------------------
# Provenance / parser info
# ---------------------------------------------------------------------------


class ParserInfo(BaseModel):
    name: str = "dwg2json"
    version: str = "0.1.0"
    backend: str
    backend_version: str | None = None
    timestamp: str = Field(default_factory=lambda: _dt.datetime.now(_dt.UTC).isoformat())


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------


class WarningRecord(BaseModel):
    code: str
    message: str
    severity: Severity = "warning"
    source_id: str | None = None
    handle: str | None = None


# ---------------------------------------------------------------------------
# Layer / Layout / Block
# ---------------------------------------------------------------------------


class Layer(BaseModel):
    id: str
    name: str
    color_index: int | None = None
    color_rgb: str | None = None
    line_type: str | None = None
    line_weight: int | None = None
    is_frozen: bool = False
    is_locked: bool = False
    is_off: bool = False
    plot_style_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Layout(BaseModel):
    id: str
    name: str
    is_model_space: bool = False
    tab_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BlockDefinition(BaseModel):
    id: str
    name: str
    is_xref: bool = False
    xref_path: str | None = None
    origin: Point3D | None = None
    entity_ids: list[str] = Field(default_factory=list)
    is_anonymous: bool = False
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Entity – the universal canonical entity
# ---------------------------------------------------------------------------


class Entity(BaseModel):
    """Canonical representation of a single DWG entity.

    Geometry is stored as a type-specific payload dict so that every entity
    kind can carry its own native fields (e.g. ``center``/``radius`` for
    CIRCLE, ``vertices`` for LWPOLYLINE) without a combinatorial explosion
    of optional top-level fields.
    """

    id: str
    source_id: str
    handle: str
    owner_handle: str | None = None
    type: str
    layer: str | None = None
    block_name: str | None = None
    layout: str | None = None
    color_index: int | None = None
    line_type: str | None = None
    line_weight: int | None = None
    is_visible: bool = True

    # Textual content (TEXT, MTEXT, ATTRIB, ATTDEF, DIMENSION, …)
    text: str | None = None

    # Block-insert fields
    insert_point: Point3D | None = None
    scale: Point3D | None = None
    rotation: float | None = None

    # Attributes (ATTRIB values attached to an INSERT)
    attributes: dict[str, Any] = Field(default_factory=dict)

    # Type-specific geometry payload
    geometry: dict[str, Any] = Field(default_factory=dict)

    bbox: BoundingBox | None = None
    transform: list[list[float]] | None = None
    composed_transform: list[list[float]] | None = None

    xdata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    warnings: list[WarningRecord] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Xref binding metadata (attached to a SourceDocument)
# ---------------------------------------------------------------------------


class XrefBindingMetadata(BaseModel):
    saved_path: str | None = None
    resolved_path: str | None = None
    mode: XrefMode = "unknown"
    transform: list[list[float]] | None = None
    insertion_point: Point3D | None = None
    scale: Point3D | None = None
    rotation: float | None = None
    exists: bool = True
    parsed: bool = True
    missing_reason: str | None = None
    candidate_paths: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Source document
# ---------------------------------------------------------------------------


class SourceDocument(BaseModel):
    """One parsed DWG/DXF source (root or xref child)."""

    id: str
    path: str
    resolved_path: str | None = None
    role: Literal["root", "xref"] = "root"
    exists: bool = True
    parsed: bool = True
    parse_status: ParseStatus = "parsed"
    parent_source_id: str | None = None
    xref_binding: XrefBindingMetadata | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    layers: list[Layer] = Field(default_factory=list)
    layouts: list[Layout] = Field(default_factory=list)
    blocks: list[BlockDefinition] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    warnings: list[WarningRecord] = Field(default_factory=list)
    raw_summary: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Xref graph
# ---------------------------------------------------------------------------


class XrefGraphNode(BaseModel):
    source_id: str
    path: str
    resolved_path: str | None = None
    exists: bool = True
    parsed: bool = True
    parse_status: ParseStatus = "parsed"
    parent_source_id: str | None = None
    depth: int = 0


class XrefGraphEdge(BaseModel):
    host_source_id: str
    target_source_id: str
    saved_path: str | None = None
    resolved_path: str | None = None
    mode: XrefMode = "unknown"
    transform: list[list[float]] | None = None
    insertion_point: Point3D | None = None
    exists: bool = True
    parsed: bool = True
    composition_required: bool = True


class XrefGraph(BaseModel):
    nodes: list[XrefGraphNode] = Field(default_factory=list)
    edges: list[XrefGraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Composition models
# ---------------------------------------------------------------------------


class SourceBinding(BaseModel):
    source_id: str
    parent_source_id: str | None = None
    placement_transform: list[list[float]] | None = None
    inherited_transform_chain: list[list[list[float]]] = Field(default_factory=list)
    mode: XrefMode = "unknown"
    included_entity_ids: list[str] = Field(default_factory=list)
    missing_dependency: bool = False


class Composition(BaseModel):
    id: str
    name: str
    root_source_id: str
    layout_name: str | None = None
    source_bindings: list[SourceBinding] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)
    relation_refs: list[str] = Field(default_factory=list)
    bbox: BoundingBox | None = None
    completeness_status: CompositionCompleteness = "complete"
    missing_source_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Missing references
# ---------------------------------------------------------------------------


class MissingReference(BaseModel):
    kind: str = "xref"
    requested_path: str | None = None
    normalized_path: str | None = None
    resolver_root: str | None = None
    parent_document_id: str | None = None
    host_handles: list[str] = Field(default_factory=list)
    impact_summary: str | None = None
    severity: MissingSeverity = "high"
    interpretation_impacted: bool = True


# ---------------------------------------------------------------------------
# Confidence heuristic
# ---------------------------------------------------------------------------


class ConfidenceFactor(BaseModel):
    factor: str
    penalty: float
    detail: str | None = None


class InterpretationConfidence(BaseModel):
    """Monotonic confidence heuristic (1.0 = full, 0.0 = no useful data)."""

    value: float = 1.0
    factors: list[ConfidenceFactor] = Field(default_factory=list)
    explanation: str | None = None

    def apply_penalty(self, factor: str, penalty: float, detail: str | None = None) -> None:
        self.factors.append(ConfidenceFactor(factor=factor, penalty=penalty, detail=detail))
        self.value = max(0.0, self.value - penalty)

    def recompute(self) -> None:
        self.value = max(0.0, 1.0 - sum(f.penalty for f in self.factors))
        if self.value >= 0.9:
            self.explanation = "High confidence: all dependencies resolved."
        elif self.value >= 0.6:
            self.explanation = "Moderate confidence: some dependencies missing or partially parsed."
        elif self.value >= 0.3:
            self.explanation = "Low confidence: significant missing dependencies or parse failures."
        else:
            self.explanation = (
                "Very low confidence: most dependencies unresolved or parse critically degraded."
            )


# ---------------------------------------------------------------------------
# Completeness report
# ---------------------------------------------------------------------------


class CompletenessReport(BaseModel):
    status: CompletenessStatus = "complete"
    missing_xrefs_count: int = 0
    unresolved_xrefs_count: int = 0
    failed_sources_count: int = 0
    cycle_blocked_count: int = 0
    unsupported_entity_types: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    consumer_caution: str | None = None

    def recompute_from_document(self, document: DwgJsonDocument) -> None:
        missing = 0
        unresolved = 0
        failed = 0
        cycle_blocked = 0
        notes: list[str] = []

        for source in document.sources:
            if source.role != "xref":
                continue
            match source.parse_status:
                case "missing":
                    missing += 1
                case "unresolved":
                    unresolved += 1
                case "failed":
                    failed += 1

        for edge in document.xref_graph.edges:
            if not edge.exists and not edge.parsed:
                for node in document.xref_graph.nodes:
                    if (
                        node.source_id == edge.target_source_id
                        and node.parse_status == "unresolved"
                    ):
                        cycle_blocked += 1
                        break

        self.missing_xrefs_count = missing
        self.unresolved_xrefs_count = unresolved
        self.failed_sources_count = failed
        self.cycle_blocked_count = cycle_blocked

        total_problems = missing + unresolved + failed + cycle_blocked
        if total_problems == 0:
            self.status = "complete"
            self.consumer_caution = None
            self.notes = []
        elif failed > 0 and (missing + unresolved + failed) == len(
            [s for s in document.sources if s.role == "xref"]
        ):
            self.status = "incomplete"
            notes.append("All xref dependencies failed or are missing.")
            self.consumer_caution = (
                "This document's xref dependencies could not be resolved. "
                "Geometry-dependent semantics are incomplete."
            )
        else:
            self.status = "partial"
            notes.append(
                "One or more xref dependencies were not fully available during parse."
            )
            self.consumer_caution = (
                "Geometry-dependent semantics may be incomplete because one or more "
                "xrefs were missing, unresolved, or failed to parse."
            )
        self.notes = notes


# ---------------------------------------------------------------------------
# Top-level document
# ---------------------------------------------------------------------------


class DwgJsonDocument(BaseModel):
    schema_version: str = "0.1.0"
    parser: ParserInfo
    root_source_id: str
    sources: list[SourceDocument] = Field(default_factory=list)
    xref_graph: XrefGraph = Field(default_factory=XrefGraph)
    compositions: list[Composition] = Field(default_factory=list)
    completeness: CompletenessReport = Field(default_factory=CompletenessReport)
    interpretation_confidence: InterpretationConfidence = Field(
        default_factory=InterpretationConfidence
    )
    interpretation_status: InterpretationStatus = "complete"
    missing_references: list[MissingReference] = Field(default_factory=list)
    warnings: list[WarningRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def root_source(self) -> SourceDocument:
        for source in self.sources:
            if source.id == self.root_source_id:
                return source
        raise KeyError(f"Root source {self.root_source_id!r} not found")

    @property
    def all_entities(self) -> list[Entity]:
        return [e for s in self.sources for e in s.entities]

    @property
    def all_layers(self) -> list[Layer]:
        return [la for s in self.sources for la in s.layers]

    def derive_interpretation_status(self) -> InterpretationStatus:
        c = self.completeness.status
        conf = self.interpretation_confidence.value
        if c == "complete" and conf >= 0.9:
            return "complete"
        if c == "incomplete" or conf < 0.2:
            return "failed"
        if conf < 0.5:
            return "degraded"
        return "partial"


# ---------------------------------------------------------------------------
# Parse options and result
# ---------------------------------------------------------------------------


class ParseOptions(BaseModel):
    resolve_xrefs: bool = True
    bind_xrefs: bool = True
    max_xref_depth: int = 8
    missing_xref_policy: MissingXrefPolicy = "record"
    xref_search_roots: list[str] = Field(default_factory=list)
    out_dir: str | None = None
    backend: str = "auto"
    keep_raw_payloads: bool = True
    indent: int = 2


class ParseResult(BaseModel):
    document: DwgJsonDocument
    output_json_path: str | None = None

    @property
    def source_path(self) -> Path:
        return Path(self.document.root_source.path)

    def to_json_text(self, indent: int = 2) -> str:
        from .pipeline.export_json import to_json_text

        return to_json_text(self, indent=indent)

    def write_json_file(self, output_dir: Path | str | None = None) -> Path:
        from .pipeline.export_json import export_json_file

        opts = ParseOptions(out_dir=str(output_dir) if output_dir else None)
        path = export_json_file(self, opts)
        self.output_json_path = str(path)
        return path
