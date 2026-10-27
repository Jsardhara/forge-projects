"""How much memory is actually left for the KV pool.

Everything here is a derivation, not a measurement: `gpu_memory_utilization` asks the
engine for a ceiling, and the engine then reserves room for weights, activations,
CUDA graphs and the driver. The result is an UPPER BOUND and is labelled as one in
every report, because a preflight that quietly overstates the pool is the exact
assumption that leaked 155 responses at Cloudflare.
"""


def kv_budget_bytes(gpu_memory_utilization, device_vram_bytes, num_gpus,
                    weights_bytes, overhead_bytes=0):
    """Bytes left for KV cache across all ranks, after weights and overhead."""
    if device_vram_bytes is None:
        raise ValueError("device_vram_bytes is required")
    if not 0 < gpu_memory_utilization <= 1:
        raise ValueError("gpu_memory_utilization must be in (0, 1], got %r"
                         % (gpu_memory_utilization,))
    total = int(device_vram_bytes) * int(num_gpus) * float(gpu_memory_utilization)
    return int(total) - int(weights_bytes) - int(overhead_bytes)
