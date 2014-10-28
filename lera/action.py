'''
action

This module describe the various actions a actor can take
'''

from asyncio import coroutine
import logging
from . import riak, model
from .mud import Room, rollback

logger = logging.getLogger(__name__)


@coroutine
def look(session, what=None):
    user = yield from model.User.read(session.db, rollback, session.user.key)
    room = yield from model.Room.read(session.db, rollback, user.room)

    occupants = [{'name': key} for key in room.occupants]

    logger.info('look data %r %r', room, occupants)
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
        key = yield from user.find_exit(session.db, label)
    except KeyError:
        return session.message("You can't go %s", label)

    logger.info('%s moving from %s to %s', user.key, user.room, key[1])
    # Remove from old room
    Room.remove_occupant(session.db, user.room, user.key)

    session.disconnect_room()

    # Update room link
    user.room = key[1]
    yield from user.save(session.db)

    # Add to new room
    yield from Room.add_occupant(session.db, user.room, user.key)
    logger.info('%s moved to %s', user.key, user.room)

    session.subscribe_room()

    yield from look(session)
