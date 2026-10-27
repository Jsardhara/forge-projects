"""The verdict: does the pool hold the context the configuration advertises?

Three answers, and UNKNOWN is a real one. Cloudflare's incident began with the belief
that the engine would return an error for a prompt it could not process; a preflight
that answers PASS on a number it could not establish is the same belief with better
formatting.
"""

from . import arith
from .budget import kv_budget_bytes

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"

EXIT_CODES = {PASS: 0, FAIL: 1, UNKNOWN: 2}


class Inputs(object):
    """Everything the operator declared about the deployment (not the model)."""

    def __init__(self, max_model_len, tensor_parallel_size=1, gpu_memory_utilization=0.90,
                 device_vram_bytes=None, num_gpus=None, weights_bytes=None,
                 overhead_bytes=0, kv_cache_dtype="auto", block_size=16,
                 max_num_seqs=None):
        self.max_model_len = int(max_model_len)
        self.tensor_parallel_size = int(tensor_parallel_size)
        self.gpu_memory_utilization = float(gpu_memory_utilization)
        self.device_vram_bytes = device_vram_bytes
        self.num_gpus = int(num_gpus) if num_gpus is not None else self.tensor_parallel_size
        self.weights_bytes = weights_bytes
        self.overhead_bytes = int(overhead_bytes or 0)
        self.kv_cache_dtype = kv_cache_dtype
        self.block_size = int(block_size)
        self.max_num_seqs = int(max_num_seqs) if max_num_seqs is not None else None


class Report(object):
    def __init__(self, verdict, headline, notes, facts):
        self.verdict = verdict
        self.exit_code = EXIT_CODES[verdict]
        self.headline = headline
        self.notes = notes
        self.facts = facts

    def __getattr__(self, item):
        # Facts are addressable as attributes for readable call sites in tests.
        try:
            return self.__dict__["facts"][item]
        except KeyError:
            raise AttributeError(item)


def _gib(value):
    return "%.2f GiB" % (float(value) / (1024 ** 3))


def _tokens(value):
    return "{:,}".format(int(value))


def evaluate(shape, inputs):
    notes = []
    facts = {
        "model": shape.name,
        "layers": shape.layers,
        "kv_heads": shape.kv_heads,
        "head_dim": shape.head_dim,
        "model_dtype": shape.dtype,
        "kv_cache_dtype": inputs.kv_cache_dtype,
        "tensor_parallel_size": inputs.tensor_parallel_size,
        "num_gpus": inputs.num_gpus,
        "block_size": inputs.block_size,
        "max_model_len": inputs.max_model_len,
        "bytes_per_token": None,
        "kv_budget_bytes": None,
        "pool_tokens": None,
    }

    try:
        heads, split_note = arith.kv_heads_per_rank(shape.kv_heads,
                                                   inputs.tensor_parallel_size)
    except arith.UnknownFact as exc:
        return _unknown(notes, facts, "cannot split KV heads across ranks: %s" % exc)
    facts["kv_heads_per_rank"] = heads
    if split_note:
        notes.append(split_note)

    if shape.sliding_window:
        notes.append("model declares sliding_window=%s: only that window of KV is "
                     "retained per sequence, so the pool holds more prompts than the "
                     "advertised context implies (the context itself is still limited)"
                     % shape.sliding_window)

    weights = inputs.weights_bytes
    if weights is None:
        weights = shape.weights_bytes
    if weights is None:
        return _unknown(
            notes, facts,
            "cannot establish the weight footprint: no safetensors files next to "
            "config.json and --weights-gb was not given")

    if inputs.device_vram_bytes is None:
        return _unknown(
            notes, facts,
            "cannot establish device VRAM per GPU: pass --device-vram-gb "
            "(device_vram was not supplied and cannot be measured offline)")

    try:
        bpt = arith.bytes_per_token(shape, inputs.tensor_parallel_size,
                                    inputs.kv_cache_dtype)
    except arith.UnknownFact as exc:
        return _unknown(notes, facts, "cannot compute bytes per token: %s" % exc)
    facts["bytes_per_token"] = bpt
    facts["kib_per_token"] = round(bpt / 1024.0, 3)

    try:
        budget = kv_budget_bytes(inputs.gpu_memory_utilization, inputs.device_vram_bytes,
                                 inputs.num_gpus, weights, inputs.overhead_bytes)
    except ValueError as exc:
        return _unknown(notes, facts, "cannot compute the KV budget: %s" % exc)
    facts["kv_budget_bytes"] = budget
    facts["weights_bytes"] = weights
    facts["overhead_bytes"] = inputs.overhead_bytes
    notes.append("gpu_memory_utilization=%s is a request, not a measurement; the %s "
                 "KV budget is an UPPER BOUND (activations, CUDA graphs and driver "
                 "reservations are not modelled)"
                 % (inputs.gpu_memory_utilization, _gib(max(budget, 0))))

    pool = arith.pool_tokens(budget, inputs.block_size, bpt)
    facts["pool_tokens"] = pool
    facts["pool_blocks"] = pool // inputs.block_size

    if budget <= 0:
        notes.append("the weights and overhead alone exceed the requested memory "
                     "ceiling: no KV pool exists at all at this configuration")

    if inputs.max_num_seqs and pool < inputs.max_model_len * inputs.max_num_seqs:
        notes.append("concurrency: a pool of %s tokens serves %d sequence(s) at full "
                     "%s-token context, not the requested max_num_seqs=%d"
                     % (_tokens(pool), pool // max(inputs.max_model_len, 1),
                        _tokens(inputs.max_model_len), inputs.max_num_seqs))

    if pool >= inputs.max_model_len:
        headline = ("PASS: KV pool holds %s tokens >= advertised context %s "
                    "(%.2f GiB budget, %s bytes/token)"
                    % (_tokens(pool), _tokens(inputs.max_model_len),
                       budget / float(1024 ** 3), _tokens(bpt)))
        return Report(PASS, headline, notes, facts)

    shortfall = inputs.max_model_len - pool
    missing_pct = 100.0 * shortfall / max(inputs.max_model_len, 1)
    headline = ("FAIL: KV pool holds %s tokens, %s short of the advertised %s "
                "(%.1f%% of the context does not exist; %s bytes/token, %s budget)"
                % (_tokens(pool), _tokens(shortfall), _tokens(inputs.max_model_len),
                   missing_pct, _tokens(bpt), _gib(max(budget, 0))))
    return Report(FAIL, headline, notes, facts)


def _unknown(notes, facts, reason):
    notes.append(reason)
    headline = "UNKNOWN: %s" % reason
    return Report(UNKNOWN, headline, notes, facts)


def to_dict(report):
    payload = dict(report.facts)
    payload["verdict"] = report.verdict
    payload["exit_code"] = report.exit_code
    payload["headline"] = report.headline
    payload["notes"] = list(report.notes)
    return payload


def render_text(report):
    lines = [report.headline]
    rows = [
        ("model", report.facts.get("model")),
        ("layers x kv_heads x head_dim",
         "%s x %s x %s" % (report.facts.get("layers"), report.facts.get("kv_heads"),
                           report.facts.get("head_dim"))),
        ("kv heads per rank (tp=%s)" % report.facts.get("tensor_parallel_size"),
         report.facts.get("kv_heads_per_rank")),
        ("bytes per token", report.facts.get("bytes_per_token")),
        ("kv budget", _gib(report.facts["kv_budget_bytes"])
         if report.facts.get("kv_budget_bytes") is not None else None),
        ("pool tokens", _tokens(report.facts["pool_tokens"])
         if report.facts.get("pool_tokens") is not None else None),
        ("advertised context", _tokens(report.facts.get("max_model_len"))),
    ]
    for label, value in rows:
        if value is not None:
            lines.append("  %-28s %s" % (label + ":", value))
    if report.notes:
        lines.append("  notes:")
        for note in report.notes:
            lines.append("    - %s" % note)
    return "\n".join(lines)
