# TinyModel Phase 3 reference API — HSP encoder sidecar (Railway / Fly / Cloud Run).
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    TINYMODEL_PATH=HyperlinksSpace/TinyModel1 \
    TINYMODEL_HSP_CORPUS=/app/texts/hsp_program_corpus.md \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-railway.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements-railway.txt

COPY scripts/ /app/scripts/
COPY texts/hsp_program_corpus.md /app/texts/hsp_program_corpus.md
RUN test -s /app/texts/hsp_program_corpus.md

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=5 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8765}/healthz" || exit 1'

CMD ["python", "scripts/phase3_reference_server.py", "--host", "0.0.0.0"]
