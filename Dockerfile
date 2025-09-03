# Use Python 3.13 on Debian Bullseye (slim = smallest variant)
FROM python:3.13-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry"

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # for cloning repos / VCS
        git \
        # for downloading scripts / installers
        curl \
        # for compiling Python packages
        build-essential \
        # PostgreSQL client libraries for psycopg2
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies (production by default)
# Use build arg INSTALL_DEV=true to include dev dependencies
ARG INSTALL_DEV=false
RUN poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV" = "true" ]; then \
         poetry install --with dev --no-root; \
       else \
         poetry install --without dev --no-root; \
       fi

# Copy the rest of the app source
COPY . .

# Expose ports for the app
EXPOSE 8000

# Command to start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
