#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "请使用 root 运行：sudo bash scripts/setup-rocky.sh" >&2
    exit 1
fi

if ! grep -qiE 'rocky' /etc/os-release; then
    echo "当前系统可能不是 Rocky Linux，脚本仍会尝试继续。" >&2
fi

echo "==> 安装基础工具"
dnf -y install dnf-plugins-core git curl ca-certificates

echo "==> 添加 Docker CE 仓库"
dnf -y config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

echo "==> 安装 Docker 和 Compose 插件"
dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> 启动并启用 Docker"
systemctl enable --now docker

echo "==> 配置防火墙"
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=9530/tcp
    firewall-cmd --permanent --add-port=8002/tcp
    firewall-cmd --reload
else
    echo "firewalld 未运行，跳过防火墙配置。"
fi

if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG docker "$SUDO_USER"
    echo "已把用户 $SUDO_USER 加入 docker 组，重新登录后生效。"
fi

echo
echo "✅ Rocky Linux 基础环境配置完成"
echo
echo "验证："
echo "  docker --version"
echo "  docker compose version"
echo
echo "如果当前用户不是 root，请退出并重新登录，使 docker 组权限生效。"
