# Code Whisperers - Standalone Docker Image
# Build: docker build -t code-whisperers .
# Run:   docker run -v $(pwd):/repo -e GITHUB_TOKEN=$GITHUB_TOKEN code-whisperers review /repo

FROM python:3.12-slim

LABEL maintainer="sethjchalmers"
LABEL description="The Code Whisperers - Multi-Agent Code Review Pipeline"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/sethjchalmers/code-whisperers"

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
