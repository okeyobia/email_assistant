# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

# Install uv so dependency management works the same as the original base image
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . /app

# Install dependencies into the project-local .venv
RUN uv sync --frozen

ENV UV_PROJECT_ENV=.venv
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "email-assistant"]
CMD ["fetch"]
