"""项目通用抽象模型基类。"""
from django.db import models


class BaseModel(models.Model):
    """所有业务模型的基类：提供自增主键 id。"""

    id = models.BigAutoField(primary_key=True, verbose_name="ID")

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """提供创建时间 / 更新时间。"""

    create_time = models.DateTimeField(auto_now_add=True, null=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")

    class Meta:
        abstract = True


class RemarkMixin(models.Model):
    """提供备注字段。"""

    remark = models.CharField(max_length=500, null=True, verbose_name="备注")

    class Meta:
        abstract = True


class StatusMixin(models.Model):
    """提供状态字段（正常/禁用）。"""

    status = models.IntegerField(
        null=True,
        default=1,
        choices=[(1, "正常"), (0, "禁用")],
        verbose_name="状态",
    )

    class Meta:
        abstract = True
