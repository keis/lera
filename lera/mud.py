from tornado.gen import coroutine, Task
from tornado.ioloop import IOLoop
import time
import logging
import smoke
import qube
import contextlib
from . import riak, lang

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


class Room(object):
    @classmethod
    @coroutine
    def read_occupants(cls, db, key):
        try:
            data = yield db.get('occupants', key)
        except riak.Conflict as e:
            rollback = []

            @contextlib.contextmanager
            def queue_rollback(op):
                txid = op[-1]
                try:
                    yield
                except Exception as e:
                    logger.debug('operation failed %r', op)
                    rollback.append({
                        'bucket': 'users',
                        'key': op[3],
                        'tx': txid})

            data = qube.from_json(e.siblings.pop())
            for r in e.siblings:
                data = qube.merge(data, qube.from_json(r), queue_rollback)

            # Ideally this would happen after returning the list
            yield db.save('occupants', key, qube.to_json(data), vclock=data.vclock)

            for tx in rollback:
                logger.info('should rollback %r', tx)

        return data

    @classmethod
    @coroutine
    def get_occupants(cls, db, key):
        try:
            data = yield cls.read_occupants(db, key)
            occupants = data['data']['occupants']
        except KeyError as e:
            return []

        return occupants

    @classmethod
    @coroutine
    def remove_occupant(cls, db, key, occupant):
        txid = 'dummy-txid'

        try:
            data = yield cls.read_occupants(db, key)
        except KeyError as e:
            pass
        else:
            try:
                qube.apply_op(data, ('rem', 'occupants', occupant, txid))
            except ValueError:
                pass
            else:
                logger.debug('updating occupants of %s, %r', key, data['data']['occupants'])
                yield db.save('occupants', key, qube.to_json(data), vclock=data.vclock)
                world.leave(key, user=occupant, room=key)

    @classmethod
    @coroutine
    def add_occupant(cls, db, key, occupant):
        txid = 'dummy-txid'

        try:
            data = yield cls.read_occupants(db, key)
        except KeyError as e:
            data = {
                'sequence': 0,
                'journal': [],
                'data': {
                    'occupants': occupants
                }
            }
        qube.apply_op(data, ('add', 'occupants', occupant, txid))
        logger.debug('updating occupants of %s, %r', key, data['data']['occupants'])
        yield db.save('occupants', key, qube.to_json(data), vclock=vclock)
        world.enter(key, user=occupant, room=key)


class User(object):
    def __init__(self, data):
        self.data = data

    @property
    def key(self):
        return self.data['name'].lower()

    @property
    def name(self):
        return self.data['name']

    @property
    def quest(self):
        return self.data['quest']

    def describe(self, room, occupants):
        others = [o['name'] for o in occupants if o['name'] != self.name]
        out = room['description']
        if len(others) > 0:
            out += '\n\nYou see %s here' % lang._and(others)
        return out

    @coroutine
    def find_exit(self, db, label):
        user = yield db.get('users', self.key)

        roomlink = [x for x in user.links if x.tag == 'room'][0]
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

        user = cls({'name': name, 'quest': quest})
        user.room = starting_room

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
            data = yield db.get('users', key)
        except KeyError:
            logger.info("User not found %s", key)
            raise

        if data['quest'] != quest:
            raise ValueError("bad quest (was: %r, expected: %r)" % (data['quest'], quest))

        logger.info('user loaded: %s', data['name'])
        user = cls(data)
        user.room = data.links[0].key

        return user

    def save(self, db):
        links = [('rooms', self.room, 'room')]
        return db.save('users', self.key, self.data, links)
