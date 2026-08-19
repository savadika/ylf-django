import json
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from user.jwt_auth import encode_token, get_token_from_request, revoke_token
from user.models import SysUser
from role.models import SysUserRole
from rest_framework import viewsets, serializers
from utils.media import build_absolute_media_url
from utils.pagination import CustomPageNumberPagination
from utils.filters import create_complex_filter_class
from utils.permissions import permission_required_for_action
from utils.ip import get_client_ip


LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 300


def _get_client_ip(request):
    return get_client_ip(request)


def _get_login_failure_key(username, ip):
    return f'login_fail:{ip}:{username}'


def _get_login_lock_key(username, ip):
    return f'login_lock:{ip}:{username}'


def _record_login_failure(fail_key, lock_key):
    """记录一次登录失败，并在达到阈值后设置短时锁定。"""
    try:
        failures = (cache.get(fail_key) or 0) + 1
        cache.set(fail_key, failures, LOGIN_LOCKOUT_SECONDS)
        if failures >= LOGIN_MAX_FAILURES:
            cache.set(lock_key, 1, LOGIN_LOCKOUT_SECONDS)
            cache.delete(fail_key)
    except Exception:
        pass


# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class GenerateToken(View):
    """
    测试生成token
    """
    def post(self, request):
        try:
            data = json.loads(request.body or b'{}')
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({'code': 400, 'message': '请求体必须是合法 JSON'}, status=400)

        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return JsonResponse({'code': 400, 'message': '用户名或密码不能为空'}, status=400)

        client_ip = _get_client_ip(request)
        lock_key = _get_login_lock_key(username, client_ip)
        fail_key = _get_login_failure_key(username, client_ip)

        try:
            locked = cache.get(lock_key)
        except Exception:
            locked = None
        if locked:
            return JsonResponse(
                {'code': 429, 'message': '失败次数过多，请稍后再试'},
                status=429,
                headers={'Retry-After': str(LOGIN_LOCKOUT_SECONDS)},
            )

        try:
            user = SysUser.objects.get(username=username)
        except SysUser.DoesNotExist:
            _record_login_failure(fail_key, lock_key)
            return JsonResponse({'code': 401, 'message': '用户不存在或密码错误'}, status=401)

        if not user.is_active or not check_password(password, user.password):
            _record_login_failure(fail_key, lock_key)
            return JsonResponse({'code': 401, 'message': '用户不存在或密码错误'}, status=401)

        try:
            cache.delete(fail_key)
            cache.delete(lock_key)
        except Exception:
            pass

        user.login_date = timezone.now()
        user.save(update_fields=['login_date'])

        token = encode_token(user)
        return JsonResponse({'code': 200, 'token': token})


class GetUserInfo(View):
    """
    获取用户信息
    """
    def get(self, request):
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return JsonResponse({'code': 401, 'message': '未登录'}, status=401)
        if not getattr(user, 'is_active', False):
            return JsonResponse({'code': 403, 'message': '用户已被禁用'}, status=403)

        menu_tree, permissions = user.get_role_menus()
        avatar_url = build_absolute_media_url(request, user.avatar)
        user_info = {
            'id': user.id,
            'username': user.username,
            'avatar': avatar_url,
            'menus': menu_tree,
            'permissions': permissions,
        }
        return JsonResponse({'code': 200, 'data': user_info})
        

@method_decorator(csrf_exempt, name='dispatch')
class LogOut(View):
    """
    注销登录
    """
    def post(self, request):
        token = get_token_from_request(request)
        if token:
            revoke_token(token)
        return JsonResponse({'code': 200, 'message': '注销成功'})


    


def _validate_password_strength(password, user):
    """接入 Django 密码强度校验，弱密码直接以 400 拒绝。

    Django 的 ``validate_password`` 抛出的是 ``django.core.exceptions.ValidationError``，
    需转换为 DRF 的 ``serializers.ValidationError`` 才会被正确渲染为 400 响应。
    """
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({'password': list(exc.messages)})


class SysUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    roles = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = SysUser
        fields = (
            'id', 'department', 'username', 'password', 'avatar', 'email', 'phone',
            'login_date', 'status', 'create_time', 'update_time', 'remark', 'roles'
        )

    def validate_email(self, value):
        # 邮箱为空时归一为 NULL，避免多个空串触发 unique 冲突。
        if value == '':
            return None
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        roles = validated_data.pop('roles', [])

        if not password:
            raise serializers.ValidationError({'password': '密码不能为空'})

        roles = list(dict.fromkeys(roles))

        user = SysUser(**validated_data)
        _validate_password_strength(password, user)

        with transaction.atomic():
            user.set_password(password)
            user.save()
            
            # 处理角色关联
            if roles:
                new_relations = []
                for role_id in roles:
                    new_relations.append(SysUserRole(user=user, role_id=role_id))
                SysUserRole.objects.bulk_create(new_relations)
                
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        roles = validated_data.pop('roles', None)
        
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            if password:
                _validate_password_strength(password, instance)
                instance.set_password(password)
            instance.save()
            
            # 处理角色关联更新
            if roles is not None:
                roles = list(dict.fromkeys(roles))
                # 先删除旧关联
                SysUserRole.objects.filter(user=instance).delete()
                # 再创建新关联
                new_relations = []
                for role_id in roles:
                    new_relations.append(SysUserRole(user=instance, role_id=role_id))
                SysUserRole.objects.bulk_create(new_relations)
                
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['roles'] = [relation.role_id for relation in instance.sysuserrole_set.all()]
        return ret


class SysUserViewSet(viewsets.ModelViewSet):
    """
    用户资源：提供列表、详情、创建、更新、局部更新、删除
    路由由 SimpleRouter 生成：/user 与 /user/{id}
    支持分页功能和高级搜索功能
    
    支持的搜索参数：
    - username: 用户名模糊搜索
    - email: 邮箱模糊搜索
    - phone: 电话模糊搜索
    - remark: 备注模糊搜索
    - status: 状态精确匹配
    - create_time_start/create_time_end: 创建时间范围
    - update_time_start/update_time_end: 更新时间范围
    - search: 全局搜索（搜索用户名、邮箱、电话、备注）
    """
    queryset = SysUser.objects.prefetch_related('sysuserrole_set__role').order_by('id')
    serializer_class = SysUserSerializer
    permission_classes = [permission_required_for_action({
        'list': 'system:user:list',
        'retrieve': 'system:user:query',
        'create': 'system:user:add',
        'update': 'system:user:edit',
        'partial_update': 'system:user:edit',
        'destroy': 'system:user:delete',
    })]
    pagination_class = CustomPageNumberPagination   # 自定义分页类
    filterset_class = create_complex_filter_class(SysUser, search_fields=['username', 'email', 'phone', 'remark'])  # 动态创建的过滤器类，会自动包含department字段
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def perform_destroy(self, instance):
        """删除用户前先清理用户角色关联，避免 PROTECT 外键导致 500。"""
        with transaction.atomic():
            SysUserRole.objects.filter(user=instance).delete()
            instance.delete()
