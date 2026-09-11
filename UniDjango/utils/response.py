"""统一响应信封基类。

所有接口响应都继承自 ``ApiResponse``，统一返回：
{"code": <code>, "message": <message>, "data": <data>}

约定：应用层成功统一使用 ``code=200``；错误使用 HTTP 状态码（400/401/403/404/500）。
"""
from rest_framework.response import Response


class ApiResponse(Response):
    """响应信封基类。"""

    default_code = 200
    default_message = "ok"

    def __init__(self, data=None, message=None, code=None, status=None, headers=None):
        code = self.default_code if code is None else code
        message = self.default_message if message is None else message
        if status is None:
            status = code if code >= 400 else 200
        super().__init__(
            {"code": code, "message": message, "data": data},
            status=status,
            headers=headers,
        )
        self.is_api_response = True


class Ok(ApiResponse):
    """成功响应。"""


class BadRequest(ApiResponse):
    default_code = 400
    default_message = "bad request"


class Unauthorized(ApiResponse):
    default_code = 401
    default_message = "unauthorized"


class Forbidden(ApiResponse):
    default_code = 403
    default_message = "forbidden"


class NotFound(ApiResponse):
    default_code = 404
    default_message = "not found"


class ServerError(ApiResponse):
    default_code = 500
    default_message = "server error"
