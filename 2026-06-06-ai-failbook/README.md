# AI Failbook

**Structured AI failure mode database — catalog, search, and learn from AI fuckups.**

Every AI system fails in predictable ways. Hallucinations. Over-refusals. Context loss. Prompt injections. The problem isn't that these failures exist — it's that every team discovers them independently, with no shared knowledge base to learn from.

AI Failbook fixes that.

## Quick Start

```bash
# Install
uv pip install -e ".[dev]"

# Seed with sample data
failbook seed

# Search for hallucinations
failbook search --category hallucination

# Add a new failure mode
failbook add --title "My AI Fuckup" --description "What happened..." --severity high

# Show stats
failbook stats

# Start the API
failbook serve
```

## CLI Usage

```bash
# Search
failbook search                          # List all
failbook search --q "hallucination"      # Full-text search
failbook search --severity critical      # By severity
failbook search --category tool_use      # By category
failbook search --model "gpt-4"          # By model
failbook search --tag security           # By tag
failbook search --verified-only          # Only verified entries

# Show details
failbook show <vid>

# Add new failure
failbook add --title "..." --description "..." --severity high --category hallucination

# Upvote (mark as commonly encountered)
failbook upvote <vid>

# Delete
failbook delete <vid>

# Statistics
failbook stats

# JSON output (for scripting)
failbook search --q "injection" --json-output
```

## API Usage

```bash
# Start server
failbook serve --port 8100

# Or with uvicorn directly
uvicorn ai_failbook.api:app --reload
```

```bash
# Search
curl "http://localhost:8100/failures?category=hallucination&severity=high"

# Create
curl -X POST "http://localhost:8100/failures" \
  -H "Content-Type: application/json" \
  -d '{"title":"New Failure","description":"Details...","severity":"medium","category":"other"}'

# Get one
curl "http://localhost:8100/failures/<vid>"

# Upvote
curl -X POST "http://localhost:8100/failures/<vid>/upvote"

# Stats
curl "http://localhost:8100/stats"
```

Interactive docs at `http://localhost:8100/docs`

## Data Model

Each failure mode has:
- **vid**: Unique 8-char ID
- **title**: Short descriptive title
- **description**: Detailed description
- **severity**: low / medium / high / critical
- **category**: One of 12 failure categories
- **model**: AI model that exhibited the failure
- **expected_behavior**: What should have happened
- **actual_behavior**: What actually happened
- **workaround**: How to avoid or mitigate
- **source_url**: Link to original report
- **tags**: Searchable tags
- **upvotes**: Community upvote count
- **verified**: Whether the failure has been independently verified

## Failure Categories

- `hallucination` — Model generates false information
- `instruction_following` — Doesn't follow or over-follows instructions
- `context_window` — Context length related failures
- `safety_refusal` — Over/under-refusal of requests
- `tool_use` — API/tool calling failures
- `reasoning` — Logical errors, math mistakes
- `code_generation` — Vulnerable or incorrect code
- `prompt_injection` — External instructions hijack model
- `cost_token` — Unexpected token usage/cost spikes
- `latency` — Performance degradation
- `data_leak` — PII or sensitive data in outputs
- `other` — Uncategorized

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design and rationale.

## Testing

```bash
pytest tests/ -v
```

## Known Limitations

- Single-user SQLite (no concurrent writes)
- No authentication on API (local use only)
- No full-text search index (LIKE queries, sufficient for <10K entries)
- Tags stored as JSON string in SQLite (no native array type)

## Future Work

- [ ] Web UI for browsing failures
- [ ] Import from HN threads, Reddit, Twitter
- [ ] Weekly digest of new failures
- [ ] Integration with Jarmes agents (query before using AI tools)
- [ ] Multi-user support with Postgres backend
- [ ] Full-text search with SQLite FTS5
