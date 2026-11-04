"""Byte-level fixture builders for the two container formats.

These write REAL files, not mocks: a safetensors file is a u64 header length
plus JSON plus a data blob, and a GGUF file is a documented little-endian
header. Tests therefore exercise the same code path a 16 GB file does.
"""

import json
import struct

GGUF_MAGIC = b"GGUF"

# ggml type id -> (name, block_size, type_size_bytes)
GGML_TYPES = {
    0: ("F32", 1, 4),
    1: ("F16", 1, 2),
    2: ("Q4_0", 32, 18),
    8: ("Q8_0", 32, 34),
    12: ("Q4_K", 256, 144),
    14: ("Q6_K", 256, 210),
    30: ("BF16", 1, 2),
}


def align_up(n, alignment):
    if alignment <= 0:
        return n
    rem = n % alignment
    return n if rem == 0 else n + (alignment - rem)


def write_safetensors(path, tensors, metadata=None):
    """tensors: list of (name, dtype, shape, raw_bytes)."""
    header = {}
    blob = b""
    for name, dtype, shape, raw in tensors:
        header[name] = {
            "dtype": dtype,
            "shape": list(shape),
            "data_offsets": [len(blob), len(blob) + len(raw)],
        }
        blob += raw
    if metadata is not None:
        header["__metadata__"] = metadata
    raw_header = json.dumps(header).encode("utf-8")
    pad = (8 - (len(raw_header) % 8)) % 8
    raw_header += b" " * pad
    with open(path, "wb") as fh:
        fh.write(struct.pack("<Q", len(raw_header)))
        fh.write(raw_header)
        fh.write(blob)
    return path


def _gguf_string(text):
    raw = text.encode("utf-8") if isinstance(text, str) else text
    return struct.pack("<Q", len(raw)) + raw


def _gguf_value(value_type, value):
    if value_type == 4:      # uint32
        return struct.pack("<I", value)
    if value_type == 8:      # string
        return _gguf_string(value)
    if value_type == 6:      # float32
        return struct.pack("<f", value)
    if value_type == 7:      # bool
        return struct.pack("<B", 1 if value else 0)
    if value_type == 9:      # array of strings
        out = struct.pack("<IQ", 8, len(value))
        for item in value:
            out += _gguf_string(item)
        return out
    raise ValueError("fixture does not build value_type %r" % (value_type,))


def write_gguf(path, tensors, kv=(), alignment=32, version=3, pad_tensors=True):
    """tensors: list of (name, ggml_type_id, dims, raw_bytes).

    ``raw_bytes`` is written verbatim, so tests control the exact payload.
    """
    kv = list(kv)
    keys = {k: v for k, v in kv}
    if "general.alignment" in keys:
        alignment = keys["general.alignment"][1]
    else:
        kv.append(("general.alignment", (4, alignment)))

    meta = bytearray()
    meta += GGUF_MAGIC
    meta += struct.pack("<I", version)
    meta += struct.pack("<Q", len(tensors))
    meta += struct.pack("<Q", len(kv))
    for key, (vtype, value) in kv:
        meta += _gguf_string(key)
        meta += struct.pack("<I", vtype)
        meta += _gguf_value(vtype, value)

    offset = 0
    infos = bytearray()
    for name, type_id, dims, raw in tensors:
        infos += _gguf_string(name)
        infos += struct.pack("<I", len(dims))
        for dim in dims:
            infos += struct.pack("<Q", dim)
        infos += struct.pack("<I", type_id)
        infos += struct.pack("<Q", offset)
        offset += len(raw) if pad_tensors else 0

    header_end = align_up(len(meta) + len(infos), alignment)
    pad_len = header_end - (len(meta) + len(infos))
    with open(path, "wb") as fh:
        fh.write(bytes(meta) + bytes(infos) + b"\x00" * pad_len)
        for _name, _type_id, _dims, raw in tensors:
            fh.write(raw)
    return path


def gbytes(n, seed=0):
    """Deterministic payload of n bytes."""
    return bytes(((i * 31 + seed * 7) & 0xFF) for i in range(n))


def gguf_tensor(type_id, dims, seed=0):
    """Raw payload sized for a real (block, type_size) pair."""
    name, block, tsize = GGML_TYPES[type_id]
    elements = 1
    for dim in dims:
        elements *= dim
    nbytes = (elements // block) * tsize
    return gbytes(nbytes, seed)
