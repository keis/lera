from tornado import ioloop, web, websocket
from tornado.gen import coroutine
import logging
import itertools
import json
import mud
import riak

riak_client = riak.Client('http://localhost:8098')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('server')

seq = itertools.count()


class Session(object):
    db = riak_client

    def __init__(self, socket):
        self.socket = socket


class WebSocket(websocket.WebSocketHandler):
    def open(self):
        logger.info('WebSocket session started');
        self.user = None
        self.name = None
        self.quest = None
        self.start()

    def write_json(self, data):
        if self.ws_connection is None:
            logger.error('Tried to write message but disconnected')
            return
        self.write_message(json.dumps(data))

    def start(self):
        self.write_json({
            'message': 'WHAT.. is your name?',
            'prompt': 'Enter your name'
        })

    @coroutine
    def handle_greeting(self, message):
        if self.name is None:
            self.name = message
            self.write_json({
                'message': 'And what is your quest?',
                'prompt': 'Enter your quest'
            })

        elif self.quest is None:
            self.quest = message
            sess = Session(self)
            try:
                self.user = yield mud.User.get(sess, self.name, self.quest)
            except:
                logger.info('Rejecting login', exc_info=True)
                self.write_json({
                    'message': "That doesn't sound right"
                })
                del self.user
                self.close()
                return

            self.user.message('Welcome %s. Your quest is %s', self.user.name, self.user.quest)
            yield self.user.look()
        else:
            logger.warning('extra message to handle_greeting: %s', message)

    @coroutine
    def handle_command(self, message):
        # TODO: do something sane with message
        parts = message.split()

        if parts[0] == 'look':
            yield self.user.look()

        elif parts[0] == 'go':
            yield self.user.go(parts[1])

        elif parts[0] == 'say':
            yield self.user.say(' '.join(parts[1:]))

        else:
            self.user.message('.. what? %s' % parts[0])

    @coroutine
    def on_message(self, message):
        s = next(seq)
        logger.info('processing message: [%s], %s', message, s)
        try:
            if not self.user:
                yield self.handle_greeting(message)

            else:
                yield self.handle_command(message)
        except Exception as e:
            logger.exception('error when processing message')
        else:
            logger.debug('message processed %s', s)


class DevStatic(web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')


application = web.Application([
    ('/socket', WebSocket),
    ('/js/(.*)', DevStatic, {'path': './js'}),
    ('/(.*)', DevStatic, {'path': '.', 'default_filename': 'test.html'})
])

if __name__ == "__main__":
    application.listen(8888)
    ioloop.IOLoop.instance().start()
