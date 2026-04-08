"""Interpretation-confidence heuristic.

Penalties are additive and the final value is clamped to [0, 1].
The heuristic is intentionally simple and monotonic: every problem
factor can only *reduce* confidence.
"""

from __future__ import annotations

from ..models import DwgJsonDocument

# Penalty constants
PENALTY_MISSING_XREF = 0.15
PENALTY_UNREADABLE_XREF = 0.12
PENALTY_CYCLE_BLOCKED = 0.10
PENALTY_UNSUPPORTED_ENTITY = 0.03
PENALTY_BACKEND_WARNING = 0.01
PENALTY_PARSE_FAILURE = 0.20


def compute_confidence(document: DwgJsonDocument) -> None:
    """Mutate *document.interpretation_confidence* in-place."""
    conf = document.interpretation_confidence
    conf.factors.clear()

    for source in document.sources:
        if source.role != "xref":
            continue
        if source.parse_status == "missing":
            conf.apply_penalty(
                "missing_xref",
                PENALTY_MISSING_XREF,
                f"Missing xref: {source.path}",
            )
        elif source.parse_status == "failed":
            conf.apply_penalty(
                "failed_xref",
                PENALTY_PARSE_FAILURE,
                f"Failed to parse xref: {source.path}",
            )
        elif source.parse_status == "unresolved":
            conf.apply_penalty(
                "cycle_blocked_xref",
                PENALTY_CYCLE_BLOCKED,
                f"Cycle-blocked xref: {source.path}",
            )

    # Unsupported entity types mentioned in warnings
    unsupported_types: set[str] = set()
    for w in document.warnings:
        if w.code == "unsupported-entity-type":
            unsupported_types.add(w.message)
    for t in unsupported_types:
        conf.apply_penalty("unsupported_entity", PENALTY_UNSUPPORTED_ENTITY, t)

    # Generic backend warnings (excluding xref-specific ones already counted)
    xref_codes = {"xref-missing", "xref-cycle", "xref-depth-limit"}
    backend_warns = [
        w
        for w in document.warnings
        if w.code not in xref_codes and w.code != "unsupported-entity-type"
    ]
    if backend_warns:
        conf.apply_penalty(
            "backend_warnings",
            min(PENALTY_BACKEND_WARNING * len(backend_warns), 0.10),
            f"{len(backend_warns)} backend warning(s)",
        )

    conf.recompute()
