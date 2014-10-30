from hamcrest import assert_that, equal_to
from hamcrest.library import has_entry, has_length
from contextlib import contextmanager

import qube

def track_error():
    error = []

    @contextmanager
    def watch(op):
        try:
            yield
        except Exception as e:
            print(e)
            error.append(op)

    return error, watch


def test_init():
    data = {'bob': 'bobby'}

    q = qube.init(data)
    assert_that(q, has_entry('sequence', 0))
    assert_that(q, has_entry('journal', []))
    assert_that(q, has_entry('data', data))


def test_merge():
    qa = qube.init({'name': 'zoidberg', 'number': 5})
    qube.apply_op(qa, ('change', 'number', (5, 6)))

    qb = qube.from_json(qube.to_json(qa))

    qube.apply_op(qa, ('change', 'name', ('zoidberg', 'bob')))
    qube.apply_op(qb, ('change', 'number', (6, 7)))

    error, watch = track_error()

    m = qube.merge(qa, qb, error=watch)
    assert_that(m, has_entry('sequence', 3))
    assert_that(m, has_entry('data', has_entry('name', 'bob')))
    assert_that(m, has_entry('data', has_entry('number', 7)))
    assert_that(error, has_length(0))


def test_threeway_merge():
    qa = qube.init({'name': 'zoidberg', 'number': 5, 'value': 10})
    qube.apply_op(qa, ('change', 'number', (5, 6)))

    qb = qube.from_json(qube.to_json(qa))
    qc = qube.from_json(qube.to_json(qa))

    qube.apply_op(qa, ('change', 'name', ('zoidberg', 'bob')))
    qube.apply_op(qb, ('change', 'number', (6, 7)))
    qube.apply_op(qc, ('change', 'value', (10, 9)))

    error, watch = track_error()

    m = qube.merge(qa, qb, qc, error=watch)
    assert_that(m, has_entry('sequence', 4))
    assert_that(m, has_entry('data', has_entry('name', 'bob')))
    assert_that(m, has_entry('data', has_entry('number', 7)))
    assert_that(m, has_entry('data', has_entry('value', 9)))

    assert_that(error, has_length(0))
