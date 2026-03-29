# Use the official smaller Python image from the Docker Hub
FROM python:3.12-slim

# Install UV from Astral.sh
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Copy ONLY dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies as a separate layer
# This layer only rebuilds when pyproject.toml or uv.lock changes
RUN uv sync --locked --no-install-project

# Now copy the rest of your code, copy the project into the image
# This layer rebuilds on every code change, but that's fine
# because dependency installation is already cached above
COPY . .

# Expose the port of my flask app (not technically needed because in docker compose)
EXPOSE 8501