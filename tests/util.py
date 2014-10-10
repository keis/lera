import functools
from tornado.gen import coroutine
from tornado.ioloop import IOLoop


def async(f):
    @functools.wraps(f)
    def test_wrapper(*args, **kwargs):
        coro = coroutine(f)
        loop = IOLoop.current()
        loop.run_sync(functools.partial(coro, *args, **kwargs), timeout=2)

    return test_wrapper
