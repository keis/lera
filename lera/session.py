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
    def handle_greeting(self):
        '''Handle a messages during the greeting script.

        Once all needed information has been collected `user` will be set.
        '''

        self.write_json(MSG_NAME)

        # Gather user details
        username = yield from self.socket.recv()
        logger.debug('(S%s) Got username "%s"', id(self), username)

        self.write_json(MSG_QUEST)

        quest = yield from self.socket.recv()
        logger.debug('(S%s) Got quest "%s"', id(self), quest)

        # Get an existing user or create a new one
        try:
            try:
                user = yield from mud.User.get(self.db, username, quest)
            except KeyError:
                user = yield from mud.User.create(self.db, username, quest)
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
                     username, quest)

        yield from action.look(self)


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
