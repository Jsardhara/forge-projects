"""Tensor-level comparison of two model files, with LoRA module mapping."""

import math
from dataclasses import dataclass, field

from . import digest
from .errors import WsAuditError

# PEFT (lora_A/lora_B) and kohya/AI-Toolkit (lora_down/lora_up) both appear on
# this host; the longer suffixes must be tested first.
LORA_SUFFIXES = (
    (".lora_A.default.weight", "A"),
    (".lora_B.default.weight", "B"),
    (".lora_A.weight", "A"),
    (".lora_B.weight", "B"),
    (".lora_down.weight", "A"),
    (".lora_up.weight", "B"),
)
PREFIX = "base_model.model."


@dataclass(frozen=True)
class DiffRow:
    name: str
    change: str                  # changed | patched | added | removed
    dtype_base: object = None
    dtype_other: object = None
    shape_base: object = None
    shape_other: object = None
    l2: object = None
    rel_norm: object = None


@dataclass(frozen=True)
class DiffReport:
    base: object
    other: object
    rows: tuple = field(default_factory=tuple)

    def _count(self, change):
        return sum(1 for row in self.rows if row.change == change)

    @property
    def changed(self):
        return self._count("changed")

    @property
    def patched(self):
        return self._count("patched")

    @property
    def added(self):
        return self._count("added")

    @property
    def removed(self):
        return self._count("removed")


def map_lora_name(name):
    """('model.layers.12.q_proj', 'A') for an adapter tensor, else None."""
    if name.startswith(PREFIX):
        name = name[len(PREFIX):]
    for suffix, side in LORA_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)], side
    return None


def _norms(path_base, base_tensor, path_other, other_tensor):
    if base_tensor.shape != other_tensor.shape:
        return None, None
    base_values = digest.float_values(path_base, base_tensor)
    other_values = digest.float_values(path_other, other_tensor)
    if base_values is None or other_values is None:
        return None, None
    l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(base_values, other_values)))
    norm = math.sqrt(sum(a * a for a in base_values))
    return l2, (l2 / norm if norm > 0 else None)


def _sort_key(row):
    primary = 0 if row.change in ("changed", "patched") else 1
    return (primary, -(row.l2 if row.l2 is not None else 0.0), row.name)


def diff_models(base_path, other_path, lora_map=False):
    parsed_base = digest.parse_model(base_path)
    parsed_other = digest.parse_model(other_path)
    digests_base = digest.digest_parsed(parsed_base)
    digests_other = digest.digest_parsed(parsed_other)

    base_by_name = {item.name: item for item in digests_base.tensors}
    other_by_name = {item.name: item for item in digests_other.tensors}
    base_tensors = {tensor.name: tensor for tensor in parsed_base.tensors}
    other_tensors = {tensor.name: tensor for tensor in parsed_other.tensors}

    rows = []
    consumed_base = set()
    lora_targets = set()
    if lora_map:
        for name in other_by_name:
            mapped = map_lora_name(name)
            if mapped is None:
                continue
            target, side = mapped
            lora_targets.add(target)
            consumed_base.add(target + ".weight")
            base_item = base_by_name.get(target + ".weight")
            other_item = other_by_name[name]
            rows.append(
                DiffRow(
                    name="%s (lora_%s)" % (target, side),
                    change="patched",
                    dtype_base=base_item.dtype if base_item else "adapter",
                    dtype_other=other_item.dtype,
                    shape_base=base_item.shape if base_item else None,
                    shape_other=other_item.shape,
                )
            )

    for name in sorted(set(base_by_name) | set(other_by_name)):
        if name in consumed_base or (lora_map and map_lora_name(name)):
            continue
        base_item = base_by_name.get(name)
        other_item = other_by_name.get(name)
        if base_item is None:
            assert other_item is not None   # the name came from the union
            rows.append(
                DiffRow(name=name, change="added", dtype_other=other_item.dtype,
                        shape_other=other_item.shape)
            )
            continue
        if other_item is None:
            rows.append(
                DiffRow(name=name, change="removed", dtype_base=base_item.dtype,
                        shape_base=base_item.shape)
            )
            continue
        if base_item.sha256 == other_item.sha256:
            continue
        l2, rel = _norms(
            base_path, base_tensors[name], other_path, other_tensors[name]
        )
        rows.append(
            DiffRow(
                name=name, change="changed",
                dtype_base=base_item.dtype, dtype_other=other_item.dtype,
                shape_base=base_item.shape, shape_other=other_item.shape,
                l2=l2, rel_norm=rel,
            )
        )

    rows.sort(key=_sort_key)
    return DiffReport(base=digests_base, other=digests_other, rows=tuple(rows))
