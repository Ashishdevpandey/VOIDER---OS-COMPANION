# ============================================================
# VOIDER — AI OS Companion
# Multi-stage Dockerfile for lean, production-ready images
# ============================================================

# ─── Stage 1: Builder ───────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# System build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install deps first (separate layer for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ───────────────────────────────────────
FROM python:3.10-slim AS runtime

LABEL maintainer="Ashish Dev Pandey <ashisdvpandey@gmail.com>"
LABEL org.opencontainers.image.title="VOIDER AI OS"
LABEL org.opencontainers.image.description="Privacy-focused intelligent OS companion with RAG & multi-provider LLM support"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.url="https://github.com/Ashishdevpandey/VOIDER---OS-COMPANION"

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd -m -u 1000 voider && \
    mkdir -p /app/data/vector_store /app/logs /app/config && \
    chown -R voider:voider /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY --chown=voider:voider backend/ ./backend/
COPY --chown=voider:voider ui/     ./ui/
COPY --chown=voider:voider config/ ./config/
COPY --chown=voider:voider requirements.txt .

# ─── Environment defaults ───────────────────────────────────
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV AIOS_HOST=0.0.0.0
ENV AIOS_PORT=8000

# LLM Provider — override with docker-compose env or -e flags
# Options: ollama | groq | openai | gemini | xai
ENV VOIDER_PROVIDER=ollama
ENV VOIDER_OLLAMA_HOST=http://ollama:11434
ENV VOIDER_MODEL=""
ENV VOIDER_API_KEY=""

# ─── Entrypoint ─────────────────────────────────────────────
COPY --chown=voider:voider docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER voider

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -sf http://localhost:8000/health | grep -q '"status"' || exit 1

ENTRYPOINT ["/entrypoint.sh"]
