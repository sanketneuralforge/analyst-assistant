#!/usr/bin/env bash
# run.sh — start the API server + Streamlit UI together
set -e

PROJ_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ_ROOT"

cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$API_PID" 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# ── Clear any stale processes from a previous run ────────────────
for port in 8000 8501; do
    pid=$(lsof -ti tcp:$port 2>/dev/null) && {
        echo "  Clearing stale process on :$port (PID $pid)"
        kill -9 $pid 2>/dev/null || true
    }
done
sleep 0.5

echo "► Starting API server  (http://localhost:8000)"
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "  Waiting for API to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  API ready ✓"
        break
    fi
    sleep 0.5
done

echo "► Starting Streamlit   (http://localhost:8501)"
.venv/bin/streamlit run ui/app.py --server.port 8501

kill "$API_PID" 2>/dev/null || true
