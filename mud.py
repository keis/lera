from tornado.gen import coroutine, Task
import time
import logging

logger = logging.getLogger('mud')


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
        yield Task(lambda callback: callback(time.sleep(0.2)))
        return "You are in a pitch black room, you are here %s" % self.quest

    @classmethod
    @coroutine
    def get(cls, db, name, quest):
        key = name.lower()

        try:
            data = yield db.get('users', key)
        except KeyError:
            logger.info('Creating new user: %s', name)
            user = cls(db, {'name': name, 'quest': quest})
            yield user.save()
        else:
            logger.info('user loaded: %s', data['name'])
            user = cls(db, data)

        return user

    def save(self):
        return self.db.save('users', self.key, self.data)       
