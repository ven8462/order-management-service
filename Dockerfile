# Use Python 3.13 slim
FROM python:3.13-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry"

# System deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        build-essential \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app

# Copy deps first
COPY pyproject.toml poetry.lock ./

# Install dependencies
ARG INSTALL_DEV=false
RUN poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV" = "true" ]; then \
         poetry install --with dev --no-root; \
       else \
         poetry install --without dev --no-root; \
       fi

# Copy project
COPY . .

EXPOSE 8000

# Default → dev server (overridden in compose for test/prod)
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]