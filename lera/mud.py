from tornado.gen import coroutine, Task
from tornado.ioloop import IOLoop
import time
import logging
import smoke
from . import riak, lang, model

logger = logging.getLogger('mud')
starting_room = 'start'


class TornadoBroker(smoke.Broker):
    # https://github.com/keis/smoke/issues/1
    def publish(self, event, **kwargs):
        IOLoop.instance().add_callback(super().publish, event, **kwargs)


class World(TornadoBroker):
    enter = smoke.signal('enter', 'room')
    leave = smoke.signal('leave', 'room')
    say = smoke.signal('say', 'room')

world = World()


rollback = model.Rollback()


class Room(object):
    @classmethod
    @coroutine
    def get_occupants(cls, db, key):
        try:
            occupants = yield model.Occupants.read(db, rollback, key)
        except KeyError as e:
            return []

        return occupants.get()

    @classmethod
    @coroutine
    def remove_occupant(cls, db, key, occupant):
        txid = 'dummy-txid'

        try:
            occupants = yield model.Occupants.read(db, rollback, key)
        except KeyError as e:
            return

        try:
            occupants.add(occupant, txid)
        except ValueError:
            pass
        else:
            logger.debug('updating occupants of %s', key)
            yield occupants.save(db)
            world.leave(key, user=occupant, room=key)

    @classmethod
    @coroutine
    def add_occupant(cls, db, key, occupant):
        txid = 'dummy-txid'

        try:
            occupants = yield model.Occupants.read(db, rollback, key)
        except KeyError as e:
            occupants = model.Occupants.new(key)

        occupants.add(occupant, txid)
        logger.debug('updating occupants of %s', key)
        yield occupants.save(db)
        world.enter(key, user=occupant, room=key)


class User(object):
    def __init__(self, data):
        self.data = data

    @property
    def key(self):
        return self.data.name.lower()

    @property
    def name(self):
        return self.data.name

    @property
    def quest(self):
        return self.data.quest

    @property
    def room(self):
        return self.data.room

    def describe(self, room, occupants):
        others = [o['name'] for o in occupants if o['name'] != self.name]
        out = room['description']
        if len(others) > 0:
            out += '\n\nYou see %s here' % lang._and(others)
        return out

    @coroutine
    def find_exit(self, db, label):
        user = yield model.User.reads(db, rollback, self.key)

        roomlink = [x for x in user.qube.links if x.tag == 'room'][0]
        room = yield db.get('rooms', roomlink.key)

        exitlinks = [x for x in room.links if x.tag == label]

        if exitlinks == []:
            raise KeyError(label)

        return exitlinks[0]

    @classmethod
    @coroutine
    def create(cls, db, name, quest):
        '''Create a new user with the given name and quest.

        The user will be added to starting_room as defined by this module.
        '''

        logger.info('Creating new user: %s', name)

        user = cls(model.User.new(name, quest, starting_room))

        yield user.save(db)
        yield Room.add_occupant(db, user.room, user.key)

        return user

    @classmethod
    @coroutine
    def get(cls, db, name, quest):
        '''Retrieve a user from the database.

        If the given quest does not match the stored, ValueError is raised
        '''

        key = name.lower()

        try:
            data = yield model.User.read(db, rollback, key)
        except KeyError:
            logger.info("User not found %s", key)
            raise

        if data.quest != quest:
            raise ValueError("bad quest (was: %r, expected: %r)" % (data['quest'], quest))

        logger.info('user loaded: %s', data.name)
        user = cls(data)

        return user

    def save(self, db):
        return self.data.save(db)
