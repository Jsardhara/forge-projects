FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY signal_feed/ signal_feed/

ENV DATABASE_URL="sqlite+aiosqlite:///data/signals.db"
ENV HOST="0.0.0.0"
ENV PORT="8000"

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "signal_feed.api:app", "--host", "0.0.0.0", "--port", "8000"]
