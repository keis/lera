from hamcrest import assert_that, equal_to
from hamcrest.library import has_entry

import qube

def test_init():
    data = {'bob': 'bobby'}

    q = qube.init(data)
    assert_that(q, has_entry('sequence', 0))
    assert_that(q, has_entry('journal', []))
    assert_that(q, has_entry('data', data))
