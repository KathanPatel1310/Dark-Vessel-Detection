# ==============================================================================
# Stage 1: Build Frontend (Vite + React 18 + TypeScript + Tailwind)
# ==============================================================================
FROM node:20-slim AS frontend-builder
WORKDIR /app/web

# Install dependencies with caching
COPY web/package*.json ./
RUN npm ci

# Copy web source and build production bundle
COPY web/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Runtime Environment (Python 3.12 + FastAPI + AI/CV Engines)
# ==============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install system runtime dependencies for OpenCV, GDAL/Shapely, and curl healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only (saves ~2GB of CUDA bloat, keeping container small & memory-light)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install Core & Maritime Intelligence Dependencies
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    pydantic-settings \
    pyyaml \
    numpy \
    pandas \
    scipy \
    scikit-learn \
    shapely \
    requests \
    httpx \
    rich \
    langgraph \
    langchain-core \
    geopandas \
    pyproj \
    opencv-python-headless \
    ultralytics \
    reportlab \
    matplotlib \
    python-multipart \
    huggingface_hub

# Copy repository source code and assets
COPY src/ /app/src/
COPY data/ /app/data/
COPY models/ /app/models/
COPY reports/ /app/reports/
COPY pyproject.toml /app/

# Copy compiled frontend SPA from Stage 1 into the location src/api/server.py expects
COPY --from=frontend-builder /app/web/dist /app/web/dist

# Expose port (default 8000)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT}/readyz || exit 1

# Launch Uvicorn dynamically binding to $PORT (compatible with Render, Railway, Fly.io, Heroku)
CMD ["sh", "-c", "python -m uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT}"]
