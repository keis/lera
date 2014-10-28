from asyncio import Task, coroutine
import logging
import smoke
import json
from . import riak, mud, action

logger = logging.getLogger(__name__)

riak_client = riak.Client('http://localhost:10018')

# Messages sent during login
MSG_NAME, MSG_QUEST = ({
    'message': 'WHAT.. is your name?',
    'prompt': 'Name'
}, {
    'message': 'And what is your quest?',
    'prompt': 'Quest'
})


class Session(object):
    db = riak_client
    world = mud.world

    def __init__(self, socket):
        self.socket = socket
        self.user = None
        self.name = None
        self.quest = None

        # Create callbacks that have weakref to self
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

    def write_json(self, data):
        Task(self.socket.send(json.dumps(data)))

    def message(self, frmt, *args):
        '''Send a plaintext message to the client'''
        self.write_json({'message': frmt % args})

    def start(self):
        self.write_json(MSG_NAME)

    def disconnect_room(self):
        '''Helper to disconnect signal subscriptions of the current room'''

        room = self.user.room
        self.world.enter(room).disconnect(self.on_enter)
        self.world.leave(room).disconnect(self.on_leave)
        self.world.say(room).disconnect(self.on_say)

    def subscribe_room(self):
        '''Helper to setup signal subscriptions of the current room'''

        room = self.user.room
        self.world.enter(room).subscribe(self.on_enter)
        self.world.leave(room).subscribe(self.on_leave)
        self.world.say(room).subscribe(self.on_say)

    @coroutine
    def handle_greeting(self, message):
        '''Handle a message during the greeting script.

        Once all needed information has been collected `user` will be set.
        '''

        if self.name is None:
            logger.debug('(S%s) Got username "%s"', id(self), message)
            self.name = message
            self.write_json(MSG_QUEST)

        elif self.quest is None:
            logger.debug('(S%s) Got quest "%s"', id(self), message)
            self.quest = message
            try:
                # Get a existing user or create a new one
                try:
                    user = yield from mud.User.get(self.db, self.name, self.quest)
                except KeyError:
                    user = yield from mud.User.create(self.db, self.name, self.quest)
            except:
                # Inform client of a rejected login
                logger.info('Rejecting login', exc_info=True)
                self.write_json({
                    'message': "That doesn't sound right"
                })
                self.user = None
                raise

            self.user = user
            self.subscribe_room()

            self.message('Welcome %s. Your quest is %s',
                         self.user.name, self.user.quest)
            yield from action.look(self)
        else:
            logger.warning('extra message to handle_greeting: %s', message)

    @coroutine
    def handle_command(self, message):
        # TODO: do something sane with message
        parts = message.split()

        if parts[0] == 'look':
            yield from action.look(self)

        elif parts[0] == 'go':
            yield from action.go(self, parts[1])

        elif parts[0] == 'say':
            yield from action.say(self, ' '.join(parts[1:]))

        else:
            self.message('.. what? %s' % parts[0])
