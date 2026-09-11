"""项目统一 ViewSet 基类。

所有 ViewSet 继承这里定义的基类，通用 CRUD 响应统一走 ``utils.response`` 信封。
"""
from rest_framework import viewsets

from utils.filters import ComplexQueryMixin
from utils.response import Ok


class _StandardListRetrieveMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).data
            return Ok(data=data)
        serializer = self.get_serializer(queryset, many=True)
        return Ok(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Ok(data=serializer.data)


class BaseModelViewSet(_StandardListRetrieveMixin, ComplexQueryMixin, viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Ok(data=serializer.data, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Ok(data=serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Ok(data=None)


class BaseReadOnlyModelViewSet(_StandardListRetrieveMixin, ComplexQueryMixin, viewsets.ReadOnlyModelViewSet):
    pass
