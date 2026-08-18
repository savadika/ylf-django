"""user 模块测试：JWT、密码强度、登录锁定、中间件、过滤器。"""
import json
from datetime import datetime
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.serializers import ValidationError
from rest_framework.test import APIClient

from user.jwt_auth import decode_token, encode_token, is_token_revoked, revoke_token
from user.models import SysUser
from user.views import LOGIN_MAX_FAILURES, SysUserSerializer
from utils.filters import create_complex_filter_class


# 测试期间用本地内存缓存，避免依赖外部 Redis。
LOCMEM_CACHE = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
}


@override_settings(CACHES=LOCMEM_CACHE)
class JwtAuthTests(SimpleTestCase):
    def test_encode_decode_roundtrip(self):
        user = SysUser(id=7, username='u')
        token = encode_token(user)
        payload = decode_token(token)
        self.assertEqual(payload['user_id'], 7)

    def test_revoke_marks_token_revoked(self):
        user = SysUser(id=8, username='u')
        token = encode_token(user)
        self.assertFalse(is_token_revoked(decode_token(token)))
        revoke_token(token)
        self.assertTrue(is_token_revoked(decode_token(token)))


class PasswordValidationTests(TestCase):
    def test_weak_password_rejected(self):
        data = {'username': 'weakuser', 'password': '123', 'email': 'weak@example.com'}
        serializer = SysUserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError):
            serializer.save()

    def test_empty_email_normalized_to_none(self):
        data = {'username': 'emailuser', 'password': 'StrongPass123', 'email': ''}
        serializer = SysUserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data['email'])

    def test_valid_password_creates_user(self):
        data = {'username': 'okuser', 'password': 'StrongPass123', 'email': 'ok@example.com'}
        serializer = SysUserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertTrue(SysUser.objects.filter(id=user.id).exists())


@override_settings(CACHES=LOCMEM_CACHE)
class LoginLockoutTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 屏蔽请求日志的后台写库，避免异步线程干扰测试事务。
        cls._log_patch = mock.patch('log.middleware.submit_log')
        cls._log_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls._log_patch.stop()
        super().tearDownClass()

    def setUp(self):
        # 清空 locmem 缓存，避免上个用例的登录锁定状态串扰到本用例。
        cache.clear()
        SysUser.objects.create(
            username='locktest',
            password=make_password('right-password'),
            email='locktest@example.com',
            status=1,
        )
        self.client = APIClient()

    def test_locks_after_max_failures(self):
        url = '/user/gen_token'
        body = json.dumps({'username': 'locktest', 'password': 'wrong'})
        for _ in range(LOGIN_MAX_FAILURES):
            resp = self.client.post(url, data=body, content_type='application/json')
            self.assertEqual(resp.status_code, 401)
        resp = self.client.post(url, data=body, content_type='application/json')
        self.assertEqual(resp.status_code, 429)

    def test_success_clears_failures(self):
        url = '/user/gen_token'
        wrong = json.dumps({'username': 'locktest', 'password': 'wrong'})
        right = json.dumps({'username': 'locktest', 'password': 'right-password'})
        for _ in range(LOGIN_MAX_FAILURES - 1):
            self.client.post(url, data=wrong, content_type='application/json')
        resp = self.client.post(url, data=right, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.json())


class JwtMiddlewareTests(TestCase):
    @mock.patch('log.middleware.submit_log')
    def test_missing_token_returns_401(self, _mock_log):
        resp = APIClient().get('/user/get_user_info')
        self.assertEqual(resp.status_code, 401)


class SysUserFilterTests(SimpleTestCase):
    def test_password_not_exposed_as_filter(self):
        filter_cls = create_complex_filter_class(SysUser, search_fields=['username'])
        self.assertNotIn('password', filter_cls.base_filters)
        self.assertIn('username', filter_cls.base_filters)


class SysUserDateTimeFilterTests(TestCase):
    def test_datetime_end_filter_includes_whole_day(self):
        user1 = SysUser.objects.create(
            username='eod-user-1',
            password='x',
            email='eod-user-1@example.com',
            status=1,
        )
        user2 = SysUser.objects.create(
            username='eod-user-2',
            password='x',
            email='eod-user-2@example.com',
            status=1,
        )

        SysUser.objects.filter(pk=user1.pk).update(
            create_time=timezone.make_aware(datetime(2026, 8, 18, 23, 30))
        )
        SysUser.objects.filter(pk=user2.pk).update(
            create_time=timezone.make_aware(datetime(2026, 8, 19, 0, 30))
        )

        filter_cls = create_complex_filter_class(SysUser, search_fields=['username'])
        filtered = filter_cls(
            {'create_time_start': '2026-08-18', 'create_time_end': '2026-08-18'},
            queryset=SysUser.objects.all(),
        ).qs

        self.assertEqual(
            set(filtered.values_list('username', flat=True)),
            {'eod-user-1'},
        )
