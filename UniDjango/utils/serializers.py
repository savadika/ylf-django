"""项目通用序列化器基类。"""
from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """通用 ModelSerializer 基类：主键与通用时间字段标记为只读。"""

    class Meta:
        abstract = True

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        model = getattr(self.Meta, "model", None)
        fields = getattr(self.Meta, "fields", None)

        if fields == "__all__" and model is not None:
            field_names = {field.name for field in model._meta.fields}
        elif fields:
            field_names = set(fields)
        else:
            field_names = set()

        for field_name in ("id", "create_time", "update_time"):
            if field_name in field_names:
                extra_kwargs.setdefault(field_name, {})
                extra_kwargs[field_name]["read_only"] = True
        return extra_kwargs
