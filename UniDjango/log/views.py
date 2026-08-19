from rest_framework import viewsets, serializers
from .models import SysLog
from utils.pagination import CustomPageNumberPagination
from utils.filters import create_complex_filter_class
from utils.permissions import permission_required_for_action

class SysLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SysLog
        fields = (
            'id', 'username', 'user', 'ip', 'method', 'path', 'params', 'status',
            'cost_time', 'create_time', 'log_type', 'error_msg', 'traceback',
        )

class SysLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    系统日志资源：提供列表、详情
    支持分页功能和高级搜索功能
    支持的搜索参数：
    - log_type: 日志类型(INFO/ERROR)
    - method: 请求方式
    - status: 响应状态码
    - create_time_start/create_time_end: 创建时间范围
    - search: 全局搜索
    """
    queryset = SysLog.objects.all()
    serializer_class = SysLogSerializer
    permission_classes = [permission_required_for_action({
        'list': 'system:log:list',
        'retrieve': 'system:log:query',
    })]
    pagination_class = CustomPageNumberPagination
    filterset_class = create_complex_filter_class(SysLog, search_fields=['path', 'error_msg', 'params'])
    ordering_fields = ['create_time', 'cost_time', 'status']
