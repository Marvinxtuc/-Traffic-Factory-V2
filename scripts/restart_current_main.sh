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
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  echo "未找到可用 Python，请先准备 Python 3.11+ 或激活虚拟环境。" >&2
  exit 1
}

ensure_valid_port() {
  local port="$1"
  if [[ ! "$port" =~ ^[0-9]+$ ]]; then
    echo "TF_PORT/--port 需要是数字，当前为: ${port}" >&2
    exit 1
  fi
  if (( port < 1 || port > 65535 )); then
    echo "TF_PORT/--port 超出有效范围（1-65535），当前为: ${port}" >&2
    exit 1
  fi
}

report_port_conflict() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local listeners
    listeners="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$listeners" ]]; then
      echo "检测到以下监听进程占用了端口 ${port}:" >&2
      echo "$listeners" >&2
      return 0
    fi
  fi
  echo "端口 ${port} 已被占用，但当前环境未拿到更详细的监听进程信息。" >&2
}

ensure_port_available() {
  local host="$1"
  local port="$2"
  local status
  if ! status="$("$PYTHON_BIN" - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        print(exc.errno or -1)
        raise SystemExit(1)
    print(0)
PY
)"; then
    :
  fi

  if [[ "$status" == "0" ]]; then
    return 0
  fi

  if [[ "$status" == "98" || "$status" == "48" ]]; then
    echo "启动前检查失败：${HOST}:${PORT} 已被占用。" >&2
    report_port_conflict "$PORT"
    echo "可改用 TF_PORT=8788 bash scripts/restart_current_main.sh 之类的方式切换端口。" >&2
    exit 1
  fi

  if [[ "$status" == "49" ]]; then
    echo "启动前检查失败：本机不存在可绑定地址 ${HOST}，请检查 TF_HOST。" >&2
    exit 1
  fi

  echo "启动前端口检查失败：${HOST}:${PORT} 无法绑定（errno=${status}）。" >&2
  exit 1
}

PYTHON_BIN="$(pick_python)"

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"当前解释器为 Python {sys.version.split()[0]}，需要 Python 3.11+。请改用 .venv/bin/python、python3.11 或设置 TF_PYTHON。")
print(f"使用解释器: Python {sys.version.split()[0]}")
PY

HOST="${TF_HOST:-127.0.0.1}"
PORT="${TF_PORT:-8787}"
DB_PATH="${TF_DB_PATH:-data/runtime/traffic_factory.sqlite3}"

ensure_valid_port "$PORT"
ensure_port_available "$HOST" "$PORT"
mkdir -p "$(dirname "$DB_PATH")"

if ! "$PYTHON_BIN" -c 'import app.main' >/dev/null 2>&1; then
  echo "app.main 导入失败，请先确认依赖已安装且当前仓库可正常导入。" >&2
  exit 1
fi

echo "[1/2] 初始化数据库: ${DB_PATH}"
"$PYTHON_BIN" scripts/init_db.py --db-path "$DB_PATH"

echo "[2/2] 启动当前主线 app.main: http://${HOST}:${PORT}"
exec env PYTHONUNBUFFERED=1 "$PYTHON_BIN" -m app.main --host "$HOST" --port "$PORT" --db-path "$DB_PATH"
