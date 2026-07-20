#!/usr/bin/env bash
# Create a new Railway service instance and deploy TinyModel HSP sidecar.
# Run from repo root in an INTERACTIVE terminal (railway login needs a browser).
#
# Usage:
#   bash deploy/railway/deploy-new-instance.sh
#   SERVICE_NAME=MySidecar bash deploy/railway/deploy-new-instance.sh
#
# Optional: non-interactive CI deploy with a project token:
#   export RAILWAY_TOKEN="your-project-token"
#   bash deploy/railway/deploy-new-instance.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SERVICE_NAME="${SERVICE_NAME:-TinyModel-sidecar-$(date +%Y%m%d)}"
HSP_PROJECT_ID="${HSP_PROJECT_ID:-357753f3-3481-4559-af22-32c41cf7293e}"
RAILWAY_ENV="${RAILWAY_ENV:-production}"

echo "==> TinyModel Railway deploy (new service: ${SERVICE_NAME})"

if ! command -v railway >/dev/null 2>&1; then
  echo "Install Railway CLI: npm i -g @railway/cli"
  exit 1
fi

if ! railway whoami >/dev/null 2>&1; then
  if [[ -n "${RAILWAY_TOKEN:-}" ]]; then
    echo "Using RAILWAY_TOKEN from environment."
  else
    echo "Not logged in. Opening Railway login (complete in browser)..."
    railway login
  fi
fi

echo "==> Linking project HSP (${HSP_PROJECT_ID}), env ${RAILWAY_ENV} (no service yet)"
railway link -p "$HSP_PROJECT_ID" -e "$RAILWAY_ENV" 2>/dev/null || railway link -p "$HSP_PROJECT_ID" -e "$RAILWAY_ENV"

echo "==> Creating service: ${SERVICE_NAME} (non-interactive)"
# MSYS_NO_PATHCONV prevents Git Bash from rewriting /app/... to C:/Program Files/Git/app/...
MSYS_NO_PATHCONV=1 railway add --service "$SERVICE_NAME" \
  --variables "TINYMODEL_PATH=HyperlinksSpace/TinyModel1" \
  --variables "TINYMODEL_HSP_CORPUS=/app/texts/hsp_program_corpus.md" \
  --variables "HOST=0.0.0.0"

echo "==> Linking cwd to service ${SERVICE_NAME}"
railway service "$SERVICE_NAME"

echo "==> Ensuring variables (idempotent)"
MSYS_NO_PATHCONV=1 railway variables \
  --set "TINYMODEL_PATH=HyperlinksSpace/TinyModel1" \
  --set "TINYMODEL_HSP_CORPUS=/app/texts/hsp_program_corpus.md" \
  --set "HOST=0.0.0.0"

if [[ -n "${HF_TOKEN:-}" ]]; then
  railway variables --set "HF_TOKEN=${HF_TOKEN}"
  echo "    (HF_TOKEN set from environment)"
else
  echo "    Tip: export HF_TOKEN=hf_... before running for faster Hub downloads"
fi

echo "==> Deploying Docker sidecar (railway up --detach)"
railway up --detach

echo ""
echo "==> Deploy started. Watch logs:"
echo "    railway logs --service ${SERVICE_NAME}"
echo ""
echo "==> After healthy, generate public URL:"
echo "    railway domain --service ${SERVICE_NAME}"
echo ""
echo "==> Verify (replace BASE_URL with your Railway or custom domain):"
echo "    python scripts/hsp_railway_deploy_smoke.py --verify --base-url https://YOUR-DOMAIN"
echo ""
railway status
