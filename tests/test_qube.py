from hamcrest import assert_that, equal_to
from hamcrest.library import has_entry, has_length
from contextlib import contextmanager
from pprint import pprint
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
    qube.apply_op(qa, ('change', 'number', (5, 6), 'tx001'))

    qb = qube.from_json(qube.to_json(qa))

    qube.apply_op(qa, ('change', 'name', ('zoidberg', 'bob'), 'tx002'))
    qube.apply_op(qb, ('change', 'number', (6, 7), 'tx003'))

    error, watch = track_error()

    m = qube.merge(qa, qb, error=watch)
    assert_that(m, has_entry('sequence', 3))
    assert_that(m, has_entry('data', has_entry('name', 'bob')))
    assert_that(m, has_entry('data', has_entry('number', 7)))
    assert_that(error, has_length(0))


def test_threeway_merge():
    qa = qube.init({'name': 'zoidberg', 'number': 5, 'value': 10})
    qube.apply_op(qa, ('change', 'number', (5, 6), 'tx001'))

    qb = qube.from_json(qube.to_json(qa))
    qc = qube.from_json(qube.to_json(qa))

    qube.apply_op(qa, ('change', 'name', ('zoidberg', 'bob'), 'tx002'))
    qube.apply_op(qb, ('change', 'number', (6, 7), 'tx003'))
    qube.apply_op(qc, ('change', 'value', (10, 9), 'tx004'))

    error, watch = track_error()

    m = qube.merge(qa, qb, qc, error=watch)
    assert_that(m, has_entry('sequence', 4))
    assert_that(m, has_entry('data', has_entry('name', 'bob')))
    assert_that(m, has_entry('data', has_entry('number', 7)))
    assert_that(m, has_entry('data', has_entry('value', 9)))

    assert_that(error, has_length(0))


def test_step_merge():
    qa = qube.init({'name': 'zoidberg', 'number': 5, 'value': 10})
    qube.apply_op(qa, ('change', 'number', (5, 6), 'tx001'))

    qb = qube.from_json(qube.to_json(qa))

    qube.apply_op(qa, ('change', 'name', ('zoidberg', 'bob'), 'tx002'))
    qube.apply_op(qb, ('change', 'number', (6, 7), 'tx003'))

    qc = qube.from_json(qube.to_json(qa))
    qube.apply_op(qc, ('change', 'value', (10, 9), 'tx004'))

    pprint(qa)
    pprint(qb)
    pprint(qc)

    error, watch = track_error()
    ma = qube.merge(qa, qb, error=watch)

    assert_that(error, has_length(0))
    assert_that(ma, has_entry('sequence', 3))
    assert_that(ma, has_entry('data', has_entry('name', 'bob')))
    assert_that(ma, has_entry('data', has_entry('number', 7)))
    assert_that(ma, has_entry('data', has_entry('value', 10)))

    print('---')
    pprint(ma)
    pprint(qc)

    error, watch = track_error()
    mb = qube.merge(ma, qc, error=watch)
    assert_that(error, has_length(0))
    assert_that(mb, has_entry('sequence', 4))
    assert_that(mb, has_entry('data', has_entry('name', 'bob')))
    assert_that(mb, has_entry('data', has_entry('number', 7)))
    assert_that(mb, has_entry('data', has_entry('value', 9)))


def test_step_merge_bside():
    qa = qube.init({'name': 'zoidberg', 'number': 5, 'value': 10})
    qube.apply_op(qa, ('change', 'number', (5, 6), 'tx001'))

    qb = qube.from_json(qube.to_json(qa))

    qube.apply_op(qa, ('change', 'name', ('zoidberg', 'bob'), 'tx002'))
    qube.apply_op(qb, ('change', 'number', (6, 7), 'tx004'))

    qc = qube.from_json(qube.to_json(qb))
    qube.apply_op(qc, ('change', 'value', (10, 9), 'tx004'))

    pprint(qa)
    pprint(qb)
    pprint(qc)

    error, watch = track_error()
    ma = qube.merge(qa, qb, error=watch)

    assert_that(error, has_length(0))
    assert_that(ma, has_entry('sequence', 3))
    assert_that(ma, has_entry('data', has_entry('name', 'bob')))
    assert_that(ma, has_entry('data', has_entry('number', 7)))
    assert_that(ma, has_entry('data', has_entry('value', 10)))

    print('---')
    pprint(ma)
    pprint(qc)

    error, watch = track_error()
    mb = qube.merge(ma, qc, error=watch)
    assert_that(error, has_length(0))
    assert_that(mb, has_entry('sequence', 4))
    assert_that(mb, has_entry('data', has_entry('name', 'bob')))
    assert_that(mb, has_entry('data', has_entry('number', 7)))
    assert_that(mb, has_entry('data', has_entry('value', 9)))
