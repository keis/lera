from tornado.gen import coroutine, Task
from tornado.ioloop import IOLoop
import time
import logging
import smoke
import riak
import lang

logger = logging.getLogger('mud')
starting_room = 'start'


class TornadoBroker(smoke.Broker):
    # https://github.com/keis/smoke/issues/1
    def publish(self, event, **kwargs):
        IOLoop.instance().add_callback(super().publish, event, **kwargs)


class World(TornadoBroker):
    enter = smoke.signal('enter')
    leave = smoke.signal('leave')
    say = smoke.signal('say')


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
        self.on_say = smoke.weak(self._on_say)

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
            self.message('%s leaves the room', user)

    def _on_say(self, name=None, message=None):
        if name == self.name:
            self.message('You say %s' % (message,))
        else:
            self.message('%s says %s' % (name, message))


    @property
    def key(self):
        return self.data['name'].lower()

    @property
    def name(self):
        return self.data['name']

    @property
    def quest(self):
        return self.data['quest']

    def message(self, frmt, *args):
        self.session.socket.write_json({
            'message': frmt % args
        })

    def describe(self, room, occupants):
        others = [o for o in occupants if o['name'] != self.name]
        out = room['description']
        if len(others) > 0:
            out += '\n\nYou see %s here' % lang._and([o['name'] for o in others])
        return out

    @coroutine
    def find_exit(self, label):
        q = riak.MapReduce()
        q.add(('users', self.key))
        q.link({'tag': 'room'})
        q.link({'tag': label})
        result = yield self.session.db.mapred(q)
        if result == []:
            raise KeyError(label)
        return result[0]

    @coroutine
    def look(self, what=None):
        q = riak.MapReduce()
        q.add(('users', self.key))
        q.link({'tag': 'room'})
        q.map({
            'language': 'javascript',
            'source': 'function (v) { var data = Riak.mapValuesJson(v); data[0].key = v.key; return [data[0]]; }',
            'keep': True
        })
        q.reduce({
            'language': 'javascript',
            'source': 'function (v) { return [["occupants", v[0].key]]; }'
        })
        q.reduce({
            'language': 'javascript',
            'name': 'Riak.filterNotFound'
        })
        q.map({
            'language': 'javascript',
            'source': 'function (v) { var data = Riak.mapValuesJson(v); oc = data[0].occupants; return oc && oc.map(function (o) { return ["users", o]; }); }'
        })
        q.map({
            'language': 'javascript',
            'name': 'Riak.mapValuesJson'
        })
        data = yield self.session.db.mapred(q)
        logger.debug("look data %r", data)
        ((room,), occupants) = data if len(data) == 2 else (data[0], [])
        self.message(self.describe(room, occupants))

    @coroutine
    def say(self, message):
        world.publish((world.say, self.room), name=self.name, message=message)

    @coroutine
    def go(self, label):
        # Find room to go to
        try:
            key = yield self.find_exit(label)
        except KeyError:
            return self.message("You can't go %s", label)

        logger.info('%s moving from %s to %s', self.key, self.room, key[1])
        # Remove from old room
        Room.remove_occupant(self.session.db, self.room, self.key)

        world.disconnect((world.enter, self.room), self.on_enter)
        world.disconnect((world.leave, self.room), self.on_leave)
        world.disconnect((world.say, self.room), self.on_say)

        # Update room link
        self.room = key[1]
        yield self.save()

        # Add to new room
        yield Room.add_occupant(self.session.db, self.room, self.key)
        logger.info('%s moved to %s', self.key, self.room)

        world.subscribe((world.enter, self.room), self.on_enter)
        world.subscribe((world.leave, self.room), self.on_leave)
        world.subscribe((world.say, self.room), self.on_say)

        yield self.look()

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
            yield Room.add_occupant(session.db, user.room, user.key)
        else:
            logger.info('user loaded: %s', data['name'])
            if data['quest'] != quest:
                raise ValueError("bad quest (was: %r, expected: %r)" % (data['quest'], quest))
            user = cls(session, data)
            user.room = data.links[0].key

        world.subscribe((world.enter, user.room), user.on_enter)
        world.subscribe((world.leave, user.room), user.on_leave)
        world.subscribe((world.say, user.room), user.on_say)

        return user

    def save(self):
        links = [('rooms', self.room, 'room')]
        return self.session.db.save('users', self.key, self.data, links)
