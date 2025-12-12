FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies
RUN uv sync --no-dev

# Create data directory
RUN mkdir -p /app/data

ENTRYPOINT ["uv", "run", "python", "-m", "src.main"]
