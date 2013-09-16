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

    @coroutine
    def look(self, what=None):
        q = riak.MapReduce()
        q.add(('users', self.key))
        q.link({'tag': 'room'})
        q.map({ 
            'language': 'javascript',
            'name': 'Riak.mapValuesJson'
        })
        (room,) = yield self.db.mapred(q)
        return room['description']

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

        return user

    def save(self):
        links = [('rooms', self.room, 'room')]
        return self.db.save('users', self.key, self.data, links)
