"""safetensors reader: u64 header length + JSON table of contents + data blob."""

import json
import os
import struct

from .errors import WsAuditError
from .models import ParsedModel, Tensor

# dtype -> bytes per element
DTYPE_SIZES = {
    "F64": 8, "F32": 4, "F16": 2, "BF16": 2,
    "I64": 8, "I32": 4, "I16": 2, "I8": 1,
    "U64": 8, "U32": 4, "U16": 2, "U8": 1,
    "BOOL": 1, "F8_E4M3": 1, "F8_E5M2": 1,
}

MAX_HEADER = 256 * 1024 * 1024   # a header this large is not a safetensors file


def _elements(shape):
    total = 1
    for dim in shape:
        total *= dim
    return total


ZIP_MAGIC = b"PK\x03\x04"


def _read_header(fh, size):
    raw_len = fh.read(8)
    if len(raw_len) != 8:
        raise WsAuditError("safetensors: file shorter than an 8-byte header length")
    if raw_len[:4] == ZIP_MAGIC:
        # Real case on this host: PEFT adapters saved with torch.save keep a
        # .safetensors name but are zip archives holding adapter_model/data.pkl.
        raise WsAuditError(
            "safetensors: this file is a ZIP archive, not a safetensors file "
            "(a torch.save/PEFT pickle container). Re-export it with "
            "safetensors.torch.save_file(); wsaudit will not unpickle model data."
        )
    (header_len,) = struct.unpack("<Q", raw_len)
    if header_len > MAX_HEADER:
        raise WsAuditError(
            "safetensors: header length %d exceeds the %d-byte sanity limit"
            % (header_len, MAX_HEADER)
        )
    if 8 + header_len > size:
        raise WsAuditError(
            "safetensors: header claims %d bytes but the file holds %d"
            % (header_len, size - 8)
        )
    raw = fh.read(header_len)
    try:
        header = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise WsAuditError("safetensors: header is not valid JSON (%s)" % exc)
    if not isinstance(header, dict):
        raise WsAuditError("safetensors: header JSON is not an object")
    return header, 8 + header_len


def _tensor_from_entry(name, entry, data_start, size):
    if not isinstance(entry, dict):
        raise WsAuditError("safetensors: entry for %r is not an object" % name)
    dtype = entry.get("dtype")
    shape = entry.get("shape")
    offsets = entry.get("data_offsets")
    if dtype is None or shape is None or offsets is None:
        raise WsAuditError(
            "safetensors: entry %r needs dtype, shape and data_offsets" % name
        )
    if dtype not in DTYPE_SIZES:
        raise WsAuditError("safetensors: unsupported dtype %r on %r" % (dtype, name))
    if not isinstance(shape, list) or any(
        not isinstance(dim, int) or dim < 0 for dim in shape
    ):
        raise WsAuditError("safetensors: bad shape on %r" % name)
    if not isinstance(offsets, list) or len(offsets) != 2:
        raise WsAuditError("safetensors: bad data_offsets on %r" % name)
    begin, end = offsets
    if not isinstance(begin, int) or not isinstance(end, int):
        raise WsAuditError("safetensors: non-integer data_offsets on %r" % name)
    if begin < 0 or end < begin:
        raise WsAuditError(
            "safetensors: inverted data_offsets %r on %r" % (offsets, name)
        )
    if data_start + end > size:
        raise WsAuditError(
            "safetensors: %r ends at byte %d past the end of the %d-byte file"
            % (name, data_start + end, size)
        )
    elements = _elements(shape)
    expected = elements * DTYPE_SIZES[dtype]
    if end - begin != expected:
        raise WsAuditError(
            "safetensors: %r declares %d elements of %s (%d bytes) but occupies %d"
            % (name, elements, dtype, expected, end - begin)
        )
    return Tensor(
        name=name,
        dtype=dtype,
        shape=tuple(shape),
        offset=data_start + begin,
        nbytes=end - begin,
        elements=elements,
    )


def parse(path):
    """Read the table of contents. Never touches tensor payload."""
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise WsAuditError("safetensors: cannot stat %s (%s)" % (path, exc))
    try:
        with open(path, "rb") as fh:
            header, data_start = _read_header(fh, size)
    except OSError as exc:
        raise WsAuditError("safetensors: cannot read %s (%s)" % (path, exc))

    metadata = header.pop("__metadata__", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise WsAuditError("safetensors: __metadata__ is not an object")

    tensors = tuple(
        _tensor_from_entry(name, entry, data_start, size)
        for name, entry in header.items()
    )
    return ParsedModel(
        format="safetensors",
        path=path,
        tensors=tensors,
        data_start=data_start,
        total_bytes=size - data_start,
        metadata=metadata,
    )
