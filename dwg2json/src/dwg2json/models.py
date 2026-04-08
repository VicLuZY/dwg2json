from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    min_x: float
    min_y: float
    min_z: float | None = None
    max_x: float
    max_y: float
    max_z: float | None = None


class ParserInfo(BaseModel):
    name: str = "dwg2json"
    version: str = "0.1.0a0"
    backend: str
    backend_version: str | None = None


class WarningRecord(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    source_id: str | None = None
    handle: str | None = None


class Layer(BaseModel):
    id: str
    name: str
    color_index: int | None = None
    line_type: str | None = None
    is_frozen: bool = False
    is_locked: bool = False
    is_off: bool = False


class BlockDefinition(BaseModel):
    id: str
    name: str
    entity_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    id: str
    source_id: str
    handle: str
    type: str
    owner_handle: str | None = None
    layer: str | None = None
    block_name: str | None = None
    layout: str | None = None
    text: str | None = None
    bbox: BoundingBox | None = None
    transform: list[list[float]] | None = None
    composed_transform: list[list[float]] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    xdata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    warnings: list[WarningRecord] = Field(default_factory=list)


class XrefBindingMetadata(BaseModel):
    saved_path: str | None = None
    resolved_path: str | None = None
    mode: Literal["attach", "overlay", "unknown"] = "unknown"
    transform: list[list[float]] | None = None
    exists: bool = True
    parsed: bool = True
    missing_reason: str | None = None
    candidate_paths: list[str] = Field(default_factory=list)


class SourceDocument(BaseModel):
    id: str
    path: str
    resolved_path: str | None = None
    role: Literal["root", "xref"] = "root"
    exists: bool = True
    parsed: bool = True
    parse_status: Literal["parsed", "partial", "unresolved", "missing", "failed"] = "parsed"
    parent_source_id: str | None = None
    xref_binding: XrefBindingMetadata | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    layers: list[Layer] = Field(default_factory=list)
    blocks: list[BlockDefinition] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    warnings: list[WarningRecord] = Field(default_factory=list)


class XrefGraphNode(BaseModel):
    source_id: str
    path: str
    resolved_path: str | None = None
    exists: bool = True
    parsed: bool = True
    parse_status: Literal["parsed", "partial", "unresolved", "missing", "failed"] = "parsed"
    parent_source_id: str | None = None
    depth: int = 0


class XrefGraphEdge(BaseModel):
    host_source_id: str
    target_source_id: str
    saved_path: str | None = None
    resolved_path: str | None = None
    mode: Literal["attach", "overlay", "unknown"] = "unknown"
    transform: list[list[float]] | None = None
    exists: bool = True
    parsed: bool = True
    composition_required: bool = True


class SourceBinding(BaseModel):
    source_id: str
    parent_source_id: str | None = None
    placement_transform: list[list[float]] | None = None
    inherited_transform_chain: list[list[list[float]]] = Field(default_factory=list)
    mode: Literal["attach", "overlay", "unknown"] = "unknown"
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
    completeness_status: Literal["complete", "partial", "missing_dependencies"] = "complete"
    missing_source_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CompletenessReport(BaseModel):
    status: Literal["complete", "partial", "incomplete"] = "complete"
    missing_xrefs_count: int = 0
    unresolved_xrefs_count: int = 0
    failed_sources_count: int = 0
    notes: list[str] = Field(default_factory=list)
    consumer_caution: str | None = None

    def recompute_from_document(self, document: "DwgJsonDocument") -> None:
        missing = 0
        unresolved = 0
        failed = 0
        notes: list[str] = []
        for source in document.sources:
            if source.role != "xref":
                continue
            if source.parse_status == "missing":
                missing += 1
            elif source.parse_status == "unresolved":
                unresolved += 1
            elif source.parse_status == "failed":
                failed += 1
        self.missing_xrefs_count = missing
        self.unresolved_xrefs_count = unresolved
        self.failed_sources_count = failed
        if missing or unresolved or failed:
            self.status = "partial" if (missing or unresolved) and not failed else "incomplete"
            notes.append("One or more xref dependencies were not fully available during parse.")
            self.consumer_caution = (
                "Geometry-dependent semantics may be incomplete because one or more xrefs were missing, unresolved, or failed to parse."
            )
        else:
            self.status = "complete"
            self.consumer_caution = None
        self.notes = notes


class DwgJsonDocument(BaseModel):
    schema_version: str = "0.1.0"
    parser: ParserInfo
    root_source_id: str
    sources: list[SourceDocument] = Field(default_factory=list)
    xref_graph_nodes: list[XrefGraphNode] = Field(default_factory=list)
    xref_graph_edges: list[XrefGraphEdge] = Field(default_factory=list)
    compositions: list[Composition] = Field(default_factory=list)
    completeness: CompletenessReport = Field(default_factory=CompletenessReport)
    warnings: list[WarningRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def root_source(self) -> SourceDocument:
        for source in self.sources:
            if source.id == self.root_source_id:
                return source
        raise KeyError(f"Root source {self.root_source_id} not found")


class ParseOptions(BaseModel):
    resolve_xrefs: bool = True
    bind_xrefs: bool = True
    max_xref_depth: int = 8
    missing_xref_policy: Literal["record", "error"] = "record"
    out_dir: str | None = None
    backend: str = "auto"
    keep_raw_payloads: bool = True


class ParseResult(BaseModel):
    document: DwgJsonDocument
    output_json_path: str | None = None

    @property
    def source_path(self) -> Path:
        return Path(self.document.root_source.path)

    def write_json_file(self, output_dir: Path | None = None) -> Path:
        from .pipeline.export_json import export_json_file
        path = export_json_file(self, ParseOptions(out_dir=str(output_dir) if output_dir else self.output_json_path))
        self.output_json_path = str(path)
        return path
