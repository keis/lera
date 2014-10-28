from asyncio import Task, coroutine
import time
import logging
import smoke
from . import riak, lang, model, rollback

logger = logging.getLogger(__name__)
starting_room = 'start'


class AsyncBroker(smoke.Broker):
    @coroutine
    def async_publish(self, event, **kwargs):
        super().publish(event, **kwargs)

    # https://github.com/keis/smoke/issues/1
    def publish(self, event, **kwargs):
        Task(async_publish(event, **kwargs))


class World(AsyncBroker):
    enter = smoke.signal('enter', 'room')
    leave = smoke.signal('leave', 'room')
    say = smoke.signal('say', 'room')

world = World()
rollback = rollback.Rollback([model.Room, model.User])


class Room(object):
    @classmethod
    @coroutine
    def get_occupants(cls, db, key):
        try:
            room = yield from model.Room.read(db, rollback, key)
        except KeyError as e:
            return []

        return room.occupants

    @classmethod
    @coroutine
    def remove_occupant(cls, db, key, occupant):
        txid = 'dummy-txid'

        room = yield from model.Room.read(db, rollback, key)

        try:
            room.remove_occupant(occupant, txid)
        except ValueError:
            pass
        else:
            logger.debug('updating occupants of %s', key)
            yield from room.save(db)
            world.leave(key, user=occupant, room=key)

    @classmethod
    @coroutine
    def add_occupant(cls, db, key, occupant):
        txid = 'dummy-txid'

        room = yield from model.Room.read(db, rollback, key)

        room.add_occupant(occupant, txid)

        logger.debug('updating occupants of %s', key)
        yield from room.save(db)
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

    @room.setter
    def room(self, room):
        self.data.change_room(room, 'dummy-tx')

    def describe(self, room, occupants):
        others = [o['name'] for o in occupants if o['name'] != self.name]
        out = room.description
        if len(others) > 0:
            out += '\n\nYou see %s here' % lang._and(others)
        return out

    @coroutine
    def find_exit(self, db, label):
        user = yield from model.User.read(db, rollback, self.key)
        room = yield from db.get('rooms', user.room)

        logger.debug("available exits from %s: %r", user.room, room.links)
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

        yield from user.save(db)
        yield from Room.add_occupant(db, user.room, user.key)

        return user

    @classmethod
    @coroutine
    def get(cls, db, name, quest):
        '''Retrieve a user from the database.

        If the given quest does not match the stored, ValueError is raised
        '''

        key = name.lower()

        try:
            data = yield from model.User.read(db, rollback, key)
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
