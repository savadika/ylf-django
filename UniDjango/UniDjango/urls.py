"""
URL configuration for UniDjango project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from utils.upload import UploadFileView

# Swagger 配置
schema_view = get_schema_view(
   openapi.Info(
      title="UniDjango API",
      default_version='v1',
      description="UniDjango 项目接口文档",
      terms_of_service="",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    re_path(r'^user(?:/|$)', include('user.urls')), # 用户模块，支持带/和不带/
    re_path(r'^department(?:/|$)', include('department.urls')), # 部门模块，支持带/和不带/
    re_path(r'^role(?:/|$)', include('role.urls')), # 角色模块，支持带/和不带/
    re_path(r'^menu(?:/|$)', include('menu.urls')), # 菜单模块
    re_path(r'^log(?:/|$)', include('log.urls')), # 日志模块
    path('upload/', UploadFileView.as_view(), name='upload_file'), # 通用上传接口

 ]

# Swagger / ReDoc 文档仅在调试模式开启，生产环境不注册路由。
if getattr(settings, 'SWAGGER_ENABLED', False):
    urlpatterns += [
        #  Swagger UI : http://127.0.0.1:8000/swagger/
        #  ReDoc : http://127.0.0.1:8000/redoc/  更加可视化阅读
        re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
        re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]

# 开发环境下提供 /media/ 路由以访问 MEDIA_ROOT 内的文件
if settings.DEBUG:
     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
