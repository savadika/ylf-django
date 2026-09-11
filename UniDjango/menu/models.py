from django.db import models

from role.models import SysRole
from utils.models import BaseModel, TimestampMixin, RemarkMixin


class SysMenu(BaseModel, TimestampMixin, RemarkMixin):
    """菜单表。"""

    name = models.CharField(max_length=50, verbose_name="菜单名称")
    icon = models.CharField(max_length=50, null=True, verbose_name="菜单图标")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="父菜单ID",
    )
    order_num = models.IntegerField(null=True, verbose_name="排序号")
    path = models.CharField(max_length=200, null=True, verbose_name="菜单路径")
    component = models.CharField(max_length=200, null=True, verbose_name="组件路径")
    menu_type = models.CharField(max_length=20, null=True, verbose_name="菜单类型")
    perms = models.CharField(max_length=100, null=True, verbose_name="权限标识")

    class Meta:
        db_table = "sys_menu"
        verbose_name = "菜单表"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=("parent", "name"),
                name="uniq_menu_parent_name",
            ),
        ]


class SysRoleMenu(BaseModel):
    """角色菜单关联表。"""

    role = models.ForeignKey(SysRole, on_delete=models.PROTECT, verbose_name="角色ID")
    menu = models.ForeignKey(SysMenu, on_delete=models.PROTECT, verbose_name="菜单ID")

    class Meta:
        db_table = "sys_role_menu"
        verbose_name = "角色菜单关联表"
        verbose_name_plural = verbose_name
        unique_together = ("role", "menu")
