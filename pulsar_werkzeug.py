import logging
from functools import partial
from asyncio import coroutine, sleep
from verktyg import App, WebSocket, serve_static

logger = logging.getLogger(__name__)
app = App()


@coroutine
def handler(sock):
    yield from sock.send('what up')
    while True:
        message = yield from sock.recv()
        if message is None:
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

    connection = req.environ.get('pulsar.connection')
    if not connection:
        res.status(404).send(b'File not found')
        return

    factory = partial(WebSocket, handler)
    connection.upgrade(factory)
    res.status(102).send(b'')


if __name__ == '__main__':
    def pulsar_app(*args):
        return app(*args)

    from pulsar.apps.wsgi import WSGIServer
    WSGIServer(pulsar_app, debug=True, reload=True).start()
