#!/bin/bash
# Launch both the FastAPI API and Streamlit UI for development.
# Usage: ./scripts/run_dev.sh

set -e

echo "Starting Elicit development servers..."
echo ""

# Start FastAPI in background
echo "Starting API server on http://localhost:8000 ..."
uvicorn discovery_engine.api.main:app --reload --port 8000 &
API_PID=$!

# Give API a moment to start
sleep 2

# Start Streamlit
echo "Starting Streamlit UI on http://localhost:8501 ..."
streamlit run streamlit_app/app.py --server.port 8501 &
UI_PID=$!

echo ""
echo "Both servers running."
echo "  API:  http://localhost:8000/docs"
echo "  UI:   http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop both."

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    wait
    echo "Done."
}

trap cleanup EXIT INT TERM

# Wait for either process to exit
wait
