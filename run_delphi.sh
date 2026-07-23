#!/usr/bin/env bash
#
# run_delphi.sh — start the whole Delphi system end-to-end.
#
#   ./run_delphi.sh            start all three processes (frontend + 2 APIs)
#   ./run_delphi.sh --setup    create both virtualenvs and install deps (run once)
#   ./run_delphi.sh --help     show this help
#
# The three processes:
#   1. Static frontend           http://localhost:8100/     (system python3 http.server)
#   2. Hypothesis Agent API       http://127.0.0.1:8200      (hypothesis_agent/.venv)
#   3. Investigation Pipeline API http://127.0.0.1:8300      (insight_pipeline/.venv)
#
# Logs stream to .run_logs/. Press Ctrl+C to stop everything cleanly.
#
# Each venv's python binary is invoked directly (no `source activate`), and the
# repo root is derived from this script's own location, so the literal `?` in
# the `Delphie?` folder name is never an issue.

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HYP_VENV="$REPO_ROOT/hypothesis_agent/.venv"
INS_VENV="$REPO_ROOT/insight_pipeline/.venv"
LOG_DIR="$REPO_ROOT/.run_logs"

# Ports (override via environment, e.g. FRONTEND_PORT=9100 ./run_delphi.sh).
# The two API ports are also exported so the servers themselves bind to them.
FRONTEND_PORT="${FRONTEND_PORT:-8100}"
HYP_PORT="${HYPOTHESIS_AGENT_SERVER_PORT:-8200}"
INS_PORT="${INSIGHT_PIPELINE_SERVER_PORT:-8300}"
export HYPOTHESIS_AGENT_SERVER_PORT="$HYP_PORT"
export INSIGHT_PIPELINE_SERVER_PORT="$INS_PORT"

# ---------------------------------------------------------------------------

usage() {
  sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

port_busy() { lsof -ti:"$1" >/dev/null 2>&1; }

wait_for() {  # url, human-name
  local url="$1" name="$2" tries=0
  until curl -sf "$url" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "$tries" -gt 90 ]; then
      echo "  ! $name did not become healthy in ~90s — check its log in $LOG_DIR"
      return 1
    fi
    sleep 1
  done
  echo "  ✓ $name is up"
}

do_setup() {
  echo "==> Setting up hypothesis_agent virtualenv"
  python3 -m venv "$HYP_VENV"
  "$HYP_VENV/bin/pip" install --upgrade pip >/dev/null
  "$HYP_VENV/bin/pip" install -e "$REPO_ROOT/hypothesis_agent[server,llm-litellm,sample-data,observability]"
  if [ ! -f "$REPO_ROOT/hypothesis_agent/.env" ]; then
    cp "$REPO_ROOT/hypothesis_agent/.env.example" "$REPO_ROOT/hypothesis_agent/.env"
    echo "    created hypothesis_agent/.env — add your LITELLM_API_KEY to it"
  fi

  echo "==> Setting up insight_pipeline virtualenv"
  python3 -m venv "$INS_VENV"
  "$INS_VENV/bin/pip" install --upgrade pip >/dev/null
  "$INS_VENV/bin/pip" install -e "$REPO_ROOT/hypothesis_agent[llm-litellm,observability]"
  "$INS_VENV/bin/pip" install -e "$REPO_ROOT/insight_pipeline[dev,analytics,plotting,data-excel,server]"

  echo
  echo "Setup complete. Add LITELLM_API_KEY to hypothesis_agent/.env, then run:"
  echo "  ./run_delphi.sh"
}

# ---------------------------------------------------------------------------

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  --setup)   do_setup; exit 0 ;;
  "")        ;;  # normal run
  *) echo "Unknown option: $1"; echo; usage; exit 1 ;;
esac

# Preflight -----------------------------------------------------------------

if [ ! -x "$HYP_VENV/bin/python" ] || [ ! -x "$INS_VENV/bin/python" ]; then
  echo "Virtualenvs not found. Run the one-time setup first:"
  echo "  ./run_delphi.sh --setup"
  exit 1
fi

if ! grep -Eq '^LITELLM_API_KEY=.+' "$REPO_ROOT/hypothesis_agent/.env" 2>/dev/null; then
  echo "  ! Warning: LITELLM_API_KEY is empty (or .env missing) in hypothesis_agent/.env."
  echo "    The servers will start, but generating a hypothesis will fail with a 500"
  echo "    until you add a key. (Offline demos/tests are unaffected.)"
  echo
fi

mkdir -p "$LOG_DIR"
cd "$REPO_ROOT"

PIDS=()
_CLEANED=0
cleanup() {
  [ "$_CLEANED" -eq 1 ] && return     # INT then EXIT both fire — run once
  _CLEANED=1
  [ "${#PIDS[@]}" -eq 0 ] && return   # nothing this script started
  echo
  echo "==> Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "    stopped."
}
trap cleanup INT TERM EXIT

start() {  # port, human-name, log-file, command...
  local port="$1" name="$2" log="$3"; shift 3
  if port_busy "$port"; then
    echo "==> $name: port $port already in use — assuming it's already running, skipping."
    return 0
  fi
  echo "==> Starting $name (port $port) — logging to ${log#$REPO_ROOT/}"
  ( cd "$REPO_ROOT" && exec "$@" ) >"$log" 2>&1 &
  PIDS+=($!)
}

echo "Delphi — starting all processes. Press Ctrl+C to stop."
echo

start "$FRONTEND_PORT" "Static frontend"          "$LOG_DIR/frontend.log" \
      python3 -m http.server "$FRONTEND_PORT"
start "$HYP_PORT"      "Hypothesis Agent API"       "$LOG_DIR/hypothesis_agent.log" \
      "$HYP_VENV/bin/python" -m hypothesis_agent.server
start "$INS_PORT"      "Investigation Pipeline API" "$LOG_DIR/insight_pipeline.log" \
      "$INS_VENV/bin/python" -m insight_pipeline.server

echo
echo "==> Waiting for services to become healthy..."
wait_for "http://127.0.0.1:$FRONTEND_PORT/"           "Static frontend"           || true
wait_for "http://127.0.0.1:$HYP_PORT/api/health"      "Hypothesis Agent API"      || true
wait_for "http://127.0.0.1:$INS_PORT/api/health"      "Investigation Pipeline API" || true

cat <<EOF

────────────────────────────────────────────────────────────
  Delphi is running:

    Frontend           http://localhost:$FRONTEND_PORT/
    Hypothesis Agent   http://127.0.0.1:$HYP_PORT/api/health
    Investigation API  http://127.0.0.1:$INS_PORT/api/health

  Open the frontend and click "+ Generate hypothesis".
EOF

if [ "${#PIDS[@]}" -eq 0 ]; then
  cat <<EOF
  (Every service was already running — this launcher started nothing and will
   now exit; the existing processes keep running.)
────────────────────────────────────────────────────────────
EOF
  exit 0
fi

cat <<EOF
  Logs: $LOG_DIR/
  Press Ctrl+C here to stop everything this launcher started.
────────────────────────────────────────────────────────────
EOF

# Keep the script in the foreground so Ctrl+C reaches the trap.
wait
