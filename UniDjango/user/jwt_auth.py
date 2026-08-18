"""轻量级 JWT 工具。

用于替代已废弃的 ``djangorestframework-jwt``，直接基于 PyJWT 2.x 实现
令牌生成、解析和注销黑名单。
"""
import datetime
import uuid

import jwt
from django.conf import settings
from django.core.cache import cache


JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = datetime.timedelta(days=7)
REVOKE_CACHE_PREFIX = 'jwt_revoke:'


def _now_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).timestamp()


def _get_jwt_secret():
    """JWT 专用签名密钥，与 Django SECRET_KEY 分离。"""
    return getattr(settings, 'JWT_SECRET_KEY', '') or settings.SECRET_KEY


def encode_token(user):
    """为指定用户签发 JWT。"""
    now = _now_timestamp()
    payload = {
        'user_id': user.pk,
        'jti': uuid.uuid4().hex,
        'iat': now,
        'exp': now + JWT_EXPIRATION_DELTA.total_seconds(),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token):
    """解析并校验 JWT。"""
    return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])


def get_token_from_request(request):
    """从 Authorization 请求头中提取原始 token，兼容带或不带 Bearer 前缀。"""
    raw_token = request.META.get('HTTP_AUTHORIZATION', '')
    token = raw_token.strip()
    if token.lower().startswith('bearer '):
        token = token[7:].strip()
    return token or None


def is_token_revoked(payload):
    """判断 token 是否已被主动注销。"""
    jti = payload.get('jti')
    if not jti:
        return False
    try:
        return bool(cache.get(REVOKE_CACHE_PREFIX + jti))
    except Exception:
        return False


def revoke_token(token):
    """将 token 加入黑名单，直到其自然过期。"""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return

    jti = payload.get('jti')
    if not jti:
        return

    timeout = JWT_EXPIRATION_DELTA.total_seconds()
    exp = payload.get('exp')
    if exp:
        remaining = exp - _now_timestamp()
        if remaining <= 0:
            return
        timeout = min(timeout, remaining)

    try:
        cache.set(REVOKE_CACHE_PREFIX + jti, 1, int(timeout) or 1)
    except Exception:
        pass
