import functools
from mock import Mock
from tornado.gen import coroutine
from tornado.ioloop import IOLoop
from tornado.concurrent import Future


def async(f):
    @functools.wraps(f)
    def test_wrapper(*args, **kwargs):
        coro = coroutine(f)
        loop = IOLoop.current()
        loop.run_sync(functools.partial(coro, *args, **kwargs), timeout=2)

    return test_wrapper


class CoroMock(Mock):
    @coroutine
    def __call__(self, *args, **kwargs):
        return Mock.__call__(self, *args, **kwargs)
