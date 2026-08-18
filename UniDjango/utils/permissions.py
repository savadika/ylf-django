"""项目通用权限类。"""
from rest_framework.permissions import BasePermission


def _is_authenticated_user(user):
    return bool(
        user
        and getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', True)
    )


def get_user_permissions(user):
    """读取 SysUser 的权限集合，并缓存到用户实例上。"""
    if not _is_authenticated_user(user):
        return set()

    cached = getattr(user, '_unidjango_permissions', None)
    if cached is not None:
        return cached

    if hasattr(user, 'get_role_menus'):
        _, permissions = user.get_role_menus()
    elif hasattr(user, 'get_permissions'):
        permissions = user.get_permissions()
    else:
        permissions = []

    permissions = set(permissions or [])
    setattr(user, '_unidjango_permissions', permissions)
    return permissions


class IsAuthenticated(BasePermission):
    """要求请求已经由 JWT 中间件识别为有效登录用户。"""

    def has_permission(self, request, view):
        return _is_authenticated_user(getattr(request, 'user', None))


class HasPermission(BasePermission):
    """要求用户拥有指定权限之一，或拥有通配权限。"""

    required_permissions = ()

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not _is_authenticated_user(user):
            return False

        required = self.get_required_permissions(request, view)
        if not required:
            return True

        user_permissions = get_user_permissions(user)
        if '*:*:*' in user_permissions:
            return True

        return bool(user_permissions.intersection(required))

    def get_required_permissions(self, request, view):
        return set(self.required_permissions)


def permission_required(*permissions):
    """创建一个带指定权限要求的 Permission 类。"""
    return type(
        'PermissionRequired',
        (HasPermission,),
        {'required_permissions': tuple(permissions)},
    )


class ActionPermission(HasPermission):
    """按 ViewSet action 映射所需权限。"""

    action_permissions = {}

    def get_required_permissions(self, request, view):
        action = getattr(view, 'action', None)
        perms = self.action_permissions.get(action)
        if not perms:
            return set()
        if isinstance(perms, str):
            return {perms}
        return set(perms)


def permission_required_for_action(action_permissions):
    """创建一个按 action 映射权限的 Permission 类。"""
    return type(
        'ActionPermissionRequired',
        (ActionPermission,),
        {'action_permissions': action_permissions},
    )
