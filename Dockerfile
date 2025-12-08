# Code Whisperers - Standalone Docker Image
# Pull: docker pull ghcr.io/sethjchalmers/code-whisperers:latest
# Run:  docker run -v $(pwd):/repo -e GITHUB_TOKEN=$GITHUB_TOKEN ghcr.io/sethjchalmers/code-whisperers review --base main

FROM python:3.12-slim

LABEL maintainer="sethjchalmers"
LABEL org.opencontainers.image.title="Code Whisperers"
LABEL org.opencontainers.image.description="Multi-Agent AI Code Review Pipeline - 8 specialized experts for Terraform, GitOps, Jenkins, Python, Security, Cost, Clean Code, and AWS"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/sethjchalmers/code-whisperers"
LABEL org.opencontainers.image.url="https://github.com/sethjchalmers/code-whisperers"
LABEL org.opencontainers.image.documentation="https://github.com/sethjchalmers/code-whisperers#readme"
LABEL org.opencontainers.image.licenses="MIT"

# Install git (needed for git operations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd --create-home codewhisperer && \
    chown -R codewhisperer:codewhisperer /app
USER codewhisperer

# Configure git for the container
RUN git config --global --add safe.directory '*'

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Entrypoint that runs the CLI
ENTRYPOINT ["python", "-m", "cli.main"]
CMD ["--help"]
