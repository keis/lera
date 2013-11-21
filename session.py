from tornado.gen import coroutine
import logging
import riak
import mud

logger = logging.getLogger('session')

riak_client = riak.Client('http://localhost:8098')


class Session(object):
    db = riak_client

    def __init__(self, socket):
        self.socket = socket
        self.user = None
        self.name = None
        self.quest = None

    def start(self):
        self.socket.write_json({
            'message': 'WHAT.. is your name?',
            'prompt': 'Enter your name'
        })

    @coroutine
    def handle_greeting(self, message):
        if self.name is None:
            self.name = message
            self.socket.write_json({
                'message': 'And what is your quest?',
                'prompt': 'Enter your quest'
            })

        elif self.quest is None:
            self.quest = message
            try:
                self.user = yield mud.User.get(self, self.name, self.quest)
            except:
                logger.info('Rejecting login', exc_info=True)
                self.socket.write_json({
                    'message': "That doesn't sound right"
                })
                del self.user
                raise

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
