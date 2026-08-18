import os
import uuid
import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from utils.permissions import IsAuthenticated


ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_FILE_COUNT = 5

class UploadFileView(APIView):
    """
    通用文件上传接口
    POST /upload/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    # 如果需要控制权限，可以在这里添加 permission_classes
    # permission_classes = [permissions.IsAuthenticated] 

    def post(self, request, format=None):  
        # 支持多文件上传
        files = request.FILES.getlist('file')
        if not files:
            return Response({
                "code": 400,
                "message": "未找到文件，请检查参数名是否为 'file'",
                "data": None
            }, status=400)

        if len(files) > MAX_FILE_COUNT:
            return Response({
                "code": 400,
                "message": f"一次最多上传 {MAX_FILE_COUNT} 个文件",
                "data": None,
            }, status=400)

        uploaded_urls = []
        
        for file_obj in files:
            ext = os.path.splitext(file_obj.name)[1]
            ext = ext.lower()
            if ext not in ALLOWED_EXTENSIONS:
                return Response({
                    "code": 400,
                    "message": "仅支持 jpg、jpeg、png、gif、webp 图片",
                    "data": None,
                }, status=400)

            if file_obj.size > MAX_FILE_SIZE:
                return Response({
                    "code": 400,
                    "message": "单个文件不能超过 2MB",
                    "data": None,
                }, status=400)

            # 生成保存路径: uploads/YYYY/MM/DD/uuid.ext
            unique_name = f"{uuid.uuid4().hex}{ext}"
            
            today = datetime.date.today()
            rel_path = f"uploads/{today.year}/{today.month:02d}/{today.day:02d}/{unique_name}"
            
            # 保存文件
            file_name = default_storage.save(rel_path, ContentFile(file_obj.read()))

            # 拼接完整访问 URL (用于返回给前端展示)
            full_url = request.build_absolute_uri(settings.MEDIA_URL + file_name)
              
            uploaded_urls.append({
                "url": full_url,
                "path": file_name  # 这是 default_storage.save 返回的相对路径
            })

        # 调整返回格式以适应多文件/单文件
        if len(uploaded_urls) == 1:
            data = {"url": uploaded_urls[0]['path']} # 只返回相对路径
        else:
            data = {
                "files": [item['path'] for item in uploaded_urls], 
                "url": uploaded_urls[0]['path'], # 兼容旧字段，只返回相对路径
            }

        return Response({
            "code": 200,
            "message": "上传成功",
            "data": data
        })
