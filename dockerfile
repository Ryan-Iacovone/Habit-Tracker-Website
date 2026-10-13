# Match the Python version pinned in pyproject.toml without the extra build tools.
FROM python:3.14.5-slim-bookworm

# Install UV from Astral.sh
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Copy ONLY dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies as a separate layer
# This layer only rebuilds when pyproject.toml or uv.lock changes
RUN uv sync --locked --no-install-project --no-dev

# Copy the app and its runtime assets after installing dependencies.
COPY . .

# Expose the port of my flask app (not technically needed because in docker compose)
EXPOSE 8501