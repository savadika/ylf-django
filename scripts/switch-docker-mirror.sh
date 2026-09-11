#!/usr/bin/env bash
set -euo pipefail

# 一键切换 Docker registry-mirrors 并重启 Docker。
# 默认执行 auto：自动选择一个可用且不同于当前配置的镜像源。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"

DAEMON_JSON="${DOCKER_DAEMON_JSON:-/etc/docker/daemon.json}"
if [[ -L "$DAEMON_JSON" ]]; then
    DAEMON_JSON="$(readlink -f "$DAEMON_JSON")"
fi

# 候选镜像源：会把当前 daemon.json 中的源和这里列出的源合并后检测。
CANDIDATE_MIRRORS=(
    "https://docker.1ms.run"
    "https://docker.xuanyuan.me"
    "https://docker.m.daocloud.io"
    "https://hub.rat.dev"
    "https://docker.1panel.live"
    "https://docker.sparkcr.cn"
)

MODE=""
SET_MIRRORS=()
NO_RESTART=0
WITH_COMPOSE=0
SKIP_PROBE=0
ORIGINAL_ARGS=("$@")
BACKUP_FILE=""
HAD_ORIGINAL=0
CURL_MISSING_WARNED=0

log() {
    printf '\033[1;34m==>\033[0m %s\n' "$*"
}

warn() {
    printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2
}

die() {
    printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'EOF'
用法：./scripts/switch-docker-mirror.sh [命令] [镜像URL...] [选项]

命令：
  auto              自动探测候选源，使用第一个可用且不同于当前的镜像（默认）
  rotate            轮换当前 daemon.json 中 registry-mirrors 的顺序
  set <URL...>      完全替换为指定的一个或多个镜像
  add <URL...>      在当前镜像基础上追加镜像
  remove <URL...>   从当前镜像中移除指定镜像
  list              只查看当前和候选镜像，不修改配置

选项：
  --no-restart      只写配置，不重启 Docker
  --with-compose    重启 Docker 后再执行 docker compose up -d
  --skip-probe      跳过镜像源连通性检测
  -h, --help        显示帮助

示例：
  ./scripts/switch-docker-mirror.sh
  ./scripts/switch-docker-mirror.sh rotate
  ./scripts/switch-docker-mirror.sh set https://docker.1ms.run
  ./scripts/switch-docker-mirror.sh set https://docker.1ms.run https://docker.m.daocloud.io
  ./scripts/switch-docker-mirror.sh auto --with-compose
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        auto|rotate|set|add|remove|list)
            if [[ -n "$MODE" ]]; then
                die "只能指定一个命令：$MODE / $1"
            fi
            MODE="$1"
            shift
            ;;
        --no-restart)
            NO_RESTART=1
            shift
            ;;
        --with-compose)
            WITH_COMPOSE=1
            shift
            ;;
        --skip-probe)
            SKIP_PROBE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            die "未知参数：$1"
            ;;
        *)
            SET_MIRRORS+=("$1")
            shift
            ;;
    esac
done

normalize_url() {
    local url="$1"
    if [[ "$url" == *[[:space:]]* ]]; then
        warn "无效的镜像 URL：$url（不能包含空白字符）"
        return 1
    fi
    if [[ "$url" != http://* && "$url" != https://* ]]; then
        warn "无效的镜像 URL：$url（需要以 http:// 或 https:// 开头）"
        return 1
    fi

    local host
    host="${url#*://}"
    host="${host%%/*}"
    if [[ -z "$host" ]]; then
        warn "无效的镜像 URL：$url（缺少主机名）"
        return 1
    fi

    url="${url%/}"
    printf '%s\n' "$url"
    return 0
}

contains() {
    local needle="$1"
    shift
    local item
    for item in "$@"; do
        [[ "$item" == "$needle" ]] && return 0
    done
    return 1
}

append_unique() {
    local -n arr="$1"
    local item="$2"
    if ! contains "$item" "${arr[@]}"; then
        arr+=("$item")
    fi
}

read_current_mirrors() {
    local -n out="$1"
    out=()
    [[ -f "$DAEMON_JSON" ]] || return 0

    if command -v python3 >/dev/null 2>&1; then
        while IFS= read -r line; do
            [[ -n "$line" ]] && out+=("$line")
        done < <(python3 - "$DAEMON_JSON" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

if not isinstance(data, dict):
    sys.exit(0)

for item in data.get("registry-mirrors", []) or []:
    if isinstance(item, str) and item.strip():
        print(item.strip())
PY
        )
    elif command -v jq >/dev/null 2>&1; then
        while IFS= read -r line; do
            [[ -n "$line" ]] && out+=("$line")
        done < <(jq -r '.registry-mirrors[]?' "$DAEMON_JSON" 2>/dev/null || true)
    else
        warn "未找到 python3 或 jq，无法可靠读取当前 daemon.json"
    fi
}

write_daemon_json() {
    local urls=("$@")

    if command -v python3 >/dev/null 2>&1; then
        python3 - "$DAEMON_JSON" "${urls[@]}" <<'PY'
import json
import os
import stat
import sys
import tempfile

path = sys.argv[1]
urls = sys.argv[2:]

data = {}
mode = 0o644
uid = -1
gid = -1
if os.path.exists(path):
    try:
        st = os.stat(path)
        mode = stat.S_IMODE(st.st_mode)
        uid = st.st_uid
        gid = st.st_gid
    except Exception:
        pass

    try:
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = loaded
    except Exception:
        data = {}

data["registry-mirrors"] = urls
os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
fd, tmp = tempfile.mkstemp(prefix="daemon.json.", dir=os.path.dirname(path) or ".")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(tmp, mode)
    if uid != -1 and gid != -1:
        try:
            os.chown(tmp, uid, gid)
        except Exception:
            pass
    os.replace(tmp, path)
except Exception:
    try:
        os.unlink(tmp)
    except Exception:
        pass
    raise
PY
    elif command -v jq >/dev/null 2>&1; then
        local tmp_file
        tmp_file="$(mktemp "${DAEMON_JSON}.tmp.XXXXXX")"
        local json_array
        json_array="$(printf '%s\n' "${urls[@]}" | jq -R . | jq -s .)"
        local original_mode=""
        if [[ -f "$DAEMON_JSON" ]]; then
            original_mode="$(stat -c '%a' "$DAEMON_JSON" 2>/dev/null || true)"
            jq --argjson mirrors "$json_array" '.registry-mirrors = $mirrors' "$DAEMON_JSON" > "$tmp_file"
        else
            jq -n --argjson mirrors "$json_array" '{ "registry-mirrors": $mirrors }' > "$tmp_file"
        fi
        if [[ -n "$original_mode" ]]; then
            chmod "$original_mode" "$tmp_file"
        else
            chmod 644 "$tmp_file"
        fi
        mv "$tmp_file" "$DAEMON_JSON"
    else
        die "需要 python3 或 jq 才能安全写入 daemon.json"
    fi

    if command -v restorecon >/dev/null 2>&1; then
        restorecon "$DAEMON_JSON" >/dev/null 2>&1 || true
    fi
}

validate_daemon_json() {
    if ! command -v dockerd >/dev/null 2>&1; then
        warn "未找到 dockerd，跳过 Docker 配置校验"
        return 0
    fi

    log "校验 ${DAEMON_JSON}"
    local err
    if err="$(dockerd --validate --config-file "$DAEMON_JSON" 2>&1)"; then
        return 0
    fi

    warn "Docker 配置校验失败："
    printf '%s\n' "$err" >&2
    return 1
}

restore_backup() {
    if [[ "$HAD_ORIGINAL" -eq 1 ]]; then
        if [[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]]; then
            cp -a "$BACKUP_FILE" "$DAEMON_JSON"
            log "已从备份恢复 $DAEMON_JSON"
            return 0
        fi

        warn "备份文件不可用，无法自动恢复 $DAEMON_JSON"
        return 1
    fi

    if [[ -f "$DAEMON_JSON" ]]; then
        if ! rm -f -- "$DAEMON_JSON"; then
            warn "无法移除本次新建的 $DAEMON_JSON"
            return 1
        fi
        log "已移除本次新建的 $DAEMON_JSON"
    fi
    return 0
}

probe_mirror() {
    local url="$1"
    if [[ "$SKIP_PROBE" -eq 1 ]]; then
        return 0
    fi
    if ! command -v curl >/dev/null 2>&1; then
        if [[ "$CURL_MISSING_WARNED" -eq 0 ]]; then
            warn "未找到 curl，跳过连通性检测"
            CURL_MISSING_WARNED=1
        fi
        return 0
    fi

    local code
    code="$(curl -sS -L -o /dev/null -w '%{http_code}' \
        --connect-timeout 3 --max-time 5 "$url/v2/" 2>/dev/null || true)"
    [[ "$code" == "200" || "$code" == "401" ]]
}

list_mirrors() {
    local -a current=()
    read_current_mirrors current

    echo "当前 ${DAEMON_JSON} 中的 registry-mirrors："
    if [[ ${#current[@]} -eq 0 ]]; then
        echo "  （无）"
    else
        local m
        for m in "${current[@]}"; do
            echo "  - $m"
        done
    fi

    echo
    echo "候选镜像源："
    local m
    for m in "${CANDIDATE_MIRRORS[@]}"; do
        if contains "$m" "${current[@]}"; then
            echo "  - $m (当前配置中)"
        else
            echo "  - $m"
        fi
    done
}

require_root() {
    if [[ $EUID -eq 0 ]]; then
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        if [[ -n "${DOCKER_DAEMON_JSON:-}" ]]; then
            exec sudo env "DOCKER_DAEMON_JSON=$DOCKER_DAEMON_JSON" bash "$SCRIPT_PATH" "${ORIGINAL_ARGS[@]}"
        fi
        exec sudo bash "$SCRIPT_PATH" "${ORIGINAL_ARGS[@]}"
    fi

    die "请使用 root 运行，或使用：sudo bash $SCRIPT_PATH"
}

choose_target_mirrors() {
    local -n result="$1"
    result=()

    local -a current=()
    read_current_mirrors current

    local -a candidates=()
    local m
    for m in "${current[@]}" "${CANDIDATE_MIRRORS[@]}"; do
        append_unique candidates "$m"
    done

    case "${MODE:-auto}" in
        set)
            [[ ${#SET_MIRRORS[@]} -gt 0 ]] || die "set 命令需要至少一个镜像 URL"
            local normalized
            for m in "${SET_MIRRORS[@]}"; do
                normalized="$(normalize_url "$m")" || die "无法设置镜像 URL：$m"
                append_unique result "$normalized"
            done
            ;;
        add)
            [[ ${#SET_MIRRORS[@]} -gt 0 ]] || die "add 命令需要至少一个镜像 URL"
            local normalized
            for m in "${current[@]}"; do
                append_unique result "${m%/}"
            done
            for m in "${SET_MIRRORS[@]}"; do
                normalized="$(normalize_url "$m")" || die "无法添加镜像 URL：$m"
                append_unique result "$normalized"
            done
            ;;
        remove)
            [[ ${#SET_MIRRORS[@]} -gt 0 ]] || die "remove 命令需要至少一个镜像 URL"
            local keep
            for m in "${current[@]}"; do
                keep=1
                local r
                for r in "${SET_MIRRORS[@]}"; do
                    if [[ "${m%/}" == "${r%/}" ]]; then
                        keep=0
                        break
                    fi
                done
                [[ "$keep" -eq 1 ]] && result+=("${m%/}")
            done
            [[ ${#result[@]} -gt 0 ]] || die "移除后没有可用镜像源"
            ;;
        rotate)
            [[ ${#current[@]} -gt 0 ]] || die "当前 daemon.json 中没有可轮换的镜像源"
            for ((i = 1; i < ${#current[@]}; i++)); do
                result+=("${current[$i]}")
            done
            result+=("${current[0]}")
            ;;
        auto)
            local first_reachable=""
            local selected=""
            for m in "${candidates[@]}"; do
                if probe_mirror "$m"; then
                    if [[ -z "$first_reachable" ]]; then
                        first_reachable="$m"
                    fi
                    if ! contains "$m" "${current[@]}"; then
                        selected="$m"
                        break
                    fi
                fi
            done
            selected="${selected:-$first_reachable}"
            [[ -n "$selected" ]] || die "没有检测到可用的镜像源"
            result+=("$selected")
            ;;
        *)
            die "未知命令：${MODE:-auto}"
            ;;
    esac
}

restart_docker() {
    log "重启 Docker 服务"
    if command -v systemctl >/dev/null 2>&1; then
        if ! systemctl restart docker; then
            warn "systemctl restart docker 失败"
            return 1
        fi
    elif command -v service >/dev/null 2>&1; then
        if ! service docker restart; then
            warn "service docker restart 失败"
            return 1
        fi
    else
        die "未找到 systemctl 或 service，无法重启 Docker"
    fi

    local i
    for i in {1..30}; do
        if docker info >/dev/null 2>&1; then
            log "Docker 已恢复运行"
            return 0
        fi
        sleep 1
    done

    warn "Docker 在 30 秒内未恢复运行，请手动检查：systemctl status docker"
    return 1
}

restart_compose() {
    [[ "$WITH_COMPOSE" -eq 1 ]] || return 0

    if [[ ! -f "$ROOT_DIR/docker-compose.yml" ]]; then
        warn "未找到 $ROOT_DIR/docker-compose.yml，跳过 compose 重启"
        return 0
    fi

    log "重启 docker compose 服务"
    cd "$ROOT_DIR"
    if docker compose version >/dev/null 2>&1; then
        if ! docker compose up -d; then
            warn "docker compose up -d 失败"
            return 1
        fi
    elif docker-compose version >/dev/null 2>&1; then
        if ! docker-compose up -d; then
            warn "docker-compose up -d 失败"
            return 1
        fi
    else
        warn "未找到 docker compose，跳过项目服务重启"
    fi

    return 0
}

if [[ "$MODE" == "list" ]]; then
    list_mirrors
    exit 0
fi

require_root

log "读取当前配置"
declare -a target=()
choose_target_mirrors target

if [[ -f "$DAEMON_JSON" ]]; then
    HAD_ORIGINAL=1
    BACKUP_FILE="$(mktemp "${DAEMON_JSON}.bak.XXXXXX")"
    cp -a "$DAEMON_JSON" "$BACKUP_FILE"
    log "已备份原配置到 $BACKUP_FILE"
else
    HAD_ORIGINAL=0
    BACKUP_FILE=""
fi

log "写入 ${DAEMON_JSON}"
write_daemon_json "${target[@]}"

if ! validate_daemon_json; then
    restore_backup || true
    die "daemon.json 校验未通过，已尝试恢复原配置"
fi

echo
echo "已配置 registry-mirrors："
for m in "${target[@]}"; do
    echo "  - $m"
done

if [[ "$NO_RESTART" -eq 1 ]]; then
    warn "已按 --no-restart 跳过 Docker 重启"
else
    if restart_docker; then
        restart_compose || warn "docker compose 服务重启失败"
    else
        restore_backup || true
        die "Docker 重启失败，已尝试恢复原配置"
    fi
fi

echo
log "完成。可运行以下命令验证："
echo "  docker info | grep -A5 'Registry Mirrors'"
