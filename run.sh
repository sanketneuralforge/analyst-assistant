#!/bin/bash

echo "Clearing ports..."
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :8501 | xargs kill -9 2>/dev/null
sleep 1

echo "Starting FastAPI on port 8000..."
cd "$(dirname "$0")"
uv run uvicorn api.main:app --port 8000 &
API_PID=$!
echo "FastAPI PID: $API_PID"

echo "Waiting for API..."
sleep 3

echo "Starting Streamlit on port 8501..."
uv run streamlit run ui/app.py --server.port 8501

# When Streamlit exits, kill FastAPI too
kill $API_PID 2>/dev/null
echo "Stopped."
