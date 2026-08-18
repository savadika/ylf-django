from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from jwt import ExpiredSignatureError,InvalidTokenError,PyJWTError
from user.models import SysUser
from user.jwt_auth import decode_token, get_token_from_request, is_token_revoked


class JwtAuthenticationMiddleware(MiddlewareMixin):
    """
    jwt解析中间件，如果不通过token认证，则返回401错误。
    """

    def process_request(self, request):
        # 默认匿名：确保 request.user 恒有定义，后续中间件/视图可安全读取。
        # 认证成功后下面会覆盖为 SysUser 实例。
        request.user = None

        path = request.path
        path_normalized = path.rstrip('/') or '/'

        public_exact = {
            '/user/gen_token',
        }
        public_prefixes = ['/media', '/static', '/favicon.ico']
        if getattr(settings, 'SWAGGER_ENABLED', False):
            public_prefixes.extend(['/swagger', '/redoc'])

        # 放行静态资源、Swagger 文档和白名单接口
        if path_normalized in public_exact or any(path.startswith(prefix) for prefix in public_prefixes):
            return None

        token = get_token_from_request(request)
        if not token:
            return JsonResponse({'code': 401, 'message': '缺少token'}, status=401)

        try:
            payload = decode_token(token)
            if is_token_revoked(payload):
                return JsonResponse({'code': 401, 'message': 'token已失效'}, status=401)
            user_id = payload.get('user_id')
            user = SysUser.objects.get(id=user_id)
        except ExpiredSignatureError:
            return JsonResponse({'code': 401, 'message': 'token已过期'}, status=401)
        except InvalidTokenError:
            return JsonResponse({'code': 401, 'message': '无效的token'}, status=401)
        except PyJWTError:
            return JsonResponse({'code': 401, 'message': 'token解析错误'}, status=401)
        except SysUser.DoesNotExist:
            return JsonResponse({'code': 401, 'message': '用户不存在'}, status=401)
        except (TypeError, ValueError):
            return JsonResponse({'code': 401, 'message': '无效的token'}, status=401)

        if not getattr(user, 'is_active', False):
            return JsonResponse({'code': 403, 'message': '用户已被禁用'}, status=403)

        # 将用户信息附加到 request 中
        request.user = user
        request.auth = token
        return None
