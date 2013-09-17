from tornado.gen import coroutine, Task
from tornado.ioloop import IOLoop
import time
import logging
import riak
import smoke

logger = logging.getLogger('mud')
starting_room = 'Tp10Fhl12GliqHtbRaBf86hPeKX'


class TornadoBroker(smoke.Broker):
    # https://github.com/keis/smoke/issues/1
    def publish(self, event, **kwargs):
        publish = super(Broker, self).publish
        IOLoop.instance().add_callback(publish, **kwargs)


class World(TornadoBroker):
    def __init__(self):
        self.rooms = {}

    def room(self, db, key):
        try:
            room = self.rooms[key]
        except KeyError as e:
            room = Room(db, key)
            self.rooms[key] = room
        return room
        

world = World()


class Room(smoke.Broker):
    enter = smoke.signal('enter')
    leave = smoke.signal('leave')

    def __init__(self, db, key):
        self.db = db
        self.key = key

    @coroutine
    def remove_occupant(self, occupant):
        try:
            occupants = yield self.db.get('occupants', self.key)
        except KeyError as e:
            pass
        else:
            try:
                occupants['occupants'].remove(occupant)
            except ValueError:
                pass
            else:
                yield self.db.save('occupants', self.key, occupants)
                self.leave(user=occupant, room=self.key)

    @coroutine
    def add_occupant(self, occupant):
        try:
            occupants = yield self.db.get('occupants', self.key)
        except KeyError as e:
            occupants = {'occupants': []}
        occupants['occupants'].append(occupant)
        yield self.db.save('occupants', self.key, occupants)
        self.enter(user=occupant, room=self.key)


class User(object):
    def __init__(self, db, data):
        self.db = db
        self.data = data

    def _on_enter(self, user=None, room=None):
        if room != self.room:
            raise smoke.Disconnect()
        if user != self.key:
            logger.debug('%s notices %s enters %s', self.key, user, room)

    def _on_leave(self, user=None, room=None):
        if room != self.room:
            raise smoke.Disconnect()
        if user != self.key and room == self.room:
            logger.debug('%s notices %s leaves %s', self.key, user, room)

    @property
    def key(self):
        return self.data['name'].lower()

    @property
    def name(self):
        return self.data['name']

    @property
    def quest(self):
        return self.data['quest']

    def describe(self, room):
        return room['description']

    @coroutine
    def look(self, what=None):
        q = riak.MapReduce()
        q.add(('users', self.key))
        q.link({'tag': 'room'})
        q.map({ 
            'language': 'javascript',
            'name': 'Riak.mapValuesJson'
        })
        # TODO: Load occupants and display somehow.
        (room,) = yield self.db.mapred(q)
        return self.describe(room)

    @coroutine
    def go(self, label):
        # Find room to go to
        q = riak.MapReduce()
        q.add(('users', self.key))
        q.link({'tag': 'room'})
        q.link({'tag': label})
        q.map({ 
            'language': 'javascript',
            'source': 'function (v) { return [[v.bucket, v.key], Riak.mapValuesJson(v)[0]]; }'
        })
        result = yield self.db.mapred(q)
        if result == []:
            return "You can't go %s" % label
        key, room = result

        logger.info('%s moving from %s to %s', self.key, self.room, key[1])
        # Remove from old room
        world.room(self.db, self.room).remove_occupant(self.key)

        # Update room link
        self.room = key[1]
        yield self.save()

        # Add to new room
        _room = world.room(self.db, self.room)
        yield _room.add_occupant(self.key)
        logger.info('%s moved to %s', self.key, self.room)

        _room.enter.subscribe(smoke.weak(self._on_enter))
        _room.leave.subscribe(smoke.weak(self._on_leave))

        return self.describe(room)

    @classmethod
    @coroutine
    def get(cls, db, name, quest):
        key = name.lower()

        try:
            data = yield db.get('users', key)
        except KeyError:
            logger.info('Creating new user: %s', name)
            user = cls(db, {'name': name, 'quest': quest})
            user.room = starting_room
            yield user.save()
        else:
            logger.info('user loaded: %s', data['name'])
            user = cls(db, data)
            user.room = data.links[0].key

        room = world.room(db, user.room)
        room.enter.subscribe(smoke.weak(user._on_enter))
        room.leave.subscribe(smoke.weak(user._on_leave))

        return user

    def save(self):
        links = [('rooms', self.room, 'room')]
        return self.db.save('users', self.key, self.data, links)
