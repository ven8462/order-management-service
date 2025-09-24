# ---- Stage 1: The Builder ----
# CORRECTED: Use Python 3.12 to match your project's requirements
FROM python:3.12-slim as builder

# Set environment variables for Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install Poetry
RUN apt-get update \
    && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY poetry.lock pyproject.toml ./

# Install only the main dependencies (no dev packages)
RUN poetry install --no-interaction --no-ansi --only main --no-root


# ---- Stage 2: The Final Image ----
# This stage builds the lean, production-ready image.
# CORRECTED: Also use Python 3.12 for the final runtime
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only the necessary runtime library for PostgreSQL
RUN apt-get update \
    && apt-get install -y libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Copy the application source code
COPY ./order_service /app/order_service

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "order_service.main:app", "--host", "0.0.0.0", "--port", "8000"]