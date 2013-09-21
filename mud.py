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
        IOLoop.instance().add_callback(super().publish, event, **kwargs)


class World(TornadoBroker):
    enter = smoke.signal('enter')
    leave = smoke.signal('leave')


world = World()


class Room(object):

    @classmethod
    @coroutine
    def remove_occupant(cls, db, key, occupant):
        try:
            occupants = yield db.get('occupants', key)
        except KeyError as e:
            pass
        else:
            try:
                occupants['occupants'].remove(occupant)
            except ValueError:
                pass
            else:
                yield db.save('occupants', key, occupants)
                world.publish((world.leave, key), user=occupant, room=key)

    @classmethod
    @coroutine
    def add_occupant(cls, db, key, occupant):
        try:
            occupants = yield db.get('occupants', key)
        except KeyError as e:
            occupants = {'occupants': []}
        occupants['occupants'].append(occupant)
        yield db.save('occupants', key, occupants)
        world.publish((world.enter, key), user=occupant, room=key)


class User(object):
    def __init__(self, session, data):
        self.session = session
        self.data = data
        self.on_enter = smoke.weak(self._on_enter)
        self.on_leave = smoke.weak(self._on_leave)

    def _on_enter(self, user=None, room=None):
        if room != self.room:
            raise smoke.Disconnect()
        if user != self.key:
            self.session.socket.write_json({
                'message': '%s enters the room' % user
            })

    def _on_leave(self, user=None, room=None):
        if room != self.room:
            raise smoke.Disconnect()
        if user != self.key and room == self.room:
            self.session.socket.write_json({
                'message': '%s leaves the room' % user
            })

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
        (room,) = yield self.session.db.mapred(q)
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
        result = yield self.session.db.mapred(q)
        if result == []:
            return "You can't go %s" % label
        key, room = result

        logger.info('%s moving from %s to %s', self.key, self.room, key[1])
        # Remove from old room
        Room.remove_occupant(self.session.db, self.room, self.key)

        world.disconnect((world.enter, self.room), self.on_enter)
        world.disconnect((world.leave, self.room), self.on_leave)

        # Update room link
        self.room = key[1]
        yield self.save()

        # Add to new room
        yield Room.add_occupant(self.session.db, self.room, self.key)
        logger.info('%s moved to %s', self.key, self.room)

        world.subscribe((world.enter, self.room), self.on_enter)
        world.subscribe((world.leave, self.room), self.on_leave)

        return self.describe(room)

    @classmethod
    @coroutine
    def get(cls, session, name, quest):
        key = name.lower()

        try:
            data = yield session.db.get('users', key)
        except KeyError:
            logger.info('Creating new user: %s', name)
            user = cls(session, {'name': name, 'quest': quest})
            user.room = starting_room
            yield user.save()
        else:
            logger.info('user loaded: %s', data['name'])
            user = cls(session, data)
            user.room = data.links[0].key

        world.subscribe((world.enter, user.room), user.on_enter)
        world.subscribe((world.leave, user.room), user.on_leave)

        return user

    def save(self):
        links = [('rooms', self.room, 'room')]
        return self.session.db.save('users', self.key, self.data, links)
