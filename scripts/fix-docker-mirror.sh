#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MIRRORS=(
  "https://docker.xuanyuan.me"
  "https://docker.1ms.run"
  "https://docker.m.daocloud.io"
)

BASE_IMAGES=(
  "redis:7-alpine"
  "mysql:8.0"
  "python:3.12-slim"
  "node:22-alpine"
  "nginx:stable-alpine"
)

PULL_IMAGES=1
FORCE_CONFIGURE=0

usage() {
    cat <<'EOF'
用法：sudo bash scripts/fix-docker-mirror.sh [选项]

一键配置 Docker Hub 国内镜像加速器，并预拉取 UniDjango 所需镜像。

选项：
  --no-pull      只配置镜像加速器，不拉取镜像
  --force        即使检测不到可用镜像站，也强制写入配置
  -h, --help     显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-pull)
            PULL_IMAGES=0
            shift
            ;;
        --force)
            FORCE_CONFIGURE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "未知参数：$1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "请使用 root 运行：sudo bash scripts/fix-docker-mirror.sh" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "未检测到 docker，请先运行：sudo bash scripts/setup-rocky.sh" >&2
    exit 1
fi

registry_reachable() {
    local mirror="$1"
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 "${mirror}/v2/" 2>/dev/null || true)"
    if [[ -n "$code" && "$code" != "000" ]]; then
        return 0
    fi
    return 1
}

selected_mirrors=()
if command -v curl >/dev/null 2>&1; then
    for mirror in "${MIRRORS[@]}"; do
        if registry_reachable "$mirror"; then
            selected_mirrors+=("$mirror")
            echo "✅ 镜像站可用：$mirror"
        else
            echo "⚠️  镜像站暂不可达：$mirror"
        fi
    done

    if [[ ${#selected_mirrors[@]} -eq 0 && "$FORCE_CONFIGURE" -ne 1 ]]; then
        echo "未检测到可用镜像站，服务器对外网 HTTPS 访问可能被限制。" >&2
        echo "请先联系网络管理员开放外网，或配置 Docker HTTP/HTTPS 代理后重试。" >&2
        echo "若仍要写入这些镜像地址，可加 --force。" >&2
        exit 1
    fi
fi

if [[ ${#selected_mirrors[@]} -eq 0 ]]; then
    selected_mirrors=("${MIRRORS[@]}")
fi

mkdir -p /etc/docker
backup="/etc/docker/daemon.json.bak.$(date +%Y%m%d%H%M%S)"
if [[ -f /etc/docker/daemon.json ]]; then
    cp -a /etc/docker/daemon.json "$backup"
    echo "已备份原配置到 $backup"
fi

if command -v python3 >/dev/null 2>&1; then
    export DOCKER_MIRRORS_JSON
    DOCKER_MIRRORS_JSON="$(printf '%s\n' "${selected_mirrors[@]}" | python3 -c 'import sys,json; print(json.dumps([x for x in (line.strip() for line in sys.stdin) if x]))')"
    python3 - <<'PY'
import json
import os

path = "/etc/docker/daemon.json"
mirrors = json.loads(os.environ["DOCKER_MIRRORS_JSON"])
config = {}

if os.path.exists(path) and os.path.getsize(path) > 0:
    try:
        config = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"/etc/docker/daemon.json 不是有效 JSON，请先检查备份文件：{exc}") from exc

config.setdefault("registry-mirrors", [])
for mirror in mirrors:
    if mirror not in config["registry-mirrors"]:
        config["registry-mirrors"].append(mirror)

with open(path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
PY
else
    if [[ -f /etc/docker/daemon.json ]]; then
        echo "未找到 python3，且已有 /etc/docker/daemon.json，无法安全合并配置。" >&2
        echo "请手动编辑该文件并加入 registry-mirrors。" >&2
        exit 1
    fi

    {
        echo '{'
        echo '  "registry-mirrors": ['
        for i in "${!selected_mirrors[@]}"; do
            if [[ $i -lt $((${#selected_mirrors[@]} - 1)) ]]; then
                echo "    \"${selected_mirrors[$i]}\","
            else
                echo "    \"${selected_mirrors[$i]}\""
            fi
        done
        echo '  ]'
        echo '}'
    } > /etc/docker/daemon.json
fi

systemctl daemon-reload
systemctl restart docker

echo
echo "当前 Docker 镜像加速配置："
docker info | grep -A5 "Registry Mirrors" || true

if [[ "$PULL_IMAGES" -eq 1 ]]; then
    echo
    echo "开始预拉取 UniDjango 所需镜像..."
    for image in "${BASE_IMAGES[@]}"; do
        echo "==> docker pull ${image}"
        docker pull "$image"
    done
    echo
    echo "✅ 镜像加速配置完成，所需镜像已预拉取。"
else
    echo
    echo "✅ 镜像加速配置完成。"
fi

echo
echo "现在可以重新运行 bootstrap，例如："
echo "  ./scripts/bootstrap.sh dev --password '你的密码'"
