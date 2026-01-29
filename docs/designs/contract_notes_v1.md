# API Contract Notes: RunStatus & Evidence Schema v1

This document formalizes the post-merge contracts for the Run system, specifically focusing on execution statuses and the Evidence Chain standard.

## 1. Run Lifecycle & Status

QualityFoundry internal execution logic (LangGraph-based) is abstracted into a streamlined status set for standard API consumers.

### RunStatus (External)

| Status | Code | Description |
| :--- | :--- | :--- |
| **PENDING** | `PENDING` | Run created, waiting in queue or initialization. |
| **RUNNING** | `RUNNING` | Run active (Planning, Executing, or Deciding). |
| **FINISHED** | `FINISHED` | Execution finished but no gate decision was made (Anomalous). |
| **JUDGED** | `JUDGED` | Execution finished and gate decision formalized (Terminal). |
| **FAILED** | `FAILED` | Process crashed or aborted (Sandbox error, Timeout, etc.). |

### RunDecision

Final gate result available when status is `JUDGED`.

- `PASS`: All quality gates satisfied.
- `FAIL`: One or more critical gates failed.
- `NEED_HITL`: Human-in-the-loop audit required.

---

## 2. Evidence Chain Standard (v1)

All run results MUST be serialized into `evidence.json` following the `v1` schema.

- **Schema URI**: `https://qualityfoundry.ai/schemas/evidence.v1.schema.json`
- **Root Validation**: Required `$schema` field.

### Key Structure Enhancements
- **Metadata Identity**: Uses `run_id` (UUID v4) as the primary key.
- **Reproducibility**: Includes `git_sha`, `git_branch`, `git_dirty`, and `deps_fingerprint`.
- **Governance Overlay**: Unified `budget` and `decision_source` at root level to prevent redundancy in tool results.
- **Relative Artifacts**: All `artifacts[].path` are normalized relative to the data root (e.g., `{run_id}/screenshot_1.png`).

---

## 3. Implementation Checklist for Tools

- [ ] Emit `TOOL_STARTED` and `TOOL_FINISHED` audit events.
- [ ] Populate `repro` metadata in `TraceCollector`.
- [ ] Ensure `collected_at` follows ISO 8601 UTC format.
- [ ] Use `model_dump(by_alias=True)` to ensure `$schema` is correctly exported.
