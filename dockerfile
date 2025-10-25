# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Install UV from Astral.sh
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the project into the image
ADD . /app

# Set the working directory in the container
WORKDIR /app

# Sync the project into a new environment, asserting the lockfile is up to date
RUN uv sync --locked

# Expose the port of my flask app (not technically needed because in docker compose)
EXPOSE 8501

# Not technically needed here because I've incldued this code in my docker compose file
CMD []