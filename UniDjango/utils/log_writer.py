"""异步写入 SysLog，避免每个 HTTP 请求都阻塞在数据库写日志上。

使用**有界队列** + 少量后台工作线程：
- 普通日志：队列满时直接丢弃（尽力而为），绝不影响业务响应。
- ERROR 日志：优先入队，最多等待 5s，尽量保证异常堆栈不丢失。
"""
import queue
import threading

from django.db import close_old_connections
from log.models import SysLog


MAX_QUEUE_SIZE = 1000  # 有界队列上限，避免 DB 慢时内存无限堆积
WORKER_COUNT = 4

_log_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)


def _writer_loop():
    while True:
        attrs = _log_queue.get()
        if attrs is None:  # 停止信号
            break
        try:
            SysLog.objects.create(**attrs)
        except Exception:
            # 日志写库失败不能影响业务响应，也不让工作线程退出。
            pass
        finally:
            # 关闭当前线程的连接，避免长期空闲后 MySQL 连接被回收导致报错。
            close_old_connections()


for _ in range(WORKER_COUNT):
    threading.Thread(target=_writer_loop, daemon=True).start()


def submit_log(**attrs):
    """提交一条日志到后台队列。

    队列满时：ERROR 日志阻塞等待最多 5s，普通日志直接丢弃。
    """
    try:
        if attrs.get('log_type') == 'ERROR':
            _log_queue.put(attrs, block=True, timeout=5)
        else:
            _log_queue.put_nowait(attrs)
    except Exception:
        # 队列已满或线程池已关闭：丢弃日志，不阻塞业务。
        pass
