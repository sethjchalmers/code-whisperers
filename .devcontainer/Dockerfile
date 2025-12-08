# Code Whisperers Dev Container
FROM python:3.12-slim

LABEL maintainer="sethjchalmers"
LABEL description="The Code Whisperers - Multi-Agent Code Review Pipeline"
LABEL version="1.0.0"

# Avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Install the package in development mode
RUN pip install --no-cache-dir -e '.[dev]'

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash codewhisperer
USER codewhisperer

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default command shows help
CMD ["python", "-m", "cli.main", "--help"]
