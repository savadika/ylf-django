from django.urls import path, include
from .views import SysMenuViewSet
from utils.routers import AppRouter

router = AppRouter()
router.register(r'', SysMenuViewSet, basename='menu')

urlpatterns = [
    path('', include(router.urls)),
]
