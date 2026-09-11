from django.db import models
from utils.models import BaseModel, TimestampMixin, RemarkMixin, StatusMixin

# Create your models here.
class SysDep(BaseModel, TimestampMixin, RemarkMixin, StatusMixin):
    """
    部门模型
    """
    dep_name = models.CharField(max_length=150, unique=True, verbose_name='部门名称')

    class Meta:
        db_table = 'sys_department'
        verbose_name = '部门'
        verbose_name_plural = verbose_name

# Create your models here.
