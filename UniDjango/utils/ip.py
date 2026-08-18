"""客户端真实 IP 提取工具。

生产环境（Docker Compose）下 Django 前只有一层 Nginx，Nginx 通过
``proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`` 把真实客户端 IP
追加到 ``X-Forwarded-For`` 链尾，同时用 ``proxy_set_header X-Real-IP $remote_addr``
覆盖写入 ``X-Real-IP``。

因此**不能取 ``X-Forwarded-For`` 的第一个值**（那是客户端可伪造的），只能信任
可信代理追加在链尾的地址，或直接使用可信代理写入的 ``X-Real-IP``。
"""
from django.conf import settings


def get_client_ip(request):
    """返回最接近真实客户端的 IP 地址。

    规则：
    - 配置了可信代理（``TRUSTED_PROXY_COUNT >= 1``）时，优先取 ``X-Real-IP``
      （由我们自己的 Nginx 覆盖写入，客户端无法伪造），其次取
      ``X-Forwarded-For`` 链尾最后一个地址（同样由可信代理追加）。
    - 未配置可信代理（开发环境直连）时，忽略一切转发头，直接使用 ``REMOTE_ADDR``。
    """
    num_proxies = getattr(settings, 'TRUSTED_PROXY_COUNT', 0) or 0

    if num_proxies >= 1:
        real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
        if real_ip:
            return real_ip

        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            addrs = [a.strip() for a in xff.split(',') if a.strip()]
            if addrs:
                # 最后一个地址由最后一跳可信代理追加，是最可信的对端地址。
                return addrs[-1]

    return request.META.get('REMOTE_ADDR', 'unknown')
