"""The arithmetic: bytes per cache token, sharded across tensor-parallel ranks.

    bytes/token = 2 (K and V) x kv_heads_per_rank x head_dim x elem_bytes x layers

Two things this module refuses to do: guess a dtype it does not know, and round a
pool size up. A block that is half empty holds zero tokens.
"""

DTYPE_BYTES = {
    "float16": 2,
    "fp16": 2,
    "half": 2,
    "bfloat16": 2,
    "bf16": 2,
    "float32": 4,
    "fp32": 4,
    "float": 4,
    "float8_e4m3fn": 1,
    "float8_e5m2": 1,
    "float8_e4m3": 1,
    "fp8": 1,
    "fp8_e4m3": 1,
}


class UnknownFact(Exception):
    """A number required for the verdict could not be established."""


def dtype_bytes(dtype):
    key = str(dtype or "").strip().lower()
    if key not in DTYPE_BYTES:
        raise UnknownFact("unknown element type %r (known: %s)"
                          % (dtype, ", ".join(sorted(DTYPE_BYTES))))
    return DTYPE_BYTES[key]


def kv_heads_per_rank(kv_heads, tensor_parallel_size):
    """KV heads held by one rank, plus a note when the split is not clean.

    Returning a note rather than raising is deliberate: replication (tp larger than
    the KV head count) is legal and just wastes memory, while an uneven split is a
    configuration the engine may refuse to start. Both change the number of bytes a
    token costs, so the operator has to see them.
    """
    if tensor_parallel_size < 1:
        raise UnknownFact("tensor_parallel_size must be >= 1, got %r"
                          % (tensor_parallel_size,))
    if kv_heads < 1:
        raise UnknownFact("kv head count must be >= 1, got %r" % (kv_heads,))
    if tensor_parallel_size > kv_heads:
        return 1, ("tensor_parallel_size %d > %d KV heads: heads are replicated "
                   "across ranks, so the per-rank cache is one head, not 1/%d of it"
                   % (tensor_parallel_size, kv_heads, tensor_parallel_size))
    if kv_heads % tensor_parallel_size:
        heads = -(-kv_heads // tensor_parallel_size)
        return heads, ("%d KV heads are not divisible by tensor_parallel_size %d: "
                       "assuming %d heads per rank (ceil), verify with the engine"
                       % (kv_heads, tensor_parallel_size, heads))
    return kv_heads // tensor_parallel_size, None


def bytes_per_token(shape, tensor_parallel_size=1, kv_dtype="auto"):
    """Bytes of KV cache one token occupies on ONE rank."""
    dtype = shape.dtype if str(kv_dtype).lower() == "auto" else kv_dtype
    elem = dtype_bytes(dtype)
    heads, _note = kv_heads_per_rank(shape.kv_heads, tensor_parallel_size)
    return 2 * shape.layers * heads * shape.head_dim * elem


def pool_tokens(budget_bytes, block_size, bytes_per_token):
    """Tokens the budget buys, rounded DOWN to whole blocks."""
    if bytes_per_token <= 0:
        raise UnknownFact("bytes_per_token must be positive, got %r" % (bytes_per_token,))
    if block_size < 1:
        raise UnknownFact("block_size must be >= 1, got %r" % (block_size,))
    if budget_bytes <= 0:
        return 0
    blocks = int(budget_bytes) // (block_size * bytes_per_token)
    return blocks * block_size
