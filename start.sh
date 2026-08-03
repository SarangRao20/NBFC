#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR"
FRONTEND_DIR="$ROOT_DIR/frontend"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# ── Backend (prefix logs with [backend]) ──
cd "$BACKEND_DIR"
./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | sed 's/^/[backend] /' &
BACKEND_PID=$!

# ── Frontend (prefix logs with [frontend]) ──
cd "$FRONTEND_DIR"
npx vite --host 0.0.0.0 --port 5173 2>&1 | sed 's/^/[frontend] /' &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
echo "========================================="
echo ""

wait
