#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MODE="prod"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
COMMON_PASSWORD="${BOOTSTRAP_PASSWORD:-}"
BOOTSTRAP_HOST_IP="${BOOTSTRAP_HOST_IP:-}"

usage() {
    cat <<'EOF'
用法：./scripts/bootstrap.sh [prod|dev] [选项]

从全新 clone 开始准备环境并启动 UniDjango：
  - 没有 .env 时自动从 .env.example 创建
  - 自动生成缺失的 Django/JWT 密钥
  - MySQL、Redis 和 admin 使用同一个密码
  - 构建并启动生产或开发环境
  - 等待后端就绪后初始化 admin 账号

选项：
  --admin-username <name>      管理员用户名，默认 admin
  --password <password>        MySQL、Redis 和 admin 的共用密码；不传则交互输入
  --admin-email <email>        管理员邮箱，默认 admin@example.com
  --host-ip <ip>               手动指定服务器访问 IP；不传则自动识别
  -h, --help                   显示帮助

示例：
  ./scripts/bootstrap.sh prod
  ./scripts/bootstrap.sh dev --password 'MyStrongPass123'
  ./scripts/bootstrap.sh prod --host-ip 172.16.100.55
EOF
}

for arg in "$@"; do
    case "$arg" in
        prod|dev)
            MODE="$arg"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
    esac
done

while [[ $# -gt 0 ]]; do
    case "$1" in
        --admin-username)
            ADMIN_USERNAME="${2:-}"
            shift 2
            ;;
        --admin-password)
            COMMON_PASSWORD="${2:-}"
            shift 2
            ;;
        --password)
            COMMON_PASSWORD="${2:-}"
            shift 2
            ;;
        --admin-email)
            ADMIN_EMAIL="${2:-}"
            shift 2
            ;;
        --host-ip)
            BOOTSTRAP_HOST_IP="${2:-}"
            shift 2
            ;;
        prod|dev|-h|--help)
            shift
            ;;
        *)
            echo "未知参数：$1" >&2
            usage
            exit 1
            ;;
    esac
done

random_hex() {
    local bytes="${1:-32}"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex "$bytes"
    else
        od -An -N "$bytes" -tx1 /dev/urandom | tr -d ' \n'
    fi
}

is_valid_ipv4() {
    [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

detect_server_ip() {
    local detected=""

    # 优先通过默认路由推导本机对外使用的源 IP，
    # 这样能自动避开 docker0、br-*、veth* 等容器网桥地址。
    if command -v ip >/dev/null 2>&1; then
        detected="$(
            ip -4 route get 1.1.1.1 2>/dev/null |
                awk '{for (i = 1; i <= NF; i++) if ($i == "src") {print $(i + 1); exit}}'
        )"
    fi

    # 回退方案一：扫描 scope global 的非回环 IPv4，并过滤容器网络接口。
    if [[ -z "$detected" ]] && command -v ip >/dev/null 2>&1; then
        detected="$(
            ip -4 -o addr show scope global 2>/dev/null |
                awk '$2 !~ /^(lo|docker[0-9]*|br-[0-9a-f]+|veth[0-9a-f]+|virbr[0-9]*|cni[0-9]*|flannel[0-9.]*|cali[0-9a-f]+)$/ {print $4; exit}' |
                cut -d/ -f1
        )"
    fi

    # 回退方案二：某些精简系统没有 iproute2，但仍有 hostname。
    if [[ -z "$detected" ]] && command -v hostname >/dev/null 2>&1; then
        detected="$(
            hostname -I 2>/dev/null |
                tr ' ' '\n' |
                awk '$0 !~ /^127\./ && $0 !~ /^(172\.(1[6-9]|2[0-9]|3[0-1])\.0\.1)$/ {print; exit}'
        )"
    fi

    if is_valid_ipv4 "$detected" && [[ "$detected" != "127.0.0.1" ]]; then
        printf '%s\n' "$detected"
    else
        printf ''
    fi
}

get_env_value() {
    local file="$1"
    local key="$2"
    grep -E "^${key}=" "$file" 2>/dev/null | tail -1 | cut -d= -f2-
}

set_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"
    local escaped_value
    escaped_value="$(printf '%s' "$value" | sed 's/[\\&|]/\\&/g')"

    if grep -qE "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${escaped_value}|" "$file"
    else
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

ensure_secret_key() {
    local key="$1"
    local current
    current="$(get_env_value .env "$key")"

    if [[ -z "$current" || "$current" == "change-me" ]]; then
        set_env_value .env "$key" "$(random_hex 32)"
        echo "已生成 $key"
    fi
}

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "已创建 .env"
fi

SERVER_IP="${BOOTSTRAP_HOST_IP:-}"
if [[ -z "$SERVER_IP" ]]; then
    SERVER_IP="$(detect_server_ip)"
fi

if [[ -z "$SERVER_IP" ]]; then
    echo "无法自动识别服务器实际 IP，请使用 --host-ip 手动指定。" >&2
    echo "例如：./scripts/bootstrap.sh $MODE --host-ip 172.16.100.54" >&2
    exit 1
fi

if [[ "$SERVER_IP" != "127.0.0.1" ]] && ! is_valid_ipv4 "$SERVER_IP"; then
    echo "无效的服务器地址：${SERVER_IP}。--host-ip 需要是 IPv4 地址。" >&2
    exit 1
fi

set_env_value .env "SERVER_HOST" "$SERVER_IP"

current_allowed="$(get_env_value .env "DJANGO_ALLOWED_HOSTS")"
if ! printf '%s\n' "$current_allowed" | tr ',' '\n' | grep -qxF "$SERVER_IP"; then
    if [[ -n "$current_allowed" ]]; then
        set_env_value .env "DJANGO_ALLOWED_HOSTS" "${current_allowed},${SERVER_IP}"
    else
        set_env_value .env "DJANGO_ALLOWED_HOSTS" "localhost,127.0.0.1,${SERVER_IP}"
    fi
fi
echo "已设置服务器访问地址：${SERVER_IP}"

ensure_secret_key "DJANGO_SECRET_KEY"
ensure_secret_key "JWT_SECRET_KEY"

if [[ -z "$COMMON_PASSWORD" ]]; then
    read -r -s -p "请输入统一密码（MySQL、Redis、admin 共用）: " COMMON_PASSWORD
    printf '\n'
    read -r -s -p "请再次确认统一密码: " COMMON_PASSWORD_CONFIRM
    printf '\n'

    if [[ "$COMMON_PASSWORD" != "$COMMON_PASSWORD_CONFIRM" ]]; then
        echo "两次输入的密码不一致。" >&2
        exit 1
    fi
fi

if [[ ${#COMMON_PASSWORD} -lt 8 ]]; then
    echo "统一密码长度不能少于 8 位。" >&2
    exit 1
fi

set_env_value .env "MYSQL_ROOT_PASSWORD" "$COMMON_PASSWORD"
set_env_value .env "REDIS_PASSWORD" "$COMMON_PASSWORD"

chmod 600 .env

if [[ "$MODE" == "prod" ]]; then
    COMPOSE_FILE="docker-compose.yml"
    PORT_KEY="FRONTEND_PORT"
else
    COMPOSE_FILE="docker-compose-dev.yml"
    PORT_KEY="FRONTEND_DEV_PORT"
fi

FRONTEND_PORT="$(get_env_value .env "$PORT_KEY")"
FRONTEND_PORT="${FRONTEND_PORT:-9530}"

if [[ "$MODE" == "dev" ]]; then
    OTHER_COMPOSE_FILE="docker-compose.yml"
else
    OTHER_COMPOSE_FILE="docker-compose-dev.yml"
fi

echo "正在停止可能冲突的 ${OTHER_COMPOSE_FILE} 容器..."
docker compose -f "$OTHER_COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true

echo "正在构建并启动 ${MODE} 环境..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "等待后端就绪..."
backend_ready=0
for _ in $(seq 1 120); do
    if docker compose -f "$COMPOSE_FILE" ps -q backend >/dev/null 2>&1 &&
       docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py migrate --check \
           >/dev/null 2>&1; then
        backend_ready=1
        break
    fi
    sleep 2
done

if [[ "$backend_ready" -ne 1 ]]; then
    echo "后端未能在预期时间内就绪，请检查日志：docker compose -f $COMPOSE_FILE logs -f backend" >&2
    exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py init_admin \
    --username "$ADMIN_USERNAME" \
    --password "$COMMON_PASSWORD" \
    --email "$ADMIN_EMAIL"

cat <<EOF

✅ 启动完成

访问地址：http://${SERVER_IP}:${FRONTEND_PORT}
管理员账号：${ADMIN_USERNAME}
统一密码：${COMMON_PASSWORD}

MySQL、Redis 和 admin 均使用上述统一密码。请妥善保存。脚本已自动将检测到的服务器 IP 写入 .env 的 SERVER_HOST 和 DJANGO_ALLOWED_HOSTS。
EOF
