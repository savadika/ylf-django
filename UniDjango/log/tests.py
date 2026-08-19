from django.test import TestCase

from log.models import SysLog
from log.views import SysLogSerializer


class SysLogSerializerTests(TestCase):
    def test_serializer_includes_params_and_traceback(self):
        log = SysLog.objects.create(
            path='/user',
            params='{"username": "admin"}',
            traceback='Traceback (most recent call last)...',
        )

        data = SysLogSerializer(log).data

        self.assertEqual(data['params'], '{"username": "admin"}')
        self.assertEqual(data['traceback'], 'Traceback (most recent call last)...')
