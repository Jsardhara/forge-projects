# ModelRouter — GLM-5.2 OpenAI-Compatible Gateway

Drop-in OpenAI API replacement that routes to GLM-5.2 with automatic fallback, health checks, and cost tracking.

## Why

GLM-5.2 (MIT-licensed, open weights) beats GPT-5.5 on BenchLM (91 vs 87) and SWE-bench Pro (62.1 vs 58.6) at 1/10th the cost ($1.40/$4.40 vs $5/$30 per M tokens). ModelRouter lets you switch without changing your OpenAI SDK code — just change `base_url`.

## Features

- **Drop-in OpenAI compatibility**: Accepts standard OpenAI chat/completions requests
- **Model mapping**: Map OpenAI model names to GLM-5.2 (e.g., `gpt-4o` → `z-ai/glm-5.2`)
- **Automatic fallback**: Routes to backup provider on timeout/error
- **Health checks**: Lightweight probe endpoint for monitoring
- **Cost tracking**: Per-request cost calculation based on token usage + provider rates
- **Circuit breaker**: Stops routing to unhealthy providers after consecutive failures
- **Stdlib only**: Zero external dependencies for core routing logic

## Quick Start

```bash
pip install -e ".[dev]"
model-router demo
model-router health --base-url https://your-glm-endpoint/v1
model-router cost --input-tokens 1000 --output-tokens 500 --provider glm-5.2
```

## Python API

```python
from model_router import Router, Provider

glm = Provider(
    name="glm-5.2",
    base_url="https://your-glm-endpoint/v1",
    api_key="your-key",
    model_map={"gpt-4o": "z-ai/glm-5.2", "gpt-4o-mini": "z-ai/glm-5.2"},
    input_cost_per_mtok=1.40,
    output_cost_per_mtok=4.40,
)

openai_backup = Provider(
    name="openai",
    base_url="https://api.openai.com/v1",
    api_key="sk-...",
    model_map={},
    input_cost_per_mtok=5.0,
    output_cost_per_mtok=15.0,
)

router = Router(primary=glm, fallback=openai_backup)
result = router.route(model="gpt-4o", messages=[{"role": "user", "content": "Hello"}])
print(result.cost_usd, result.provider, result.model)
```

## Architecture

```
Client (OpenAI SDK) → Router → Primary Provider (GLM-5.2)
                                  ↓ (on failure)
                                Fallback Provider (OpenAI)
```

## License

MIT
