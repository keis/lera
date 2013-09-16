from tornado import ioloop, web, websocket
from tornado.gen import coroutine
import logging
import json
import mud
import riak

riak_client = riak.Client('http://localhost:8098')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('server')


class WebSocket(websocket.WebSocketHandler):
    def open(self):
        self.user = None
        self.name = None
        self.quest = None
        self.start()

    def write_json(self, data):
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
            self.user = yield mud.User.get(riak_client, self.name, self.quest)

            desc = yield self.user.look()
            self.write_json({
                'message': desc
            })
        else:
            logger.warning('extra message to handle_greeting: %s', message)

    @coroutine
    def handle_command(self, message):
        # TODO: do something sane with message
        parts = message.split()

        if parts[0] == 'look':
            desc = yield self.user.look()

            self.write_json({
                'message': desc
            })

        if parts[0] == 'go':
            message = yield self.user.go(parts[1])

            self.write_json({
                'message': message
            })

        else:
            self.write_json({
                'message': '.. what?'
            })

    @coroutine
    def on_message(self, message):
        logger.info('processing message: %s', message)
        try:
            if not self.user:
                yield self.handle_greeting(message)

            else:
                yield self.handle_command(message)
        except Exception as e:
            logger.exception('error when processing message')


application = web.Application([
    ('/socket', WebSocket)
])

if __name__ == "__main__":
    application.listen(8888)
    ioloop.IOLoop.instance().start()
