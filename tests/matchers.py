from contextlib import contextmanager
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.helpers.wrap_matcher import wrap_matcher, is_matchable_type
from hamcrest import assert_that, instance_of


class RaisesContext(object):
    exception = None


@contextmanager
def assert_raises(matcher=None, message=''):
    # Short hand for instance_of matcher
    if is_matchable_type(matcher):
        matcher = instance_of(matcher)
    else:
        matcher = wrap_matcher(matcher)

    context = RaisesContext()
    try:
        yield context
    except Exception as e:
        context.exception = e

    assert_that(context.exception, matcher, message)


class CalledWith(BaseMatcher):
    def __init__(self, args, kwargs, count=None):
        self.args = (args, kwargs)
        self.count = count

    def _matches(self, item):
        if self.count is not None and item.call_count != self.count:
            return False

        return item.call_args == self.args

    def describe_call(self, call, desc):
        args, kwargs = call
        desc.append_description_of(args)
        desc.append_text(', ')
        desc.append_description_of(kwargs)

    def describe_mismatch(self, item, mismatch_description):
        if self.count is not None and item.call_count != self.count:
            mismatch_description.append_text(
                'was called %s times' % item.call_count)
        else:
            mismatch_description.append_text('was called with ')
            self.describe_call(item.call_args, mismatch_description)

    def describe_to(self, desc):
        desc.append_text('mock called with ')
        self.describe_call(self.args, desc)


def called_with(*args, **kwargs):
    return CalledWith(args, kwargs)


def called_once_with(*args, **kwargs):
    return CalledWith(args, kwargs, count=1)
