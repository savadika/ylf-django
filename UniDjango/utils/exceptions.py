"""DRF 异常处理：把错误统一成 ApiResponse 信封。"""
import logging

from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

from utils.response import ApiResponse, BadRequest, Forbidden, NotFound, ServerError, Unauthorized

logger = logging.getLogger(__name__)


class CacheUnavailable(RuntimeError):
    """缓存服务不可用。

    用于 JWT 注销黑名单、登录失败锁定等依赖 Redis 的能力。调用方应把
    该异常转换为 503，而不是静默放行，避免 Redis 故障期间安全控制失效。
    """


_ERROR_RESPONSE_CLASSES = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    500: ServerError,
}


class ApiException(APIException):
    """业务异常基类。

    业务代码抛出：``raise ApiException('用户已存在', status_code=400)``，
    由 api_exception_handler 统一转成 {"code": status_code, "message": detail, "data": null}。
    """

    status_code = 400

    def __init__(self, detail=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if detail is None:
            detail = "error"
        super().__init__(detail)


def _message_from_detail(detail):
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        if "detail" in detail:
            return _message_from_detail(detail["detail"])
        parts = [f"{key}: {value}" for key, value in detail.items()]
        return "; ".join(parts)
    if isinstance(detail, (list, tuple)):
        return "; ".join(str(item) for item in detail)
    return str(detail)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # 非 DRF 异常（代码 bug 等）：记录完整堆栈，但只给客户端返回通用 500，避免泄露内部细节。
        logger.exception("Unhandled exception in %s", context.get("view"))
        return ServerError(message="服务器内部错误")

    message = _message_from_detail(response.data)
    response_cls = _ERROR_RESPONSE_CLASSES.get(response.status_code)
    if response_cls is not None:
        return response_cls(message=message)
    return ApiResponse(data=None, message=message, code=response.status_code)
