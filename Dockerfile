FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock* ./

# Install production dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ src/
COPY server.py .

# Environment variables
ENV HOST=0.0.0.0 \
    PORT=3001 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

EXPOSE 3001

ENTRYPOINT ["uv", "run", "server.py"]
CMD ["--stdio"]
