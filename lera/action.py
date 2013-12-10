'''
action

This module describe the various actions a actor can take
'''

from tornado.gen import coroutine
import logging
from . import riak
from .mud import Room

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
    session.world.say(user.room, name=user.name, message=message)


@coroutine
def go(session, label):
    user = session.user
    # Find room to go to
    try:
        key = yield user.find_exit(session.db, label)
    except KeyError:
        return session.message("You can't go %s", label)

    logger.info('%s moving from %s to %s', user.key, user.room, key[1])
    # Remove from old room
    Room.remove_occupant(session.db, user.room, user.key)

    session.disconnect_room()

    # Update room link
    user.room = key[1]
    yield user.save(session.db)

    # Add to new room
    yield Room.add_occupant(session.db, user.room, user.key)
    logger.info('%s moved to %s', user.key, user.room)

    session.subscribe_room()

    yield look(session)

