from rest_framework.routers import SimpleRouter


class AppRouter(SimpleRouter):
    """项目统一路由器。

    统一使用无尾斜杠的 URL（``/user``、``/user/{id}``），配合
    ``settings.APPEND_SLASH = False`` 使用，主 URLconf 里的
    ``re_path(r'^user(?:/|$)')`` 已经同时兼容带/不带尾斜杠的入口。

    不再像旧版那样同时注册带/不带斜杠两份路由——那会导致同名路由重复注册，
    使 ``reverse()`` 产生歧义。
    """
    def __init__(self, *args, **kwargs):
        # DRF 3.16 起 trailing_slash 改为 __init__ 参数（布尔），类属性不再生效，
        # 必须在这里显式传入 False 才能生成无尾斜杠的 URL。
        kwargs.setdefault('trailing_slash', False)
        super().__init__(*args, **kwargs)
