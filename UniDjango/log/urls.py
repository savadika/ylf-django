from django.urls import include, path
from utils.routers import AppRouter
from .views import SysLogViewSet

router = AppRouter()
router.register(r'', SysLogViewSet, basename='log')

urlpatterns = [
    path('', include(router.urls)),
]
