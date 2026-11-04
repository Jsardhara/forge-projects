"""Human and machine rendering. No I/O, no decisions - the CLI owns policy."""

import json

TOOL = "wsaudit"
MAX_LISTED = 20


def _shape(shape):
    return "x".join(str(dim) for dim in shape) if shape else "scalar"


def _num(value):
    return "n/a" if value is None else "%.6g" % value


def hash_json(model, comparison=None, problems=None):
    payload = {
        "tool": TOOL,
        "version": 1,
        "path": model.path,
        "format": model.format,
        "model_digest": model.model_digest,
        "partial": model.partial,
        "tensor_count": model.tensor_count,
        "total_bytes": model.total_bytes,
        "tensors": [
            {
                "name": item.name,
                "dtype": item.dtype,
                "shape": list(item.shape),
                "sha256": item.sha256,
            }
            for item in model.tensors
        ],
        "manifest": None,
        "verdict": "unverified",
    }
    if comparison is not None:
        payload["manifest"] = {
            "ok": comparison.ok,
            "checked": comparison.checked,
            "problems": list(comparison.problems),
        }
        payload["verdict"] = "verified" if comparison.ok else "mismatch"
    if problems:
        payload["problems"] = list(problems)
    return payload


def hash_text(model, comparison=None, manifest_path=None):
    lines = [
        "wsaudit %s" % model.path,
        "  format    %s" % model.format,
        "  tensors   %d" % model.tensor_count,
        "  bytes     %d" % model.total_bytes,
        "  digest    %s%s" % (model.model_digest, "  (PARTIAL: header only)" if model.partial else ""),
        "",
    ]
    shown = model.tensors[:MAX_LISTED]
    width = max([len(item.name) for item in shown], default=0)
    for item in shown:
        sha = (item.sha256 or "-")[:16]
        lines.append(
            "  %-*s  %-6s %-12s %s" % (width, item.name, item.dtype, _shape(item.shape), sha)
        )
    if len(model.tensors) > len(shown):
        lines.append("  ... %d more tensor(s)" % (len(model.tensors) - len(shown)))
    lines.append("")
    if comparison is None:
        lines.append("verdict: digest computed; unverified (no manifest given)")
    elif comparison.ok:
        lines.append(
            "verdict: VERIFIED - digest matches %s (%d tensor(s) checked)"
            % (manifest_path or "the manifest", comparison.checked)
        )
    else:
        lines.append("verdict: MISMATCH - %d problem(s)" % len(comparison.problems))
        for problem in comparison.problems:
            lines.append("  - %s" % problem)
    return "\n".join(lines)


def diff_json(report_):
    return {
        "tool": TOOL,
        "base": {"path": report_.base.path, "model_digest": report_.base.model_digest},
        "other": {"path": report_.other.path, "model_digest": report_.other.model_digest},
        "changed": report_.changed,
        "patched": report_.patched,
        "added": report_.added,
        "removed": report_.removed,
        "rows": [
            {
                "name": row.name,
                "change": row.change,
                "dtype_base": row.dtype_base,
                "dtype_other": row.dtype_other,
                "shape_base": list(row.shape_base) if row.shape_base else None,
                "shape_other": list(row.shape_other) if row.shape_other else None,
                "l2": row.l2,
                "rel_norm": row.rel_norm,
            }
            for row in report_.rows
        ],
    }


def diff_text(report_, top=None):
    lines = [
        "wsaudit diff",
        "  base   %s  %s" % (report_.base.path, report_.base.model_digest[:16]),
        "  other  %s  %s" % (report_.other.path, report_.other.model_digest[:16]),
        "",
    ]
    if not report_.rows:
        lines.append("Models are identical tensor-for-tensor: %s" % report_.base.model_digest)
        return "\n".join(lines)

    lines.append(
        "changed %d  patched %d  added %d  removed %d"
        % (report_.changed, report_.patched, report_.added, report_.removed)
    )
    rows = report_.rows
    if top is not None:
        rows = rows[:top]
    width = max(len(row.name) for row in rows)
    for row in rows:
        detail = "%s->%s" % (row.dtype_base or "-", row.dtype_other or "-")
        lines.append(
            "  %-8s %-*s  %-13s l2=%-10s rel=%s"
            % (row.change, width, row.name, detail, _num(row.l2), _num(row.rel_norm))
        )
    if top is not None and len(report_.rows) > top:
        lines.append("  ... %d more row(s)" % (len(report_.rows) - top))
    return "\n".join(lines)


def dumps(payload):
    return json.dumps(payload, indent=2, sort_keys=True)
