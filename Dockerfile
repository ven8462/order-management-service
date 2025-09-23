# ---- Stage 1: The Builder ----
# This stage installs dependencies and builds our virtual environment.
FROM python:3.9-slim as builder

# Set environment variables for Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install Poetry
RUN apt-get update \
    && apt-get install -y curl \
    && curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy only the files needed for dependency installation to leverage Docker cache
COPY poetry.lock pyproject.toml ./

# Install project dependencies into a local .venv directory
# --no-dev ensures packages like pytest are not included
RUN poetry install --no-interaction --no-ansi --no-dev


# ---- Stage 2: The Final Image ----
# This stage builds the lean, production-ready image.
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only the necessary runtime dependencies
# 'libpq5' is the runtime library for PostgreSQL, unlike the bulky 'libpq-dev'
RUN apt-get update \
    && apt-get install -y libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
# This is the key step: we get all the Python packages without the build tools
COPY --from=builder /app/.venv ./.venv

# Copy the application source code
COPY ./order_service /app/order_service

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# **IMPORTANT**: Ensure "order_service.main:app" matches your file structure and FastAPI app variable name.
CMD ["uvicorn", "order_service.main:app", "--host", "0.0.0.0", "--port", "8000"]