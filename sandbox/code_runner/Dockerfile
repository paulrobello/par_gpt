FROM python:3.12.2-slim-bullseye

# Security best practices
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user with its home directory
RUN useradd --create-home pythonuser
USER pythonuser
WORKDIR /code
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/pythonuser/.local/bin:${PATH}"
RUN /home/pythonuser/.local/bin/uv venv .venv

# Optional: Only if you have specific dependencies
# COPY --chown=appuser:appuser requirements.txt .
# RUN pip install --user -r requirements.txt
