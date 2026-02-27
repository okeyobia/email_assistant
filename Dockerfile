# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.11

WORKDIR /app
COPY . /app

# Install dependencies into the project-local .venv
RUN uv sync --frozen

ENV UV_PROJECT_ENV=.venv
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "email-assistant"]
CMD ["fetch"]
