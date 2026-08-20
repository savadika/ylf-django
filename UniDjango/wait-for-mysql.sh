#!/bin/sh

DB_HOST="${DB_HOST:-}"
DB_PORT="${MYSQL_INTERNAL_PORT:-3306}"
DB_USER="root"
DB_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
DB_NAME="${MYSQL_DATABASE:-}"

if [ -z "$DB_HOST" ]; then
  echo "Error: DB_HOST environment variable is not set." >&2
  exit 1
fi

echo "Waiting for MySQL at ${DB_HOST}:${DB_PORT}..."

# 优先用 PyMySQL 做真实连接检查，避免“端口已监听但 MySQL 还不能认证”的竞态。
if command -v python >/dev/null 2>&1 && python -c 'import pymysql' >/dev/null 2>&1; then
  until python - "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASSWORD" "$DB_NAME" <<'PY'
import sys

import pymysql

host, port, user, password, database = sys.argv[1:]
try:
    port = int(port)
except ValueError:
    port = 3306

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database or None,
        connect_timeout=3,
    )
except Exception as exc:  # noqa: BLE001 - 等待阶段需要吞掉所有连接异常
    print(f"MySQL is unavailable - sleeping: {exc}", flush=True)
    sys.exit(1)
else:
    conn.close()
PY
  do
    sleep 1
  done
elif command -v nc >/dev/null 2>&1; then
  # 没有 Python/PyMySQL 时退化为端口检查。
  while ! nc -z "$DB_HOST" "$DB_PORT"; do
    echo "MySQL is unavailable - sleeping"
    sleep 1
  done
else
  echo "Error: neither Python/PyMySQL nor nc is available." >&2
  exit 1
fi

echo "MySQL is ready"

# 执行原来的命令
exec "$@"
