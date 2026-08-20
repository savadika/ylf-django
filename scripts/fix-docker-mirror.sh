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
PULL_TIMEOUT=300
PULL_KILL_AFTER=15

usage() {
    cat <<'EOF'
用法：sudo bash scripts/fix-docker-mirror.sh [选项]

一键配置 Docker Hub 国内镜像加速器，并预拉取 UniDjango 所需镜像。

选项：
  --no-pull      只配置镜像加速器，不拉取镜像
  --force        即使检测不到可用镜像站，也强制写入配置
  --timeout 秒   单个镜像源拉取超时，默认 300 秒
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
        --timeout)
            if [[ -z "${2:-}" || ! "$2" =~ ^[0-9]+$ ]]; then
                echo "--timeout 需要正整数秒数" >&2
                exit 1
            fi
            PULL_TIMEOUT="$2"
            shift 2
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

registry_probe() {
    local mirror="$1"
    local result
    result="$(curl -sS -o /dev/null -w '%{http_code} %{time_total}' --max-time 8 "${mirror}/v2/" 2>/dev/null || true)"
    printf '%s\n' "$result"
}

selected_mirrors=()
if command -v curl >/dev/null 2>&1; then
    mirror_probe_results=()
    for mirror in "${MIRRORS[@]}"; do
        probe="$(registry_probe "$mirror")"
        code="${probe%% *}"
        elapsed="${probe##* }"
        if [[ -n "$code" && "$code" != "000" ]]; then
            mirror_probe_results+=("${elapsed}|${mirror}")
            echo "✅ 镜像站可用：$mirror（${elapsed}s）"
        else
            echo "⚠️  镜像站暂不可达：$mirror"
        fi
    done

    if [[ ${#mirror_probe_results[@]} -gt 0 ]]; then
        while IFS='|' read -r _ mirror; do
            [[ -z "$mirror" ]] && continue
            selected_mirrors+=("$mirror")
        done < <(printf '%s\n' "${mirror_probe_results[@]}" | sort -g -t'|' -k1,1)
    fi

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

run_pull_with_timeout() {
    if command -v timeout >/dev/null 2>&1; then
        timeout --kill-after="$PULL_KILL_AFTER" "$PULL_TIMEOUT" "$@"
    else
        "$@"
    fi
}

pull_image_with_fallback() {
    local image="$1"
    local mirror host ref

    for mirror in "${selected_mirrors[@]}"; do
        host="${mirror#https://}"
        if [[ "$image" == */* ]]; then
            ref="${host}/${image}"
        else
            ref="${host}/library/${image}"
        fi

        echo "==> docker pull ${ref}（镜像源：${mirror}，超时：${PULL_TIMEOUT}s）"
        if run_pull_with_timeout docker pull "$ref"; then
            if [[ "$ref" != "$image" ]]; then
                docker tag "$ref" "$image"
                docker rmi "$ref" >/dev/null 2>&1 || true
            fi
            echo "✅ ${image} 已通过 ${mirror} 拉取完成"
            return 0
        fi

        echo "⚠️  ${mirror} 拉取 ${image} 超时或失败，尝试下一个镜像源。"
    done

    echo "==> docker pull ${image}（Docker 默认源兜底）"
    run_pull_with_timeout docker pull "$image"
}

if [[ "$PULL_IMAGES" -eq 1 ]]; then
    echo
    echo "开始预拉取 UniDjango 所需镜像..."
    failed_images=()
    for image in "${BASE_IMAGES[@]}"; do
        if ! pull_image_with_fallback "$image"; then
            failed_images+=("$image")
            echo "❌ ${image} 在所有镜像源均未拉取成功。" >&2
        fi
    done

    if [[ ${#failed_images[@]} -eq 0 ]]; then
        echo
        echo "✅ 镜像加速配置完成，所需镜像已预拉取。"
    else
        echo
        echo "❌ 部分镜像未拉取成功：${failed_images[*]}" >&2
        echo "可稍后重试，或运行：sudo bash scripts/fix-docker-mirror.sh --no-pull" >&2
        exit 1
    fi
else
    echo
    echo "✅ 镜像加速配置完成。"
fi

echo
echo "现在可以重新运行 bootstrap，例如："
echo "  ./scripts/bootstrap.sh dev --password '你的密码'"
