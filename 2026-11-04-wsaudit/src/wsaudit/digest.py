"""Per-tensor hashing and the canonical model digest."""

import hashlib
import os
import struct

from . import gguf, safetensors
from .errors import WsAuditError
from .models import ModelDigest, TensorDigest

CHUNK = 4 * 1024 * 1024


def parse_model(path):
    """Detect the container from its magic and return its table of contents."""
    try:
        with open(path, "rb") as fh:
            magic = fh.read(4)
    except OSError as exc:
        raise WsAuditError("cannot read %s (%s)" % (path, exc))
    if magic == gguf.MAGIC:
        return gguf.parse(path)
    return safetensors.parse(path)


def tensor_sha256(fh, tensor):
    """sha256 over exactly the tensor's byte range, streamed."""
    fh.seek(tensor.offset)
    digest = hashlib.sha256()
    remaining = tensor.nbytes
    while remaining:
        block = fh.read(min(CHUNK, remaining))
        if not block:
            raise WsAuditError(
                "short read inside %r at byte %d" % (tensor.name, fh.tell())
            )
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def canonical_digest(tensor_digests, partial=False):
    """One digest over the sorted (name, dtype, shape, hash) tuples.

    Every field is length-prefixed so ('a|b','cc') cannot collide with
    ('a','bb|cc') - the boundary is encoded, not assumed.
    """
    hasher = hashlib.sha256()
    hasher.update(b"wsaudit/v1\n")
    hasher.update(b"partial\n" if partial else b"full\n")
    for item in sorted(tensor_digests, key=lambda d: d.name):
        shape = ",".join(str(dim) for dim in item.shape)
        sha = item.sha256 or ""
        line = "%d:%s%d:%s%d:%s%d:%s\n" % (
            len(item.name), item.name,
            len(item.dtype), item.dtype,
            len(shape), shape,
            len(sha), sha,
        )
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def digest_parsed(parsed, header_only=False):
    """Digest an already-parsed model. Opens the file once for all tensors."""
    if header_only:
        digests = tuple(
            TensorDigest(t.name, t.dtype, t.shape, None) for t in parsed.tensors
        )
    else:
        digests = []
        try:
            with open(parsed.path, "rb") as fh:
                for tensor in parsed.tensors:
                    digests.append(
                        TensorDigest(
                            tensor.name,
                            tensor.dtype,
                            tensor.shape,
                            tensor_sha256(fh, tensor),
                        )
                    )
        except OSError as exc:
            raise WsAuditError("cannot hash %s (%s)" % (parsed.path, exc))
        digests = tuple(digests)
    return ModelDigest(
        format=parsed.format,
        path=parsed.path,
        model_digest=canonical_digest(digests, partial=header_only),
        tensors=digests,
        total_bytes=parsed.total_bytes,
        partial=header_only,
    )


def digest_model(path, header_only=False):
    if not os.path.exists(path):
        raise WsAuditError("no such file: %s" % path)
    return digest_parsed(parse_model(path), header_only=header_only)


def float_values(path, tensor, max_bytes=256 * 1024 * 1024):
    """Decode a float tensor to Python floats; None when that is not possible.

    Returns None (never a guess) for quantised or oversized tensors.
    """
    if tensor.nbytes > max_bytes:
        return None
    code = {"F64": "d", "F32": "f", "F16": "e"}.get(tensor.dtype)
    try:
        with open(path, "rb") as fh:
            fh.seek(tensor.offset)
            raw = fh.read(tensor.nbytes)
    except OSError as exc:
        raise WsAuditError("cannot read %r (%s)" % (tensor.name, exc))
    if len(raw) != tensor.nbytes:
        raise WsAuditError("short read while decoding %r" % tensor.name)
    if tensor.dtype == "BF16":
        return [
            struct.unpack("<f", b"\x00\x00" + raw[i:i + 2])[0]
            for i in range(0, len(raw) - 1, 2)
        ]
    if code is None:
        return None
    import array
    values = array.array(code)
    usable = len(raw) - (len(raw) % values.itemsize)
    values.frombytes(raw[:usable])
    return values.tolist()
