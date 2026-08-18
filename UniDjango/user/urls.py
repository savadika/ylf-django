from django.urls import path, include

from user.views import GenerateToken, GetUserInfo, LogOut, SysUserViewSet
from utils.routers import AppRouter

# 创建支持可选斜杠的路由器
router = AppRouter()
router.register(r'', SysUserViewSet, basename='user')


urlpatterns = [
    path('gen_token', GenerateToken.as_view(), name='gen_token'),  # 测试生成token
    path('get_user_info', GetUserInfo.as_view(), name='get_user_info'),  # 测试生成token
    path('logout', LogOut.as_view(), name='logout'),  # 退出登录

    # 支持带斜杠和不带斜杠的路由
    # - GET /user 或 /user/ → 用户列表
    # - POST /user 或 /user/ → 新增用户
    # - GET /user/{id} 或 /user/{id}/ → 用户详情
    # - PUT /user/{id} 或 /user/{id}/ → 全量更新
    # - PATCH /user/{id} 或 /user/{id}/ → 局部更新
    # - DELETE /user/{id} 或 /user/{id}/ → 删除
    path('', include(router.urls)),
]



