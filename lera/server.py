from asyncio import coroutine
from verktyg import App, WebSocket, serve_static
import logging
import functools
import itertools
from .session import Session

logger = logging.getLogger(__name__)

app = App()
seq = itertools.count()

@coroutine
def websocket_handler(sock):
    session = Session(sock)
    logger.info('WebSocket session started');

    yield from session.handle_greeting()

    while True:
        message = yield from sock.recv()

        if message is None:
            logger.info('WebSocket session closed (Session %s)', id(session));
            return

        s = next(seq)
        logger.info('processing message: [%s], %s', message, s)

        try:
            yield from session.handle_command(message)
        except:
            logger.exception('error when processing message %s', s)
        else:
            logger.debug('message processed %s', s)


@app.route('/socket')
@coroutine
def websocket(req, res):
    WebSocket.handshake(req, res)

    writer = req.environ.get('async.writer')
    reader = req.environ.get('async.reader')

    socket = WebSocket(websocket_handler)
    socket.claim_transport(writer.transport)

    res.headers['Upgrade'] = 'WebSocket'
    res.headers['Connection'] = 'Upgrade'
    res.status(101).end()


@app.route('/js/<path:path>')
@coroutine
def dev_static(req, res, path):
    res.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    serve_static(res, './js/%s' % path)


@app.route('/')
@coroutine
def index(req, res):
    serve_static(res, 'test.html')
