"""Immutable records shared by the parsers, the digester and the reporters."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tensor:
    """One tensor's location inside a container file."""

    name: str
    dtype: str
    shape: tuple
    offset: int          # absolute byte offset of the payload in the file
    nbytes: int
    elements: int = 0


@dataclass(frozen=True)
class TensorDigest:
    """One tensor's identity. ``sha256`` is None for a header-only scan."""

    name: str
    dtype: str
    shape: tuple
    sha256: object = None


@dataclass(frozen=True)
class ParsedModel:
    """A container's table of contents; no tensor payload is loaded."""

    format: str
    path: str
    tensors: tuple
    data_start: int
    total_bytes: int
    metadata: dict = field(default_factory=dict)
    kv: dict = field(default_factory=dict)
    alignment: int = 1
    version: int = 0


@dataclass(frozen=True)
class ModelDigest:
    """The canonical model digest plus the per-tensor digests behind it."""

    format: str
    path: str
    model_digest: str
    tensors: tuple
    total_bytes: int
    partial: bool = False

    @property
    def tensor_count(self):
        return len(self.tensors)
