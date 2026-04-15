#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

pick_python() {
  if [[ -n "${TF_PYTHON:-}" ]]; then
    printf '%s\n' "$TF_PYTHON"
    return 0
  fi
  if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    printf '%s\n' "${VIRTUAL_ENV}/bin/python"
    return 0
  fi
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  echo "未找到可用 Python 解释器。" >&2
  exit 1
}

wait_for_healthz() {
  local base_url="$1"
  local attempts=60
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "${base_url}/healthz" >/dev/null 2>&1; then
      return 0
    fi
    if [[ -n "${SERVER_PID:-}" ]] && ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
      return 1
    fi
    sleep 0.5
  done
  return 1
}

ensure_allow_dirty_supported() {
  local help_text
  help_text="$("$PYTHON_BIN" scripts/release_check.py --help 2>&1 || true)"
  if [[ "$help_text" != *"--allow-dirty"* ]]; then
    echo "当前 scripts/release_check.py 未支持 --allow-dirty。请先合入 Worker-A 的 release_check 改动。" >&2
    exit 2
  fi
}

ALLOW_DIRTY_REASON=""
SKIP_TESTS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-dirty-reason)
      ALLOW_DIRTY_REASON="${2:-}"
      shift 2
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift 1
      ;;
    *)
      echo "未知参数: $1" >&2
      echo "用法: bash scripts/release_rehearsal.sh [--allow-dirty-reason <reason>] [--skip-tests]" >&2
      exit 2
      ;;
  esac
done

PYTHON_BIN="$(pick_python)"

HOST="${TF_HOST:-127.0.0.1}"
PORT="${TF_PORT:-8787}"
DB_PATH="${TF_DB_PATH:-data/runtime/traffic_factory_qa.sqlite3}"
LOG_LEVEL="${TF_LOG_LEVEL:-INFO}"
ACCESS_LOG="${TF_ACCESS_LOG:-true}"
BASE_URL="http://${HOST}:${PORT}"
STARTUP_LOG="${TF_STARTUP_LOG:-logs/release-rehearsal.log}"

mkdir -p "$(dirname "$DB_PATH")" "$(dirname "$STARTUP_LOG")" runtime

TMP_ENV_FILE="$(mktemp "$ROOT_DIR/runtime/release_rehearsal_env.XXXXXX")"
SERVER_PID=""

cleanup() {
  rm -f "$TMP_ENV_FILE"
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

cat >"$TMP_ENV_FILE" <<EOF
TF_HOST=${HOST}
TF_PORT=${PORT}
TF_DB_PATH=${DB_PATH}
TF_LOG_LEVEL=${LOG_LEVEL}
TF_ACCESS_LOG=${ACCESS_LOG}
EOF

echo "[1/3] 启动 current-main 实例: ${BASE_URL}"
TF_HOST="$HOST" TF_PORT="$PORT" TF_DB_PATH="$DB_PATH" TF_LOG_LEVEL="$LOG_LEVEL" TF_ACCESS_LOG="$ACCESS_LOG" \
  bash scripts/restart_current_main.sh >"$STARTUP_LOG" 2>&1 &
SERVER_PID=$!

if ! wait_for_healthz "$BASE_URL"; then
  echo "实例启动失败或健康检查超时，请查看日志: $STARTUP_LOG" >&2
  exit 1
fi

echo "[2/3] 运行 smoke: ${BASE_URL}"
"$PYTHON_BIN" scripts/current_main_smoke_test.py --base-url "$BASE_URL"

echo "[3/3] 运行 release_check"
release_cmd=("$PYTHON_BIN" scripts/release_check.py --env-file "$TMP_ENV_FILE" --base-url "$BASE_URL" --startup-log "$STARTUP_LOG")
if [[ "$SKIP_TESTS" == "1" ]]; then
  release_cmd+=(--skip-tests)
fi
if [[ -n "$ALLOW_DIRTY_REASON" ]]; then
  ensure_allow_dirty_supported
  release_cmd+=(--allow-dirty --allow-dirty-reason "$ALLOW_DIRTY_REASON")
fi
"${release_cmd[@]}"

echo "rehearsal 完成。模式: $( [[ -n "$ALLOW_DIRTY_REASON" ]] && echo "debug_allow_dirty" || echo "strict" )"
