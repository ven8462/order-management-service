# ---- Stage 1: The Builder ----
FROM python:3.12-slim as builder

ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN apt-get update \
    && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 -


ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app


COPY poetry.lock pyproject.toml ./


RUN poetry install --no-interaction --no-ansi --only main --no-root


# ---- Stage 2: The Final Image ----
FROM python:3.12-slim


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


RUN apt-get update \
    && apt-get install -y libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY --from=builder /app/.venv ./.venv


COPY ./order_service /app/order_service

ENV PATH="/app/.venv/bin:$PATH"


EXPOSE 8000


CMD ["uvicorn", "order_service.main:app", "--host", "0.0.0.0", "--port", "8000"]