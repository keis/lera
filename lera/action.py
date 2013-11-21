'''
action

This module describe the various actions a actor can take
'''

from tornado.gen import coroutine
import logging
from . import riak

logger = logging.getLogger('session')


@coroutine
def look(session, what=None):
    q = riak.MapReduce()
    q.add(('users', session.user.key))
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
        'source': 'function (v) { var data = Riak.mapValuesJson(v); oc = data[0].occupants || []; return oc.map(function (o) { return ["users", o]; }); }'
    })
    q.map({
        'language': 'javascript',
        'name': 'Riak.mapValuesJson'
    })
    data = yield session.db.mapred(q)
    logger.debug("look data %r", data)
    ((room,), occupants) = data if len(data) == 2 else (data[0], [])

    session.message(session.user.describe(room, occupants))


@coroutine
def say(session, message):
    user = session.user
    session.world.publish((world.say, user.room), name=user.name, message=message)


@coroutine
def go(session, label):
    user = session.user
    # Find room to go to
    try:
        key = yield user.find_exit(label)
    except KeyError:
        return session.message("You can't go %s", label)

    logger.info('%s moving from %s to %s', user.key, user.room, key[1])
    # Remove from old room
    Room.remove_occupant(session.db, user.room, user.key)

    session.world.disconnect((session.world.enter, user.room), session.on_enter)
    session.world.disconnect((session.world.leave, user.room), session.on_leave)
    session.world.disconnect((session.world.say, user.room), session.on_say)

    # Update room link
    self.room = key[1]
    yield self.save()

    # Add to new room
    yield Room.add_occupant(session.db, user.room, user.key)
    logger.info('%s moved to %s', self.key, self.room)

    session.world.subscribe((session.world.enter, user.room), session.on_enter)
    session.world.subscribe((session.world.leave, user.room), session.on_leave)
    session.world.subscribe((session.world.say, user.room), session.on_say)

    yield look(session)

