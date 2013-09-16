from tornado import ioloop
from tornado.gen import coroutine
import riak
import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
db = riak.Client('http://localhost:8098')

spec = [{
    'description': 'room a',
}, {
    'description': 'room b',
}, {
    'description': 'room c',
}, {
    'description': 'room d',
}]

link_spec = [
    [(1, 'north'), (2, 'west')],
    [(0, 'south')],
    [(0, 'east'), (3, 'north')],
    [(2, 'south')]
]
    

@coroutine
def create():
    rooms = yield [db.save('rooms', None, d) for d in spec]
    logger.info('rooms created')
    for i, e in enumerate(link_spec):
        room = rooms[i]
        links = [('rooms', rooms[t].key, l) for (t, l) in e]
        logger.info('adding links for %s, %r', room.key, links)
        yield db.save('rooms', room.key, spec[i], links)
    print([x.key for x in rooms])


@coroutine
def main():
    try:
        yield create()
    except:
        logger.exception('oops')


def done(future):
    print("klart!", future)


loop = ioloop.IOLoop.instance()
loop.add_future(main(), done)
loop.start()
