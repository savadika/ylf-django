from rest_framework import serializers

from .models import SysMenu, SysRoleMenu
from utils.serializers import BaseModelSerializer


class SysMenuSerializer(BaseModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=SysMenu.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SysMenu
        fields = (
            "id",
            "name",
            "icon",
            "parent_id",
            "order_num",
            "path",
            "component",
            "menu_type",
            "perms",
            "remark",
        )

    def _get_descendant_ids(self, root_id):
        descendant_ids = set()
        pending = [root_id]
        while pending:
            child_ids = list(
                SysMenu.objects.filter(parent_id__in=pending).values_list("id", flat=True)
            )
            descendant_ids.update(child_ids)
            pending = child_ids
        return descendant_ids

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        parent = attrs.get("parent")

        # 校验同一父级下菜单名称唯一；父级为空时校验顶级菜单名称唯一。
        # 数据库的复合唯一约束对 NULL parent 不生效，因此顶级节点在此补齐应用层校验。
        if "name" in attrs or "parent" in attrs:
            target_name = attrs.get("name", getattr(instance, "name", None))
            target_parent = attrs.get("parent", getattr(instance, "parent", None))
            if target_name:
                qs = SysMenu.objects.filter(name=target_name, parent=target_parent)
                if instance is not None and getattr(instance, "pk", None):
                    qs = qs.exclude(pk=instance.pk)
                if qs.exists():
                    raise serializers.ValidationError({"name": "同一层级下菜单名称不能重复"})

        if parent is None or instance is None or not getattr(instance, "pk", None):
            return attrs

        if parent.pk == instance.pk:
            raise serializers.ValidationError({"parent_id": "不能选择自身作为父级"})

        if parent.pk in self._get_descendant_ids(instance.pk):
            raise serializers.ValidationError({"parent_id": "不能选择自己的子级作为父级"})

        return attrs


class SysRoleMenuSerializer(BaseModelSerializer):
    class Meta:
        model = SysRoleMenu
        fields = "__all__"
