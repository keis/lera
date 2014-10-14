from tornado.gen import coroutine
import logging
import contextlib
import qube
from . import riak

logger = logging.getLogger(__name__)


class Model(object):
    '''A generic qube powered model stored in RIAK'''

    def __init__(self, qube):
        self.qube = qube

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.qube['data'])

    @property
    def key(self):
        return self.qube.key

    @property
    def vclock(self):
        return self.qube.vclock

    @property
    def links(self):
        return self.qube.links

    @classmethod
    @coroutine
    def read(cls, db, rollback, key):
        logger.debug("reading %s/%s", cls.bucket, key)

        modified = False
        rollbacks = rollback.txs

        @contextlib.contextmanager
        def queue_rollback(op):
            try:
                yield
            except Exception as e:
                logger.debug('operation failed %r', op)
                cls.queue_rollback(rollback, op)

        try:
            data = yield db.get(cls.bucket, key)

        except riak.Conflict as e:
            logger.debug("conflict in %s/%s", cls.bucket, key)
            modified = True
            data = qube.from_json(e.siblings.pop())

            for tx in rollbacks:
                qube.rollback(data, tx, queue_rollback)

            for r in e.siblings:
                r = qube.from_json(r)

                for tx in rollbacks:
                    qube.rollback(r, tx, queue_rollback)

                data = qube.merge(data, r, queue_rollback)

            links = data.links
            data = riak.Object(data)
            data.location = e.location
            data.vclock = e.vclock
            data.links = links

        except:
            logger.error("Other error reading", exc_info=True)
            raise

        else:
            try:
                data = qube.from_json(data)
            except:
                logger.error("failed to parse %s", data)
                raise

            if rollbacks:
                logger.debug("processing rollbacks in %s/%s %r", cls.bucket, key, rollbacks)

                try:
                    seq = data['sequence']
                    for tx in rollbacks:
                        data = qube.rollback(data, tx, queue_rollback)
                    modified = seq != data['sequence']
                except:
                    logger.error("error performing rollback", exc_info=True)
                    raise

        model = cls(data)
        if modified:
            # Ideally this would happen after returning the list
            yield model.save(db)
            yield rollback.process(db)

        logger.debug('read %s/%s %s', cls.bucket, key, data.vclock)
        return model

    @coroutine
    def save(self, db):
        logger.debug("saving %s/%s %s", self.bucket, self.key, self.vclock)

        data = qube.to_json(self.qube)
        yield db.save(self.bucket, self.key, data,
                      vclock=self.vclock,
                      links=self.links)


class Room(Model):
    bucket = 'rooms'

    @property
    def description(self):
        return self.qube['data']['description']

    @property
    def occupants(self):
        return self.qube['data']['occupants']

    def add_occupant(self, occupant, txid):
        qube.apply_op(self.qube, ('add', 'occupants', occupant, txid))

    def remove_occupant(self, occupant, txid):
        qube.apply_op(self.qube, ('rem', 'occupants', occupant, txid))

    @classmethod
    def queue_rollback(cls, rollback, op):
        txid = op[-1]
        rollback.queue('users', op[3], txid)


class User(Model):
    bucket = 'users'

    @property
    def name(self):
        return self.qube['data']['name']

    @property
    def quest(self):
        return self.qube['data']['quest']

    @property
    def room(self):
        return self.qube['data']['room']

    def change_room(self, key, txid):
        qube.apply_op(self.qube, ('change', 'room', (self.room, key), txid))

    @classmethod
    def new(cls, name, quest, location):
        data = riak.Object(qube.init({
            'name': name,
            'quest': quest,
            'room': location
        }))
        data.location = '/' + name.lower()
        data.links = [riak.link('rooms', location, 'room')]
        return cls(data)
