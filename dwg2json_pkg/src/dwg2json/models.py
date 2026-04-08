from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ParseWarning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    related_handles: list[str] = Field(default_factory=list)
    related_paths: list[str] = Field(default_factory=list)


class MissingReference(BaseModel):
    kind: Literal["xref", "image", "underlay", "font", "shape_file", "other"] = "xref"
    requested_path: str | None = None
    normalized_path: str | None = None
    resolver_root: str | None = None
    parent_document_id: str | None = None
    host_handles: list[str] = Field(default_factory=list)
    impact_summary: str
    severity: Literal["warning", "error"] = "warning"
    interpretation_impacted: bool = True


class Provenance(BaseModel):
    backend_name: str = "unconfigured"
    backend_version: str | None = None
    source_file: str | None = None
    parse_timestamp_utc: str | None = None


class Bounds2D(BaseModel):
    min_x: float | None = None
    min_y: float | None = None
    max_x: float | None = None
    max_y: float | None = None


class Transform2D(BaseModel):
    matrix_3x3_row_major: list[float] = Field(default_factory=list)


class Layer(BaseModel):
    id: str
    name: str
    handle: str | None = None
    visible: bool = True
    frozen: bool = False
    locked: bool = False


class Layout(BaseModel):
    id: str
    name: str
    handle: str | None = None
    kind: Literal["model", "paper", "unknown"] = "unknown"


class BlockDefinition(BaseModel):
    id: str
    name: str
    handle: str | None = None
    entity_ids: list[str] = Field(default_factory=list)
    attribute_definition_ids: list[str] = Field(default_factory=list)
    bounds: Bounds2D | None = None


class Entity(BaseModel):
    id: str
    handle: str | None = None
    owner_handle: str | None = None
    kind: str
    layer_id: str | None = None
    layout_id: str | None = None
    block_definition_id: str | None = None
    text: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    geometry: dict[str, Any] = Field(default_factory=dict)
    bounds: Bounds2D | None = None
    transform: Transform2D | None = None
    source_document_id: str | None = None
    source_xref_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    source_id: str
    relation: str
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class XrefBinding(BaseModel):
    id: str
    host_document_id: str
    referenced_document_id: str | None = None
    block_reference_entity_id: str | None = None
    requested_path: str | None = None
    resolved_path: str | None = None
    status: Literal["resolved", "missing", "unreadable", "cycle_blocked"] = "resolved"
    overlay_mode: Literal["attach", "overlay", "unknown"] = "unknown"
    transform_into_host: Transform2D | None = None
    interpretation_notes: list[str] = Field(default_factory=list)


class CompositeContext(BaseModel):
    id: str
    host_document_id: str
    layout_id: str | None = None
    participating_document_ids: list[str] = Field(default_factory=list)
    participating_xref_ids: list[str] = Field(default_factory=list)
    participating_entity_ids: list[str] = Field(default_factory=list)
    interpretation_required: bool = True
    summary: str | None = None


class CanonicalDrawingDocument(BaseModel):
    schema_version: str = "0.1.0"
    package_name: str = "dwg2json"
    root_document_id: str
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)
    layers: list[Layer] = Field(default_factory=list)
    layouts: list[Layout] = Field(default_factory=list)
    block_definitions: list[BlockDefinition] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    xrefs: list[XrefBinding] = Field(default_factory=list)
    composite_contexts: list[CompositeContext] = Field(default_factory=list)
    missing_references: list[MissingReference] = Field(default_factory=list)
    warnings: list[ParseWarning] = Field(default_factory=list)
    interpretation_confidence: float = 0.0
    interpretation_status: Literal["complete", "partial", "degraded", "failed"] = "partial"
