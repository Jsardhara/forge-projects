"""Read a model's real config.json and measure its weight footprint.

No transformers, no torch: a KV pool is arithmetic over values that already sit in
config.json, and reading them with a 2 GB dependency would be the wrong trade.
"""

import json
import os


class ConfigError(Exception):
    """The model configuration could not be read or is missing a required field."""


class ModelShape(object):
    """Everything about a model that changes the size of one cache token."""

    def __init__(self, name, layers, kv_heads, attn_heads, head_dim, dtype,
                 sliding_window=None, weights_bytes=None):
        self.name = name
        self.layers = layers
        self.kv_heads = kv_heads
        self.attn_heads = attn_heads
        self.head_dim = head_dim
        self.dtype = dtype
        self.sliding_window = sliding_window
        self.weights_bytes = weights_bytes

    def __repr__(self):
        return ("ModelShape(name=%r, layers=%r, kv_heads=%r, head_dim=%r, dtype=%r)"
                % (self.name, self.layers, self.kv_heads, self.head_dim, self.dtype))


def _config_path(model_path):
    if os.path.isdir(model_path):
        return os.path.join(model_path, "config.json")
    return model_path


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise ConfigError("cannot read %s: %s" % (path, exc))
    except ValueError as exc:
        raise ConfigError("cannot parse %s: %s" % (path, exc))


def _require(payload, key, path):
    if key not in payload or payload[key] in (None, 0):
        raise ConfigError("%s: missing required field %r" % (path, key))
    return payload[key]


def _weights_bytes(directory, payload):
    """Measured bytes, never a parameter-count guess.

    Preference order: the safetensors index total_size (authoritative for sharded
    checkpoints), then the real file sizes on disk. A guess from parameter counts is
    exactly the kind of estimate this tool exists to refuse.
    """
    index = os.path.join(directory, "model.safetensors.index.json")
    if os.path.isfile(index):
        try:
            with open(index, "r", encoding="utf-8") as fh:
                total = json.load(fh).get("metadata", {}).get("total_size")
            if total:
                return int(total)
        except (OSError, ValueError, AttributeError):
            pass
    total = 0
    found = False
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".safetensors"):
            continue
        try:
            total += os.path.getsize(os.path.join(directory, name))
            found = True
        except OSError:
            continue
    return total if found else None


def _derive_name(directory):
    """Readable model name, including from a HuggingFace cache snapshot layout."""
    parent = os.path.basename(os.path.dirname(directory))
    if parent == "snapshots":
        parent = os.path.basename(os.path.dirname(os.path.dirname(directory)))
    if parent.startswith("models--"):
        return parent[len("models--"):].replace("--", "/")
    base = os.path.basename(directory)
    if base in ("", "snapshots"):
        return os.path.basename(os.path.dirname(os.path.dirname(directory))) or "model"
    return base


def load_model_shape(model_path):
    """Parse config.json into a ModelShape. Raises ConfigError naming the file."""
    path = _config_path(model_path)
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ConfigError("%s: config.json is not a JSON object" % path)

    layers = int(_require(payload, "num_hidden_layers", path))
    attn_heads = int(_require(payload, "num_attention_heads", path))
    hidden = int(_require(payload, "hidden_size", path))
    kv_heads = int(payload.get("num_key_value_heads") or attn_heads)

    head_dim = payload.get("head_dim")
    head_dim = int(head_dim) if head_dim else hidden // attn_heads
    if head_dim <= 0:
        raise ConfigError("%s: cannot derive head_dim from hidden_size/num_attention_heads"
                          % path)

    dtype = payload.get("torch_dtype") or payload.get("dtype") or "unknown"

    sliding_window = payload.get("sliding_window")
    if sliding_window and not payload.get("use_sliding_window", True):
        sliding_window = None

    directory = os.path.dirname(os.path.abspath(path))
    name = payload.get("_name_or_path") or _derive_name(directory)

    return ModelShape(
        name=name,
        layers=layers,
        kv_heads=kv_heads,
        attn_heads=attn_heads,
        head_dim=head_dim,
        dtype=str(dtype),
        sliding_window=sliding_window,
        weights_bytes=_weights_bytes(directory, payload),
    )
