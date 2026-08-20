#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

# 按实际可用性和响应速度排序的 Docker Hub 镜像加速器。
# 脚本启动时会并行探测，再按延迟从快到慢重新排序。
MIRRORS=(
    "https://docker.1ms.run"
    "https://docker.m.daocloud.io"
    "https://docker.xuanyuan.me"
    "https://docker.sparkcr.cn"
    "https://docker.1panel.live"
)

# UniDjango 构建时需要的基础镜像。
# node:22 用于开发镜像，node:22-alpine/nginx 用于生产前端镜像。
DEFAULT_IMAGES=(
    "redis:7-alpine"
    "mysql:8.0"
    "python:3.12-slim"
    "node:22-alpine"
    "node:22"
    "nginx:stable-alpine"
)

PULL_IMAGES=1
FORCE_CONFIGURE=0
NO_RESTART=0
PULL_TIMEOUT=300
PULL_KILL_AFTER=10
PROBE_TIMEOUT=6
PULL_PARALLEL=2
PULL_RACE=2
ONLY_IMAGES=()
EXTRA_IMAGES=()
SERVER_HOST_IP="${SERVER_HOST_IP:-}"

usage() {
    cat <<'EOF'
用法：sudo bash scripts/fix-docker-mirror.sh [选项]

探测可用的 Docker Hub 国内镜像源，按响应速度排序后写入 /etc/docker/daemon.json，
并预拉取 UniDjango 构建所需的基础镜像。

选项：
  --no-pull        只配置镜像加速器，不拉取镜像
  --force          即使没有探测到可用镜像源，也强制写入配置
  --timeout 秒     单个镜像源拉取超时，默认 300 秒
  --parallel 数量   同时拉取的镜像数量，默认 2，范围 1-4
  --only "镜像..."  只拉取指定镜像，覆盖默认镜像列表
  --image 镜像     额外增加一个要拉取的镜像，可重复使用
  --host-ip IP     同时把该 IP 写入 .env 的 SERVER_HOST 和 DJANGO_ALLOWED_HOSTS
  --no-restart     只生成配置，不重启 Docker 服务
  -h, --help       显示帮助
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
        --no-restart)
            NO_RESTART=1
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
        --parallel)
            if [[ -z "${2:-}" || ! "$2" =~ ^[1-4]$ ]]; then
                echo "--parallel 需要 1-4 之间的整数" >&2
                exit 1
            fi
            PULL_PARALLEL="$2"
            shift 2
            ;;
        --only)
            if [[ -z "${2:-}" ]]; then
                echo "--only 后面需要镜像列表" >&2
                exit 1
            fi
            IFS=' ' read -r -a ONLY_IMAGES <<< "$2"
            shift 2
            ;;
        --image)
            if [[ -z "${2:-}" ]]; then
                echo "--image 后面需要镜像名称" >&2
                exit 1
            fi
            EXTRA_IMAGES+=("$2")
            shift 2
            ;;
        --host-ip)
            if [[ -z "${2:-}" ]]; then
                echo "--host-ip 后面需要 IP 地址" >&2
                exit 1
            fi
            SERVER_HOST_IP="$2"
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

if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon 当前不可用，请先启动 Docker 后再运行本脚本。" >&2
    exit 1
fi

probe_tmp="$(mktemp -d)"
trap 'rm -rf "$probe_tmp"' EXIT

get_env_value() {
    local file="$1"
    local key="$2"
    local value=""

    value="$(grep -E "^${key}=" "$file" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
    printf '%s\n' "$value"
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

detect_server_ip() {
    local detected=""

    if command -v ip >/dev/null 2>&1; then
        detected="$(
            ip -4 -o addr show scope global 2>/dev/null |
                awk '$2 !~ /^(docker[0-9]*|br-[0-9a-f]+|veth[0-9a-f]+|virbr[0-9]*)$/ {print $4; exit}' |
                cut -d/ -f1
        )"
    fi

    if [[ -z "$detected" ]] && command -v hostname >/dev/null 2>&1; then
        detected="$(hostname -I 2>/dev/null | awk '{print $1}')"
    fi

    printf '%s\n' "$detected"
}

probe_mirror() {
    local mirror="$1"
    local out="$2"
    local headers code manifest_code elapsed

    # 先探测 /v2/，并校验它真的带有 Docker Registry 的响应头。
    # 一些看似返回 200 的站点其实只是普通网页，不能当作镜像源。
    headers="$(curl -sS -D - -o /dev/null --max-time "$PROBE_TIMEOUT" "$mirror/v2/" 2>/dev/null || true)"
    if ! printf '%s\n' "$headers" | grep -qi 'docker-distribution-api-version:'; then
        : > "$out"
        return
    fi

    code="$(printf '%s\n' "$headers" | awk 'NR == 1 {print $2}')"
    case "$code" in
        200|301|302|401|403) ;;
        *)
            : > "$out"
            return
            ;;
    esac

    # 再用一个真实 manifest 探测后端是否可用。401/404 也是正常的：
    # 未认证时 401，仓库不存在时 404；但 502/503 说明代理后端已经坏了。
    manifest_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$PROBE_TIMEOUT" \
        -H 'Accept: application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.index.v1+json' \
        "$mirror/v2/library/alpine/manifests/3.20" 2>/dev/null || true)"
    case "$manifest_code" in
        200|401|404) ;;
        *)
            : > "$out"
            return
            ;;
    esac

    elapsed="$(curl -sS -o /dev/null -w '%{time_total}' --max-time "$PROBE_TIMEOUT" "$mirror/v2/" 2>/dev/null || true)"
    [[ -n "$elapsed" ]] && printf '%s %s\n' "$elapsed" "$mirror" > "$out"
}

selected_mirrors=()
if command -v curl >/dev/null 2>&1; then
    echo "正在并行探测镜像源..."
    for i in "${!MIRRORS[@]}"; do
        probe_mirror "${MIRRORS[$i]}" "$probe_tmp/$i" &
    done
    wait

    while read -r elapsed mirror; do
        [[ -n "$mirror" ]] && selected_mirrors+=("$mirror")
    done < <(for f in "$probe_tmp"/*; do
        cat "$f"
    done | sort -g -k1,1)

    if [[ ${#selected_mirrors[@]} -gt 0 ]]; then
        echo "✅ 按速度排序后的镜像源："
        for mirror in "${selected_mirrors[@]}"; do
            echo "   - $mirror"
        done
    else
        echo "⚠️  未探测到可用镜像源。"
    fi

    if [[ ${#selected_mirrors[@]} -eq 0 && "$FORCE_CONFIGURE" -ne 1 ]]; then
        echo "服务器对外网 HTTPS 访问可能被限制。" >&2
        echo "请先联系网络管理员开放外网，或配置 Docker HTTP/HTTPS 代理后重试。" >&2
        echo "若仍要写入默认镜像地址，可加 --force。" >&2
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
    export DOCKER_SELECTED_MIRRORS
    DOCKER_SELECTED_MIRRORS="$(printf '%s\n' "${selected_mirrors[@]}" | \
        python3 -c 'import sys,json; print(json.dumps([x.strip() for x in sys.stdin if x.strip()]))')"
    python3 - <<'PY'
import json
import os
from urllib.parse import urlparse

path = "/etc/docker/daemon.json"
selected = json.loads(os.environ["DOCKER_SELECTED_MIRRORS"])
config = {}

if os.path.exists(path) and os.path.getsize(path) > 0:
    try:
        config = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"/etc/docker/daemon.json 不是有效 JSON，请先检查备份文件：{exc}") from exc

existing = config.get("registry-mirrors", [])
selected_set = set(selected)
dead_hosts = {"dockerproxy.net", "dytt.online"}
merged = [mirror for mirror in selected]
for mirror in existing:
    try:
        host = urlparse(mirror).netloc.lower()
    except (TypeError, ValueError):
        host = ""
    if host in dead_hosts:
        continue
    if mirror not in selected_set:
        merged.append(mirror)
config["registry-mirrors"] = merged

# 提高并发层下载能力，这是大镜像“卡在 Pulling fs layer”时最有效的加速项之一。
for key, minimum in (
    ("max-concurrent-downloads", 10),
    ("max-concurrent-uploads", 5),
    ("max-download-attempts", 5),
):
    try:
        old = int(config.get(key, 0))
    except (TypeError, ValueError):
        old = 0
    config[key] = max(old, minimum)

with open(path, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
PY
else
    if [[ -f /etc/docker/daemon.json ]]; then
        echo "未找到 python3，且已有 /etc/docker/daemon.json，无法安全合并配置。" >&2
        echo "请安装 python3 后重试，或手动编辑该文件加入 registry-mirrors。" >&2
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
        echo '  ],'
        echo '  "max-concurrent-downloads": 10,'
        echo '  "max-concurrent-uploads": 5,'
        echo '  "max-download-attempts": 5'
        echo '}'
    } > /etc/docker/daemon.json
fi

if [[ "$NO_RESTART" -eq 0 ]]; then
    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload
        systemctl restart docker
    elif command -v service >/dev/null 2>&1; then
        service docker restart
    else
        echo "未找到 systemctl/service，请手动重启 Docker 使配置生效。" >&2
    fi
fi

echo
echo "当前 Docker 镜像加速配置："
docker info 2>/dev/null | grep -A8 "Registry Mirrors" || true

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
    local pids=()
    local race_dir
    local winner=""
    local remaining

    race_dir="$(mktemp -d)"

    # 让前几个镜像源并发拉取，任何一个成功就立即使用；
    # 避免“排第一的源接口很快、实际下载很慢”时把整张镜像卡死。
    local tried=0
    for mirror in "${selected_mirrors[@]}"; do
        ((tried += 1))
        host="${mirror#https://}"
        if [[ "$image" == */* ]]; then
            ref="${host}/${image}"
        else
            ref="${host}/library/${image}"
        fi

        echo "==> ${image}：并发尝试 ${mirror}（超时 ${PULL_TIMEOUT}s）"
        if command -v setsid >/dev/null 2>&1; then
            export PULL_TIMEOUT PULL_KILL_AFTER
            export -f run_pull_with_timeout
            (
                exec setsid bash -c '
                    if run_pull_with_timeout docker pull "$1" >/dev/null 2>&1; then
                        printf "%s\n" "$1" > "$2/winner"
                        exit 0
                    fi
                    exit 1
                ' _ "$ref" "$race_dir"
            ) &
        else
            (
                if run_pull_with_timeout docker pull "$ref" >/dev/null 2>&1; then
                    printf '%s\n' "$ref" > "$race_dir/winner"
                    exit 0
                fi
                exit 1
            ) &
        fi
        pids+=("$!")

        if (( tried >= PULL_RACE )); then
            break
        fi
    done

    remaining="${#pids[@]}"
    while (( remaining > 0 )); do
        if [[ -f "$race_dir/winner" ]]; then
            winner="$(cat "$race_dir/winner")"
            break
        fi

        wait -n || true
        remaining=$((remaining - 1))
    done

    if [[ -n "$winner" ]]; then
        if command -v setsid >/dev/null 2>&1; then
            for pid in "${pids[@]}"; do
                kill -- -"$pid" 2>/dev/null || true
            done
        else
            for pid in "${pids[@]}"; do
                kill "$pid" 2>/dev/null || true
            done
        fi
        wait "${pids[@]}" 2>/dev/null || true

        if [[ "$winner" != "$image" ]]; then
            docker tag "$winner" "$image"
            docker rmi "$winner" >/dev/null 2>&1 || true
        fi
        rm -rf "$race_dir"
        echo "✅ ${image} 已拉取完成"
        return 0
    fi

    wait "${pids[@]}" 2>/dev/null || true
    rm -rf "$race_dir"

    # 前几个源都没成功时，再按顺序尝试剩余源。
    for mirror in "${selected_mirrors[@]:$PULL_RACE}"; do
        host="${mirror#https://}"
        if [[ "$image" == */* ]]; then
            ref="${host}/${image}"
        else
            ref="${host}/library/${image}"
        fi

        echo "==> ${image}：尝试 ${mirror}（超时 ${PULL_TIMEOUT}s）"
        if run_pull_with_timeout docker pull "$ref"; then
            if [[ "$ref" != "$image" ]]; then
                docker tag "$ref" "$image"
                docker rmi "$ref" >/dev/null 2>&1 || true
            fi
            echo "✅ ${image} 已拉取完成"
            return 0
        fi

        echo "⚠️  ${mirror} 拉取 ${image} 失败或超时，尝试下一个镜像源。"
    done

    echo "==> ${image}：使用 Docker 默认源兜底"
    run_pull_with_timeout docker pull "$image"
}

if [[ "$PULL_IMAGES" -eq 1 ]]; then
    images=()
    if [[ ${#ONLY_IMAGES[@]} -gt 0 ]]; then
        images=("${ONLY_IMAGES[@]}")
    else
        images=("${DEFAULT_IMAGES[@]}")
    fi
    images+=("${EXTRA_IMAGES[@]}")

    # 去重，同时避免重复并发拉取同一个镜像。
    mapfile -t images < <(printf '%s\n' "${images[@]}" | sed '/^[[:space:]]*$/d' | sort -u)

    echo
    echo "开始预拉取镜像（并发数：${PULL_PARALLEL}）..."
    status_dir="$(mktemp -d)"
    failed_images=()
    running=0

    for idx in "${!images[@]}"; do
        if (( running >= PULL_PARALLEL )); then
            wait -n || true
            running=$((running - 1))
        fi

        (
            if pull_image_with_fallback "${images[$idx]}"; then
                printf '0\n' > "$status_dir/$idx"
            else
                printf '1\n' > "$status_dir/$idx"
            fi
        ) &
        running=$((running + 1))
    done

    wait || true

    for idx in "${!images[@]}"; do
        if [[ "$(cat "$status_dir/$idx" 2>/dev/null || printf '1')" != "0" ]]; then
            failed_images+=("${images[$idx]}")
        fi
    done
    rm -rf "$status_dir"

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

if [[ -f .env ]]; then
    SERVER_IP="${SERVER_HOST_IP:-$(detect_server_ip)}"
    if [[ -n "$SERVER_IP" && "$SERVER_IP" != "127.0.0.1" ]]; then
        set_env_value .env "SERVER_HOST" "$SERVER_IP"

        current_allowed="$(get_env_value .env "DJANGO_ALLOWED_HOSTS")"
        if ! printf '%s\n' "$current_allowed" | tr ',' '\n' | grep -qxF "$SERVER_IP"; then
            if [[ -n "$current_allowed" ]]; then
                set_env_value .env "DJANGO_ALLOWED_HOSTS" "${current_allowed},${SERVER_IP}"
            else
                set_env_value .env "DJANGO_ALLOWED_HOSTS" "localhost,127.0.0.1,${SERVER_IP}"
            fi
        fi
        echo
        echo "已设置服务器访问地址：${SERVER_IP}"
    fi
else
    echo
    echo "未找到 .env，跳过服务器 IP 配置；运行 bootstrap.sh 时会自动识别。"
fi

echo
echo "现在可以重新运行 bootstrap，例如："
echo "  ./scripts/bootstrap.sh dev --password '你的密码'"
