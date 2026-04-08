# Confidence & Completeness

dwg2json provides two complementary quality signals so consumers never mistake a partial parse for a complete one.

## Interpretation confidence

`interpretation_confidence` is a scalar between 0.0 and 1.0. It starts at 1.0 and is reduced by **monotonic penalties** for each issue discovered during parsing.

### Penalty factors

| Factor | Penalty | Trigger |
|--------|---------|---------|
| Missing xref | 0.15 | Each xref whose target file was not found |
| Failed xref parse | 0.20 | Each xref that was found but failed to parse |
| Cycle-blocked xref | 0.10 | Each xref blocked by a dependency cycle |
| Unsupported entity type | 0.03 | Each unknown entity type in warnings |
| Backend warnings | 0.01 each (capped at 0.10) | Non-xref backend warnings |

### Factor ledger

Every applied penalty is recorded in `interpretation_confidence.factors`:

```json
{
  "value": 0.70,
  "factors": [
    { "factor": "missing_xref", "penalty": 0.15, "detail": "Missing xref: bg.dwg" },
    { "factor": "missing_xref", "penalty": 0.15, "detail": "Missing xref: site.dwg" }
  ],
  "explanation": "Moderate confidence: some dependencies missing or partially parsed."
}
```

### Explanation tiers

| Range | Explanation |
|-------|-------------|
| ≥ 0.9 | High confidence: all dependencies resolved. |
| 0.6 – 0.9 | Moderate confidence: some dependencies missing or partially parsed. |
| 0.3 – 0.6 | Low confidence: significant missing dependencies or parse failures. |
| < 0.3 | Very low confidence: most dependencies unresolved or parse critically degraded. |

## Completeness report

`completeness` provides aggregate counts and a consumer-facing status:

```json
{
  "status": "partial",
  "missing_xrefs_count": 2,
  "unresolved_xrefs_count": 0,
  "failed_sources_count": 0,
  "cycle_blocked_count": 0,
  "notes": ["One or more xref dependencies were not fully available during parse."],
  "consumer_caution": "Geometry-dependent semantics may be incomplete because one or more xrefs were missing, unresolved, or failed to parse."
}
```

### Status values

| Status | Meaning |
|--------|---------|
| `complete` | All xref dependencies resolved and parsed successfully. |
| `partial` | Some xref dependencies are missing or unresolved. |
| `incomplete` | All xref dependencies failed or are missing. |

## Interpretation status

`interpretation_status` combines completeness and confidence into a single field:

| Status | Condition |
|--------|-----------|
| `complete` | Completeness is `complete` and confidence ≥ 0.9 |
| `partial` | Completeness is not `complete` or confidence is moderate |
| `degraded` | Confidence < 0.5 |
| `failed` | Completeness is `incomplete` or confidence < 0.2 |

## Best practices for consumers

1. **Always check `interpretation_status`** before treating the output as authoritative.
2. **Inspect `missing_references`** to understand which dependencies were unavailable.
3. **Use `interpretation_confidence.value`** for ranking or gating automation — but treat it as a relative signal, not a calibrated probability.
4. **Read `consumer_caution`** when present — it provides a human-readable summary of the limitations.
