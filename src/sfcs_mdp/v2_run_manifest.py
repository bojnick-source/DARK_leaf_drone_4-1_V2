from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Sequence, Tuple

kRunsDir = "runs"
kArtifactsDir = "artifacts"
kRunOutputFile = "run_output.json"
kRunIdCharset = "0123456789abcdef"


def fnv1a_64(data: str) -> int:
    h = 14695981039346656037
    for b in data.encode("utf-8"):
        h ^= b
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def run_id_from_seed(seed: str) -> str:
    return f"{fnv1a_64(seed):016x}"


def is_lower_hex_run_id(run_id: str) -> bool:
    return len(run_id) == 16 and all(c in kRunIdCharset for c in run_id)


def run_artifact_dir(run_id: str) -> str:
    return (PurePosixPath(kArtifactsDir) / kRunsDir / run_id).as_posix()


def run_output_path(run_id: str) -> str:
    return (PurePosixPath(kArtifactsDir) / kRunsDir / run_id / kRunOutputFile).as_posix()


def format_scalar(value: float, precision: int = 12) -> str:
    if not math.isfinite(value):
        raise ValueError("non-finite float")
    return f"{float(value):.{precision}f}"


def format_array(values: Sequence[float], precision: int = 12) -> str:
    return "[" + ",".join(format_scalar(float(v), precision) for v in values) + "]"


def _json_escape(s: str) -> str:
    out: list[str] = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20 or ch == "\u2028" or ch == "\u2029":
            out.append(f"\\u{o:04x}")
        else:
            out.append(ch)
    return "".join(out)


def _dump_json(obj: Any, *, sort_keys: bool = False, precision: int = 12) -> str:
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, float):
        return format_scalar(obj, precision)
    if isinstance(obj, str):
        return '"' + _json_escape(obj) + '"'
    if isinstance(obj, list):
        return "[" + ",".join(_dump_json(x, sort_keys=sort_keys, precision=precision) for x in obj) + "]"
    if isinstance(obj, dict):
        items = list(obj.items())
        if sort_keys:
            items.sort(key=lambda kv: str(kv[0]))
        parts: list[str] = ["{"]
        first = True
        for k, v in items:
            if not isinstance(k, str):
                raise TypeError("json object key must be str")
            if not first:
                parts.append(",")
            first = False
            parts.append('"' + _json_escape(k) + '":' + _dump_json(v, sort_keys=sort_keys, precision=precision))
        parts.append("}")
        return "".join(parts)
    raise TypeError(f"unsupported json type: {type(obj).__name__}")


def _json_load_no_dupes(s: str) -> Any:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k, v in pairs:
            if k in d:
                raise ValueError(f"duplicate key: {k}")
            d[k] = v
        return d

    return json.loads(s, object_pairs_hook=hook)


def canonicalize_inputs(
    scalars: Mapping[str, float],
    text: Mapping[str, str] | None = None,
    arrays: Mapping[str, Sequence[float]] | None = None,
    units: Mapping[str, Tuple[float, str]] | None = None,
    precision: int = 12,
) -> str:
    text = text or {}
    arrays = arrays or {}
    units = units or {}

    payload: dict[str, str] = {}

    for k in sorted(scalars.keys()):
        v = float(scalars[k])
        payload[f"s:{k}"] = format_scalar(v, precision)

    for k in sorted(text.keys()):
        payload[f"t:{k}"] = str(text[k])

    for k in sorted(arrays.keys()):
        vv = [float(x) for x in arrays[k]]
        if not all(math.isfinite(x) for x in vv):
            raise ValueError("arrays must be finite")
        payload[f"a:{k}"] = format_array(vv, precision)

    for k in sorted(units.keys()):
        mag, unit = units[k]
        payload[f"u:{k}"] = f"{format_scalar(float(mag), precision)} {str(unit)}"

    return _dump_json(payload, sort_keys=True, precision=precision)


def run_id_from_inputs(
    scalars: Mapping[str, float],
    text: Mapping[str, str] | None = None,
    arrays: Mapping[str, Sequence[float]] | None = None,
    units: Mapping[str, Tuple[float, str]] | None = None,
    precision: int = 12,
) -> str:
    return run_id_from_seed(canonicalize_inputs(scalars, text, arrays, units, precision))


def _is_portable_relative_clean_path(path: str) -> bool:
    if not isinstance(path, str) or not path:
        return False
    if "\x00" in path:
        return False
    for ch in path:
        if ord(ch) < 0x20:
            return False
    if "\\" in path:
        return False
    if ":" in path:
        return False
    p = PurePosixPath(path)
    if p.is_absolute():
        return False
    parts = p.parts
    if not parts:
        return False
    for seg in parts:
        if seg in ("", ".", ".."):
            return False
    return True


class LoadError(str, Enum):
    NONE = "NONE"
    MISSING_FILE = "MISSING_FILE"
    JSON_PARSE_ERROR = "JSON_PARSE_ERROR"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    RUN_ID_MISMATCH = "RUN_ID_MISMATCH"
    INVALID_METRIC = "INVALID_METRIC"
    INVALID_ARTIFACT_PATH = "INVALID_ARTIFACT_PATH"


class FailLabel(str, Enum):
    AERO_SOLIDITY_FAIL = "AERO_SOLIDITY_FAIL"
    AERO_TIPMACH_FAIL = "AERO_TIPMACH_FAIL"
    AERO_DISK_LOADING_FAIL = "AERO_DISK_LOADING_FAIL"
    AERO_BEMT_DIVERGENCE = "AERO_BEMT_DIVERGENCE"
    ELEC_MOTOR_CURRENT_FAIL = "ELEC_MOTOR_CURRENT_FAIL"
    ELEC_MOTOR_THERMAL_FAIL = "ELEC_MOTOR_THERMAL_FAIL"
    ELEC_ESC_THERMAL_FAIL = "ELEC_ESC_THERMAL_FAIL"
    ELEC_BUS_CURRENT_FAIL = "ELEC_BUS_CURRENT_FAIL"
    ELEC_BATTERY_INFEASIBLE = "ELEC_BATTERY_INFEASIBLE"
    ELEC_BATTERY_THERMAL_FAIL = "ELEC_BATTERY_THERMAL_FAIL"
    ENERGY_ENDURANCE_FAIL = "ENERGY_ENDURANCE_FAIL"
    ENERGY_NEGATIVE_MARGIN = "ENERGY_NEGATIVE_MARGIN"
    STRUCT_STRESS_FAIL = "STRUCT_STRESS_FAIL"
    STRUCT_BUCKLING_FAIL = "STRUCT_BUCKLING_FAIL"
    STRUCT_FATIGUE_FAIL = "STRUCT_FATIGUE_FAIL"
    SYS_CONVERGENCE_FAIL = "SYS_CONVERGENCE_FAIL"
    SYS_NAN_FAIL = "SYS_NAN_FAIL"
    SYS_INFEASIBLE = "SYS_INFEASIBLE"


@dataclass(frozen=True)
class RunOutput:
    run_id: str
    ok: bool
    label: Optional[FailLabel]
    inputs: dict[str, Any]
    metrics: dict[str, float]
    artifact_root: str
    artifact_paths: list[str]


@dataclass(frozen=True)
class LoadResult:
    success: bool
    code: LoadError
    message: str
    output: Optional[RunOutput] = None


def write_run_output(
    run_id: str,
    inputs_json: str,
    metrics: Mapping[str, float],
    ok: bool,
    label: Optional[FailLabel] = None,
    artifact_paths: Sequence[str] = (),
    artifact_root_override: str = "",
    precision: int = 12,
    *,
    strict_paths: bool = True,
) -> str:
    if not is_lower_hex_run_id(run_id):
        raise ValueError("run_id format invalid")
    if ok and label is not None:
        raise ValueError("label must be None when ok==True")
    if (not ok) and label is None:
        raise ValueError("label required when ok==False")

    try:
        inputs_obj = _json_load_no_dupes(inputs_json)
    except Exception as exc:
        raise ValueError(f"inputs_json invalid: {exc}") from exc
    if not isinstance(inputs_obj, dict):
        raise ValueError("inputs_json must be object")

    metrics_obj: dict[str, float] = {}
    for k in sorted(metrics.keys()):
        v = float(metrics[k])
        if not math.isfinite(v):
            raise ValueError("metrics must be finite")
        metrics_obj[str(k)] = v

    paths_out: list[str] = []
    for p in artifact_paths:
        ps = str(p)
        if strict_paths and (not _is_portable_relative_clean_path(ps)):
            raise ValueError("artifact path invalid")
        paths_out.append(ps)

    artifact_root = artifact_root_override or run_artifact_dir(run_id)

    out: dict[str, Any] = {}
    out["run_id"] = run_id
    out["ok"] = bool(ok)
    out["label"] = (None if ok else label.value)
    out["inputs"] = inputs_obj
    out["metrics"] = metrics_obj
    out["artifacts"] = {"root": artifact_root, "paths": paths_out}

    payload = _dump_json(out, sort_keys=False, precision=precision) + "\n"

    root_dir = Path(artifact_root)
    root_dir.mkdir(parents=True, exist_ok=True)
    out_path = root_dir / kRunOutputFile
    tmp_path = Path(str(out_path) + ".tmp")

    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, out_path)
        try:
            dfd = os.open(str(root_dir), os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except Exception:
            pass
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass

    return out_path.as_posix()


def load_run_output(
    run_id: str,
    artifact_root_override: str = "",
    *,
    strict_paths: bool = True,
) -> LoadResult:
    if not is_lower_hex_run_id(run_id):
        return LoadResult(False, LoadError.RUN_ID_MISMATCH, "run_id format invalid")

    artifact_root = artifact_root_override or run_artifact_dir(run_id)
    path = Path(artifact_root) / kRunOutputFile
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return LoadResult(False, LoadError.MISSING_FILE, "run_output.json missing")

    try:
        root = _json_load_no_dupes(content)
    except Exception as exc:
        return LoadResult(False, LoadError.JSON_PARSE_ERROR, f"invalid JSON: {exc}")

    if not isinstance(root, dict):
        return LoadResult(False, LoadError.JSON_PARSE_ERROR, "root must be object")

    allowed = {"run_id", "ok", "label", "inputs", "metrics", "artifacts"}
    if set(root.keys()) - allowed:
        return LoadResult(False, LoadError.SCHEMA_VIOLATION, "unknown top-level field")

    for k in ("run_id", "ok", "label", "inputs", "metrics"):
        if k not in root:
            return LoadResult(False, LoadError.SCHEMA_VIOLATION, "missing required fields")

    rid = root.get("run_id")
    if not isinstance(rid, str) or rid != run_id or (not is_lower_hex_run_id(rid)):
        return LoadResult(False, LoadError.RUN_ID_MISMATCH, "run_id mismatch")

    ok = root.get("ok")
    if not isinstance(ok, bool):
        return LoadResult(False, LoadError.SCHEMA_VIOLATION, "ok must be bool")

    label_val = root.get("label")
    label: Optional[FailLabel] = None
    if ok:
        if label_val is not None:
            return LoadResult(False, LoadError.SCHEMA_VIOLATION, "label must be null when ok")
    else:
        if not isinstance(label_val, str):
            return LoadResult(False, LoadError.SCHEMA_VIOLATION, "label must be string when !ok")
        try:
            label = FailLabel(label_val)
        except Exception:
            return LoadResult(False, LoadError.SCHEMA_VIOLATION, "invalid fail label")

    inputs = root.get("inputs")
    if not isinstance(inputs, dict):
        return LoadResult(False, LoadError.SCHEMA_VIOLATION, "inputs must be object")

    metrics_raw = root.get("metrics")
    if not isinstance(metrics_raw, dict):
        return LoadResult(False, LoadError.SCHEMA_VIOLATION, "metrics must be object")
    metrics: dict[str, float] = {}
    for k, v in metrics_raw.items():
        if not isinstance(k, str) or not isinstance(v, (int, float)):
            return LoadResult(False, LoadError.INVALID_METRIC, "metric invalid")
        fv = float(v)
        if not math.isfinite(fv):
            return LoadResult(False, LoadError.INVALID_METRIC, "metric invalid")
        metrics[k] = fv

    artifacts = root.get("artifacts")
    artifact_root_out = artifact_root
    artifact_paths_out: list[str] = []
    if artifacts is not None:
        if not isinstance(artifacts, dict):
            return LoadResult(False, LoadError.SCHEMA_VIOLATION, "artifacts must be object")
        if "root" in artifacts:
            if not isinstance(artifacts["root"], str):
                return LoadResult(False, LoadError.SCHEMA_VIOLATION, "artifacts.root must be string")
            artifact_root_out = artifacts["root"]
        if "paths" in artifacts:
            paths = artifacts["paths"]
            if not isinstance(paths, list):
                return LoadResult(False, LoadError.SCHEMA_VIOLATION, "artifacts.paths must be array")
            for e in paths:
                if not isinstance(e, str):
                    return LoadResult(False, LoadError.SCHEMA_VIOLATION, "artifact path must be string")
                if strict_paths and (not _is_portable_relative_clean_path(e)):
                    return LoadResult(False, LoadError.INVALID_ARTIFACT_PATH, "artifact path invalid")
                artifact_paths_out.append(e)

    return LoadResult(
        True,
        LoadError.NONE,
        "",
        RunOutput(
            run_id=run_id,
            ok=ok,
            label=label,
            inputs=inputs,
            metrics=dict(sorted(metrics.items())),
            artifact_root=str(PurePosixPath(artifact_root_out).as_posix()),
            artifact_paths=artifact_paths_out,
        ),
    )


@dataclass(frozen=True)
class IngestOptions:
    artifact_root: str = (PurePosixPath(kArtifactsDir) / kRunsDir).as_posix()
    run_ids: Sequence[str] = ()
    prefix: str = ""
    max_runs: int = (1 << 63) - 1
    strict_paths: bool = True


@dataclass(frozen=True)
class IngestError:
    run_id: str
    code: str
    message: str
    source_path: str


@dataclass(frozen=True)
class IngestedRun:
    output: RunOutput
    source_path: str


@dataclass(frozen=True)
class IngestResult:
    runs: list[IngestedRun]
    errors: list[IngestError]


def ingest_runs(opts: IngestOptions = IngestOptions()) -> IngestResult:
    root = Path(opts.artifact_root)
    errors: list[IngestError] = []
    runs: list[IngestedRun] = []
    allow = set(opts.run_ids) if opts.run_ids else None

    candidates: list[str] = []
    if root.exists():
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if opts.prefix and not name.startswith(opts.prefix):
                continue
            if allow is not None and name not in allow:
                continue
            if not is_lower_hex_run_id(name):
                errors.append(IngestError(name, "INVALID_RUN_ID_DIR", "run_id directory invalid", entry.as_posix()))
                continue
            candidates.append(name)

    candidates.sort()
    if opts.max_runs < len(candidates):
        candidates = candidates[: opts.max_runs]

    for rid in candidates:
        run_dir = root / rid
        p = run_dir / kRunOutputFile
        if not p.exists():
            errors.append(IngestError(rid, "MISSING_MANIFEST", "run_output.json missing", p.as_posix()))
            continue
        lr = load_run_output(rid, run_dir.as_posix(), strict_paths=opts.strict_paths)
        if not lr.success or lr.output is None:
            errors.append(IngestError(rid, "VALIDATION_FAILED", lr.message, p.as_posix()))
            continue
        runs.append(IngestedRun(lr.output, p.as_posix()))

    return IngestResult(runs=runs, errors=errors)


@dataclass(frozen=True)
class SummaryCounts:
    total: int = 0
    passed: int = 0
    failed: int = 0
    invalid: int = 0


@dataclass(frozen=True)
class SummaryRun:
    run_id: str
    ok: bool
    label: Optional[str]
    metrics: dict[str, float]
    source_path: str
    error: Optional[IngestError]


@dataclass(frozen=True)
class SummaryResult:
    json: str
    counts: SummaryCounts
    errors: list[IngestError]
    runs: list[SummaryRun]


@dataclass(frozen=True)
class SummaryOptions:
    ingest_opts: IngestOptions = IngestOptions()
    schema: str = "dark/v2/io/run_summary/1.1"
    generated_at: str = "1970-01-01T00:00:00Z"


def aggregate_runs(opts: SummaryOptions = SummaryOptions()) -> SummaryResult:
    ingest = ingest_runs(opts.ingest_opts)
    total = 0
    passed = 0
    failed = 0

    summary_runs: list[SummaryRun] = []
    for r in ingest.runs:
        total += 1
        if r.output.ok:
            passed += 1
            summary_runs.append(
                SummaryRun(
                    run_id=r.output.run_id,
                    ok=True,
                    label=None,
                    metrics=dict(sorted(r.output.metrics.items())),
                    source_path=r.source_path,
                    error=None,
                )
            )
        else:
            failed += 1
            lbl = r.output.label.value if r.output.label else "FAILED"
            summary_runs.append(
                SummaryRun(
                    run_id=r.output.run_id,
                    ok=False,
                    label=lbl,
                    metrics={},
                    source_path=r.source_path,
                    error=IngestError(r.output.run_id, "FAILED", lbl, r.source_path),
                )
            )

    invalid = len(ingest.errors)
    total += invalid

    label_tally: dict[str, int] = {}
    for r in summary_runs:
        if (not r.ok) and r.label:
            label_tally[r.label] = label_tally.get(r.label, 0) + 1

    summary_runs.sort(key=lambda x: x.run_id)
    errors = sorted(ingest.errors, key=lambda e: (e.run_id, e.code, e.message))

    top: dict[str, Any] = {
        "schema": opts.schema,
        "artifact_root": opts.ingest_opts.artifact_root,
        "generated_at": opts.generated_at,
        "runs": [
            {
                **({"run_id": r.run_id, "ok": r.ok, "source_path": r.source_path}),
                **({} if r.label is None else {"label": r.label}),
                **({} if (not r.ok) or (not r.metrics) else {"metrics": dict(sorted(r.metrics.items()))}),
                **({} if r.error is None else {"error": {"code": r.error.code, "message": r.error.message}}),
            }
            for r in summary_runs
        ],
        "counts": {"total": total, "passed": passed, "failed": failed, "invalid": invalid},
        "label_tally": dict(sorted(label_tally.items())),
        "errors": [
            {
                "run_id": e.run_id,
                "code": e.code,
                "message": e.message,
                **({} if not e.source_path else {"source_path": e.source_path}),
            }
            for e in errors
        ],
    }

    return SummaryResult(
        json=_dump_json(top, sort_keys=False, precision=12),
        counts=SummaryCounts(total=total, passed=passed, failed=failed, invalid=invalid),
        errors=errors,
        runs=summary_runs,
    )
