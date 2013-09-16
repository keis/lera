from tornado.gen import coroutine, Task
import time
import logging
import riak


logger = logging.getLogger('mud')
starting_room = 'Tp10Fhl12GliqHtbRaBf86hPeKX'


class User(object):
    def __init__(self, db, data):
        self.db = db
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

        # Remove from old room
        try:
            old_occupants = yield self.db.get('occupants', self.room)
        except KeyError as e:
            pass
        else:
            old_occupants['occupants'].remove(self.key)
            yield self.db.save('occupants', self.room, old_occupants)

        # Update room link
        self.room = key[1]
        yield self.save()

        # Add to new room
        try:
            new_occupants = yield self.db.get('occupants', self.room)
        except KeyError as e:
            new_occupants = {'occupants': []}
        new_occupants['occupants'].append(self.key)
        yield self.db.save('occupants', self.room, new_occupants)

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

        return user

    def save(self):
        links = [('rooms', self.room, 'room')]
        return self.db.save('users', self.key, self.data, links)
