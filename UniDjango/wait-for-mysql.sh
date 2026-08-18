#!/bin/sh

DB_PORT="${MYSQL_INTERNAL_PORT:-3306}"

# 等待 MySQL 启动
echo "Waiting for MySQL at $DB_HOST:$DB_PORT..."
# 使用 nc (netcat) 检查端口
# 如果 $DB_HOST 是空的，nc 会报错
if [ -z "$DB_HOST" ]; then
  echo "Error: DB_HOST environment variable is not set."
  exit 1
fi

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  echo "MySQL is unavailable - sleeping"
  sleep 1
done

echo "MySQL started"

# 执行原来的命令
exec "$@"
