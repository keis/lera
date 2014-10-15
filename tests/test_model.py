from hamcrest import assert_that, equal_to
from hamcrest.library import instance_of, has_property, has_entry, has_length, has_key
from .matchers import called_once_with
from tornado.gen import coroutine
from mock import Mock
from .util import async, CoroMock

import qube
from lera import model, riak


class FooModel(model.Model):
    bucket = 'foo_bucket'

    # TODO: Preferably this would be declarative
    @classmethod
    def queue_rollback(self, rollback, op):
        txid = op[-1]
        rollback.queue('bar', op[3], txid)


class StubDb(object):
    def __init__(self):
        self.get = CoroMock()
        self.save = CoroMock()


class StubDbResult(dict):
    def __init__(self, data, key=None, vclock=None, links=None):
        self.key = key
        self.vclock = vclock
        self.links = links
        self.update(data)


class StubRollback(object):
    txs = ()

    def __init__(self):
        self.queue = Mock()
        self.process = CoroMock()


@async
def test_read_returns_new_instance():
    db = StubDb()
    rollback = StubRollback()

    db.get.return_value = StubDbResult(qube.init(), key='zzz')

    m = yield FooModel.read(db, rollback, 'zzz')

    assert_that(m, instance_of(FooModel))


@async
def test_read_merges_siblings():
    db = StubDb()
    rollback = StubRollback()

    qa = qube.init({'test': set()})
    qb = qube.init({'test': set()})

    qube.apply_op(qa, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qb, ('add', 'test', 'abc', 'tx0'))

    qube.apply_op(qa, ('add', 'test', 'def', 'tx123'))
    qube.apply_op(qb, ('add', 'test', 'ghi', 'tx456'))

    def doraise(a, b):
        raise riak.Conflict('the_vclock',
                            'x/zzz',
                            [StubDbResult(qube.to_json(qa)),
                             StubDbResult(qube.to_json(qb))])

    db.get.side_effect = doraise

    m = yield FooModel.read(db, rollback, 'zzz')

    assert_that(m, instance_of(FooModel))
    assert_that(m.qube['data'], has_entry('test', {'abc', 'def', 'ghi'}))


@async
def test_read_queues_rollback():
    db = StubDb()
    rollback = StubRollback()

    qa = qube.init({'test': set()})
    qb = qube.init({'test': set()})

    qube.apply_op(qa, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qb, ('add', 'test', 'abc', 'tx0'))

    qube.apply_op(qa, ('rem', 'test', 'abc', 'tx123'))
    qube.apply_op(qa, ('add', 'test', 'def', 'tx456'))

    qube.apply_op(qb, ('rem', 'test', 'abc', 'tx789'))

    def doraise(a, b):
        raise riak.Conflict('the_vclock',
                            'x/zzz',
                            [StubDbResult(qube.to_json(qa)),
                             StubDbResult(qube.to_json(qb))])

    db.get.side_effect = doraise

    m = yield FooModel.read(db, rollback, 'zzz')

    assert_that(rollback.queue, called_once_with('bar', 'abc', 'tx789'))


@async
def test_read_performs_rollback():
    db = StubDb()
    rollback = StubRollback()
    rollback.txs = ('tx123',)

    qa = qube.init({'test': set()})
    qube.apply_op(qa, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qa, ('add', 'test', 'def', 'tx123'))
    qube.apply_op(qa, ('add', 'test', 'ghi', 'tx456'))

    db.get.return_value = StubDbResult(qube.to_json(qa), key='zzz')

    m = yield FooModel.read(db, rollback, 'zzz')

    assert_that(m.qube['journal'], has_length(2))
    assert_that(m.qube['data'], has_entry('test', {'abc', 'ghi'}))

    assert_that(db.save, called_once_with('foo_bucket',
                                          'zzz',
                                          has_key('data')))


@async
def test_read_performs_rollback_with_siblings():
    db = StubDb()
    rollback = StubRollback()
    rollback.txs = ('tx123', 'tx456')

    qa = qube.init({'test': set()})
    qb = qube.init({'test': set()})

    qube.apply_op(qa, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qa, ('add', 'test', 'ghi', 'tx456'))

    qube.apply_op(qb, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qb, ('add', 'test', 'def', 'tx123'))
    qube.apply_op(qb, ('add', 'test', 'jkl', 'tx789'))

    def doraise(a, b):
        raise riak.Conflict('the_vclock',
                            'x/zzz',
                            [StubDbResult(qube.to_json(qa)),
                             StubDbResult(qube.to_json(qb))])

    db.get.side_effect = doraise

    m = yield FooModel.read(db, rollback, 'zzz')

    assert_that(m.qube['journal'], has_length(2))
    assert_that(m.qube['data'], has_entry('test', {'abc', 'jkl'}))

    assert_that(db.save, called_once_with('foo_bucket',
                                          'zzz',
                                          has_key('data')))


@async
def test_read_conflict_rollback_not_reintroduced():
    db = StubDb()
    rollback = StubRollback()

    qa = qube.init({'test': set()})
    qb = qube.init({'test': set()})

    qube.apply_op(qa, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qa, ('rem', 'test', 'abc', 'tx456'))

    qube.apply_op(qb, ('add', 'test', 'abc', 'tx0'))
    qube.apply_op(qb, ('rem', 'test', 'abc', 'tx456'))

    qube.rollback(qa, 'tx456')
    qube.apply_op(qa, ('add', 'test', 'def', 'tx789'))

    qube.apply_op(qb, ('add', 'test', 'ghi', 'tx321'))

    def doraise(a, b):
        raise riak.Conflict('the_vclock',
                            'x/zzz',
                            [StubDbResult(qube.to_json(qa)),
                             StubDbResult(qube.to_json(qb))])

    db.get.side_effect = doraise

    m = yield FooModel.read(db, rollback, 'zzz')

    assert_that(m.qube['journal'], has_length(3))
    assert_that(m.qube['data'], has_entry('test', {'abc', 'def', 'ghi'}))

    assert_that(db.save, called_once_with('foo_bucket',
                                          'zzz',
                                          has_key('data')))
