import logging
from functools import partial
from asyncio import coroutine, sleep, get_event_loop
from verktyg import App, WebSocket, serve_static

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
app = App()


@coroutine
def handler(sock):
    yield from sock.send('what up')
    while True:
        message = yield from sock.recv()
        if message is None:
            print('no message')
            return
        print('message', message)


@app.route('/')
@coroutine
def index(req, res):
    res.send(b'index')


@app.route('/lazy')
@coroutine
def lazy(req, res):
    yield from sleep(1)
    res.status(201).send([b'lazy page'])


@app.route('/js/<path:path>')
@coroutine
def javascript(req, res, path):
    serve_static(res, './js/%s' % path)


@app.route('/socket')
@coroutine
def ws(req, res):
    WebSocket.handshake(req, res)

    reader = req.environ.get('async.reader')
    writer = req.environ.get('async.writer')

    socket = WebSocket(handler)
    socket.claim_transport(writer.transport)

    res.headers['Upgrade'] = 'WebSocket'
    res.headers['Connection'] = 'Upgrade'
    res.status(101).end()


if __name__ == '__main__':
    from aiohttp.wsgi import WSGIServerHttpProtocol

    loop = get_event_loop()
    f = loop.create_server(
        partial(WSGIServerHttpProtocol, app, debug=True, keep_alive=75),
        '0.0.0.0', '8060')
    srv = loop.run_until_complete(f)

    print('serving on %s' % (srv.sockets[0].getsockname(),))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
