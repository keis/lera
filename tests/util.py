import functools
from mock import Mock
from asyncio import coroutine, get_event_loop


def async(f):
    @functools.wraps(f)
    def test_wrapper(*args, **kwargs):
        coro = coroutine(f)
        future = coro(*args, **kwargs)
        loop = get_event_loop()
        loop.run_until_complete(future)

    return test_wrapper


class CoroMock(Mock):
    @coroutine
    def __call__(self, *args, **kwargs):
        return Mock.__call__(self, *args, **kwargs)
