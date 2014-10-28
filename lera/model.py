from asyncio import coroutine
import logging
import contextlib
import qube
from . import riak

logger = logging.getLogger(__name__)


class Model(object):
    '''A generic qube powered model stored in RIAK'''

    def __init__(self, key, qube, vclock=None, links=None):
        self.key = key
        self.qube = qube
        self.vclock = vclock
        self.links = links

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.qube['data'])

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
            response = yield from db.get(cls.bucket, key)

        except riak.Conflict as e:
            logger.debug("conflict in %s/%s", cls.bucket, key)
            modified = True
            first = e.siblings.pop()

            links = first.links
            vclock = e.vclock
            data = qube.from_json(first)

            for tx in rollbacks:
                qube.rollback(data, tx, queue_rollback)

            for r in e.siblings:
                r = qube.from_json(r)

                for tx in rollbacks:
                    qube.rollback(r, tx, queue_rollback)

                data = qube.merge(data, r, queue_rollback)

        except:
            logger.error("Other error reading", exc_info=True)
            raise

        else:
            links = response.links
            vclock = response.vclock
            data = qube.from_json(response)

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

        model = cls(key, data, vclock=vclock, links=links)

        if modified:
            # Ideally this would happen after returning the list
            # TODO: Task()
            yield from model.save(db)
            yield from rollback.process(db)

        logger.debug('read %s/%s %s', cls.bucket, key, vclock)
        return model

    @coroutine
    def save(self, db):
        logger.debug("saving %s/%s %s", self.bucket, self.key, self.vclock)

        data = qube.to_json(self.qube)
        yield from db.save(self.bucket, self.key, data,
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
        data = qube.init({
            'name': name,
            'quest': quest,
            'room': location
        })
        links=[riak.link('rooms', location, 'room')]

        return cls(name.lower(), data, links=links)
