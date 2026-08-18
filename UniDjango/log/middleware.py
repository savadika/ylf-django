import time
import json
import traceback
from django.utils.deprecation import MiddlewareMixin
from utils.log_writer import submit_log
from utils.ip import get_client_ip


SENSITIVE_KEYS = {
    'password', 'passwd', 'new_password', 'old_password', 'confirm_password',
    'token', 'access_token', 'refresh_token', 'jwt', 'authorization',
    'secret', 'api_key', 'apikey', 'cookie',
}


def _is_sensitive_key(key):
    normalized = str(key).lower().replace('-', '_')
    return any(part in normalized for part in SENSITIVE_KEYS)


def _sanitize_data(data):
    if isinstance(data, dict):
        return {
            key: ('***' if _is_sensitive_key(key) else _sanitize_data(value))
            for key, value in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [_sanitize_data(item) for item in data]
    return data


class RequestLogMiddleware(MiddlewareMixin):
    """
    请求日志中间件
    """

    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            cost_time = (time.time() - request.start_time) * 1000
        else:
            cost_time = 0

        # 过滤掉不需要记录的请求 (静态资源等)
        path = request.path
        if path.startswith('/media') or path.startswith('/static') or path.startswith('/favicon.ico'):
            return response

        # 获取用户信息
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            user = None

        # 获取请求参数
        try:
            if request.method == 'GET':
                raw_params = request.GET.dict()
            elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                if request.content_type == 'application/json':
                    raw_params = json.loads(request.body or b'{}')
                else:
                    raw_params = request.POST.dict()
            else:
                raw_params = {}
            params = json.dumps(_sanitize_data(raw_params), ensure_ascii=False)
        except Exception:
            params = ''

        # 获取IP（仅信任可信代理追加/写入的地址，防伪造）
        ip = get_client_ip(request)

        # 记录日志 (仅记录非ERROR类型，ERROR在process_exception中记录，或者根据response status判断)
        # 如果 status >= 500，通常意味着服务器错误，但也可能是由 process_exception 捕获并处理后的结果
        # 这里主要记录正常的审计日志
        if response.status_code < 500:
            submit_log(
                user=user,
                ip=ip,
                method=request.method,
                path=path,
                params=params[:2000], # 截断过长的参数
                status=response.status_code,
                cost_time=cost_time,
                log_type='INFO'
            )

        return response

    def process_exception(self, request, exception):
        # 捕获异常
        if hasattr(request, 'start_time'):
            cost_time = (time.time() - request.start_time) * 1000
        else:
            cost_time = 0

        # 获取IP（仅信任可信代理追加/写入的地址，防伪造）
        ip = get_client_ip(request)

        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            user = None

        # 记录异常日志
        try:
            if request.method == 'GET':
                raw_params = request.GET.dict()
            elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                if request.content_type == 'application/json':
                    raw_params = json.loads(request.body or b'{}')
                else:
                    raw_params = request.POST.dict()
            else:
                raw_params = {}
            params = json.dumps(_sanitize_data(raw_params), ensure_ascii=False)
        except Exception:
            params = ''

        submit_log(
            user=user,
            ip=ip,
            method=request.method,
            path=request.path,
            params=params[:2000],
            status=500,
            cost_time=cost_time,
            log_type='ERROR',
            error_msg=str(exception),
            traceback=traceback.format_exc()
        )
        
        return None # 返回None，交给Django默认的异常处理机制或后续中间件
