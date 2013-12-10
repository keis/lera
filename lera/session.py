from tornado.gen import coroutine
import logging
import smoke
from . import riak, mud, action

logger = logging.getLogger('session')

riak_client = riak.Client('http://localhost:8098')


class Session(object):
    db = riak_client
    world = mud.world

    def __init__(self, socket):
        self.socket = socket
        self.user = None
        self.name = None
        self.quest = None

        self.on_enter = smoke.weak(self._on_enter)
        self.on_leave = smoke.weak(self._on_leave)
        self.on_say = smoke.weak(self._on_say)

    def _on_enter(self, user=None, room=None):
        if room != self.user.room:
            raise smoke.Disconnect()
        if user != self.user.key:
            self.message('%s enters the room', user)

    def _on_leave(self, user=None, room=None):
        if room != self.user.room:
            raise smoke.Disconnect()
        if user != self.user.key:
            self.message('%s leaves the room', user)

    def _on_say(self, name=None, message=None):
        if name != self.user.name:
            self.message('%s says %s' % (name, message))

    def message(self, frmt, *args):
        self.socket.write_json({
            'message': frmt % args
        })

    def start(self):
        self.socket.write_json({
            'message': 'WHAT.. is your name?',
            'prompt': 'Enter your name'
        })

    @coroutine
    def handle_greeting(self, message):
        if self.name is None:
            logger.debug('(S%s) Got username "%s"', id(self), message)
            self.name = message
            self.socket.write_json({
                'message': 'And what is your quest?',
                'prompt': 'Enter your quest'
            })

        elif self.quest is None:
            logger.debug('(S%s) Got quest "%s"', id(self), message)
            self.quest = message
            try:
                self.user = yield mud.User.get(self.db, self.name, self.quest)

                self.world.subscribe((self.world.enter, self.user.room), self.on_enter)
                self.world.subscribe((self.world.leave, self.user.room), self.on_leave)
                self.world.subscribe((self.world.say, self.user.room), self.on_say)

            except:
                logger.info('Rejecting login', exc_info=True)
                self.socket.write_json({
                    'message': "That doesn't sound right"
                })
                del self.user
                raise

            self.message('Welcome %s. Your quest is %s', self.user.name, self.user.quest)
            yield action.look(self)
        else:
            logger.warning('extra message to handle_greeting: %s', message)

    @coroutine
    def handle_command(self, message):
        # TODO: do something sane with message
        parts = message.split()

        if parts[0] == 'look':
            yield action.look(self)

        elif parts[0] == 'go':
            yield action.go(self, parts[1])

        elif parts[0] == 'say':
            yield action.say(self, ' '.join(parts[1:]))

        else:
            self.message('.. what? %s' % parts[0])
