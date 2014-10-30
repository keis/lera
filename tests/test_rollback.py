from hamcrest import assert_that, equal_to
from hamcrest.library import has_length
from asyncio import coroutine
from mock import Mock
from .util import async

from lera import rollback


class Model(object):
    def __init__(self, bucket):
        self.bucket = bucket
        self.calls = []

    @coroutine
    def read(self, db, rollback, key):
        self.calls.append((db, rollback, key))
        return


class NewRollback(object):
    def __init__(self, bucket, rollback):
        self.bucket = bucket
        self.calls = []
        self.rollback = rollback

    @coroutine
    def read(self, db, rollback, key):
        rollback.queue(*self.rollback)
        self.calls.append((db, rollback, key))
        return


@async
def test_processes_until_queue_is_empty():
    db = Mock()
    r = rollback.Rollback([Model('foo'), Model('bar')])

    r.queue('foo', '10', 'tx0')
    r.queue('bar', '20', 'tx1')

    assert_that(r._queue, has_length(2))

    yield from r.process(db)

    assert_that(r._queue, has_length(0))


@async
def test_queue_during_process():
    db = Mock()
    b = Model('bar')
    r = rollback.Rollback([NewRollback('foo', ('bar', '20', 'tx2')), b])

    r.queue('foo', '10', 'tx0')

    assert_that(r._queue, has_length(1))

    yield from r.process(db)

    assert_that(r._queue, has_length(0))
    assert_that(b.calls[0], equal_to((db, r, '20')))
