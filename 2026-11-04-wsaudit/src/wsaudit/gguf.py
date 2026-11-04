"""GGUF reader: magic, KV block, tensor-info table, then page-aligned data.

Only the header is parsed. Tensor payloads are addressed by absolute offset and
never read here, so a 19 GB file costs a few MB of RAM to inspect.
"""

import os
import struct

from .errors import WsAuditError
from .models import ParsedModel, Tensor

MAGIC = b"GGUF"
SUPPORTED_VERSIONS = (2, 3)

# ggml type id -> (name, elements per block, bytes per block)
GGML_TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 36),
    10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176), 14: ("Q6_K", 256, 210), 15: ("Q8_K", 256, 292),
    16: ("IQ2_XXS", 256, 66), 17: ("IQ2_XS", 256, 74), 18: ("IQ3_XXS", 256, 98),
    19: ("IQ1_S", 256, 50), 20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 110),
    22: ("IQ2_S", 256, 82), 23: ("IQ4_XS", 256, 136), 24: ("I8", 1, 1),
    25: ("I16", 1, 2), 26: ("I32", 1, 4), 27: ("I64", 1, 8), 28: ("F64", 1, 8),
    29: ("IQ1_M", 256, 56), 30: ("BF16", 1, 2),
}

# GGUF value type ids
UINT8, INT8, UINT16, INT16 = 0, 1, 2, 3
UINT32, INT32, FLOAT32, BOOL = 4, 5, 6, 7
STRING, ARRAY, UINT64, INT64, FLOAT64 = 8, 9, 10, 11, 12

_SCALAR = {
    UINT8: "<B", INT8: "<b", UINT16: "<H", INT16: "<h",
    UINT32: "<I", INT32: "<i", FLOAT32: "<f", BOOL: "<B",
    UINT64: "<Q", INT64: "<q", FLOAT64: "<d",
}
MAX_STORED_ARRAY = 4096   # tokenizer vocabularies are large; keep the header small


def align_up(value, alignment):
    if alignment <= 0:
        return value
    remainder = value % alignment
    return value if remainder == 0 else value + (alignment - remainder)


class _Reader:
    def __init__(self, fh, size):
        self.fh = fh
        self.size = size

    @property
    def pos(self):
        return self.fh.tell()

    def read(self, n, what):
        start = self.fh.tell()
        data = self.fh.read(n)
        if len(data) != n:
            raise WsAuditError(
                "gguf: truncated %s at byte %d (wanted %d, got %d)"
                % (what, start, n, len(data))
            )
        return data

    def u32(self, what):
        return struct.unpack("<I", self.read(4, what))[0]

    def u64(self, what):
        return struct.unpack("<Q", self.read(8, what))[0]

    def string(self, what):
        length = self.u64(what + " length")
        if length > self.size:
            raise WsAuditError("gguf: %s claims an impossible length %d" % (what, length))
        raw = self.read(length, what)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise WsAuditError("gguf: %s is not valid UTF-8" % what)

    def value(self, vtype, what):
        if vtype in _SCALAR:
            raw = self.read(struct.calcsize(_SCALAR[vtype]), what)
            value = struct.unpack(_SCALAR[vtype], raw)[0]
            return bool(value) if vtype == BOOL else value
        if vtype == STRING:
            return self.string(what)
        if vtype == ARRAY:
            return self._array(what)
        raise WsAuditError("gguf: unknown value type %d for %s" % (vtype, what))

    def _array(self, what):
        elem_type = self.u32(what + " array type")
        count = self.u64(what + " array count")
        if count * 8 > self.size:
            raise WsAuditError("gguf: %s array count %d exceeds file size" % (what, count))
        if count > MAX_STORED_ARRAY:
            self._skip(elem_type, count, what)
            return "<array of %d>" % count
        return [self.value(elem_type, what) for _ in range(count)]

    def _skip(self, elem_type, count, what):
        if elem_type in _SCALAR:
            self.read(struct.calcsize(_SCALAR[elem_type]) * count, what)
            return
        if elem_type == STRING:
            for _ in range(count):
                self.read(self.u64(what + " length"), what)
            return
        raise WsAuditError("gguf: cannot skip nested array type %d" % elem_type)


def parse(path):
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise WsAuditError("gguf: cannot stat %s (%s)" % (path, exc))
    try:
        with open(path, "rb") as fh:
            return _parse_open(fh, size, path)
    except OSError as exc:
        raise WsAuditError("gguf: cannot read %s (%s)" % (path, exc))


def _parse_open(fh, size, path):
    reader = _Reader(fh, size)
    if reader.read(4, "magic") != MAGIC:
        raise WsAuditError("gguf: bad magic (this is not a GGUF file)")
    version = reader.u32("version")
    if version not in SUPPORTED_VERSIONS:
        raise WsAuditError(
            "gguf: unsupported version %d (supported: %s)"
            % (version, ", ".join(str(v) for v in SUPPORTED_VERSIONS))
        )
    tensor_count = reader.u64("tensor count")
    kv_count = reader.u64("kv count")
    if tensor_count > size or kv_count > size:
        raise WsAuditError(
            "gguf: header claims %d tensors / %d metadata entries for a %d-byte file"
            % (tensor_count, kv_count, size)
        )

    kv = {}
    for index in range(kv_count):
        key = reader.string("metadata key %d" % index)
        vtype = reader.u32("metadata type for %r" % key)
        kv[key] = reader.value(vtype, "metadata value for %r" % key)

    entries = []
    for index in range(tensor_count):
        name = reader.string("tensor name %d" % index)
        n_dims = reader.u32("tensor rank for %r" % name)
        if n_dims > 8:
            raise WsAuditError("gguf: %r declares %d dimensions" % (name, n_dims))
        dims = tuple(reader.u64("tensor dim for %r" % name) for _ in range(n_dims))
        type_id = reader.u32("tensor type for %r" % name)
        offset = reader.u64("tensor offset for %r" % name)
        if type_id not in GGML_TYPES:
            raise WsAuditError(
                "gguf: %r uses unknown ggml type id %d" % (name, type_id)
            )
        dtype, block, type_size = GGML_TYPES[type_id]
        elements = 1
        for dim in dims:
            elements *= dim
        if block > 1 and elements % block:
            raise WsAuditError(
                "gguf: %r has %d elements, not a multiple of the %s block size %d"
                % (name, elements, dtype, block)
            )
        nbytes = elements // block * type_size
        entries.append((name, dtype, dims, offset, nbytes, elements))

    alignment = kv.get("general.alignment", 32)
    if not isinstance(alignment, int) or alignment <= 0:
        raise WsAuditError("gguf: general.alignment %r is not a positive integer" % (alignment,))
    data_start = align_up(reader.pos, alignment)
    if data_start > size:
        raise WsAuditError(
            "gguf: tensor data starts at %d, past the %d-byte file" % (data_start, size)
        )

    tensors = []
    for name, dtype, dims, offset, nbytes, elements in entries:
        absolute = data_start + offset
        if absolute + nbytes > size:
            raise WsAuditError(
                "gguf: %r ends at byte %d past the end of the %d-byte file"
                % (name, absolute + nbytes, size)
            )
        tensors.append(
            Tensor(
                name=name,
                dtype=dtype,
                shape=dims,
                offset=absolute,
                nbytes=nbytes,
                elements=elements,
            )
        )

    return ParsedModel(
        format="gguf",
        path=path,
        tensors=tuple(tensors),
        data_start=data_start,
        total_bytes=size - data_start,
        kv=kv,
        alignment=alignment,
        version=version,
    )
