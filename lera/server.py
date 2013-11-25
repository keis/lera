from tornado import web, websocket
from tornado.gen import coroutine
import logging
import itertools
import json
from .session import Session

logger = logging.getLogger('server')

seq = itertools.count()


class WebSocket(websocket.WebSocketHandler):
    def open(self):
        logger.info('WebSocket session started');
        self.session = Session(self)
        self.session.start()

    def write_json(self, data):
        if self.ws_connection is None:
            logger.error('Tried to write message but disconnected')
            return
        self.write_message(json.dumps(data))

    @coroutine
    def on_message(self, message):
        s = next(seq)
        logger.info('processing message: [%s], %s', message, s)
        try:
            if not self.session.user:
                try:
                    yield self.session.handle_greeting(message)
                except:
                    self.close()

            else:
                yield self.session.handle_command(message)
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
