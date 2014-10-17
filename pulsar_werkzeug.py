from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Request
#from asyncio import coroutine, Future, Task, sleep
from trollius import coroutine, Future, Task, sleep


from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.datastructures import Headers

class Response(Future):
    '''connect/express inspired response object'''

    default_status = 200
    default_mimetype = 'text/plain'

    @property
    def status_code(self):
        return self._status_code

    @status_code.setter
    def status_code(self, code):
        self._status_code = code
        try:
            self._status = '%d %s' % (code, HTTP_STATUS_CODES[code].upper())
        except KeyError:
            self._status = '%d UNKNOWN' % code

    def __init__(self, environ, start_response):
        super(Response, self).__init__()
        self.environ = environ
        self.start_response = start_response
        self.headers = Headers()
        self.status_code = self.default_status
        self.headers['Content-Type'] = self.default_status

    def status(self, code):
        self.status_code = code
        return self

    def send(self, result):
        if isinstance(result, bytes):
            result = [result]

        headers = self.headers.to_wsgi_list()
        self.start_response(self._status, headers)

        self.set_result(result)
        return self


@coroutine
def index(req, res):
    res.send(b'index')


@coroutine
def lazy(req, res):
    yield from sleep(1)
    res.status(201).send([b'lazy page'])


def read_file(path):
    chunk_size = 64 * 1024
    with open(path, 'rb') as f:
        while True:
            chunk  = f.read(chunk_size)
            if chunk:
                yield chunk
            else:
                return


@coroutine
def javascript(req, res, path):
    path = './js/%s' % path
    try:
        gen = read_file(path)
    except FileNotFoundError as e:
        res.status(404).send(b'File not found')
        return

    res.status(200).send(gen)


from pulsar.apps.ws import WebSocket, WebSocketProtocol
from functools import partial


class Handler(object):
    def on_message(self, sock, message):
        print("message", message)

    def on_open(self, sock):
        sock.write('what up')
        print("open", sock)

    def on_close(self, sock):
        print("close", sock)


wsr = WebSocket('/websocket', Handler())

@coroutine
def ws(req, res):
    headers_parser = wsr.handle_handshake(req.environ)

    if not headers_parser:
        res.status(404).send(b'File not found')
        return

    headers, parser = headers_parser

    connection = req.environ.get('pulsar.connection')
    if not connection:
        res.status(404).send(b'File not found')
        return

    factory = partial(WebSocketProtocol, req, wsr.handle, parser)
    connection.upgrade(factory)

    for k,v in headers:
        res.headers[k] = v
    res.status(102).send(b'')


urls = Map([
    Rule('/', endpoint=index),
    Rule('/lazy', endpoint=lazy),
    Rule('/js/<path:path>', endpoint=javascript),
    Rule('/socket', endpoint=ws)
])


def dispatch_request(req, res):
    adapter = urls.bind_to_environ(req.environ)
    try:
        endpoint, values = adapter.match()
        return endpoint(req, res, **values)
    except HTTPException as e:
        return e


def app(environ, start_response):
    request = Request(environ)
    response = Response(environ, start_response)
    Task(dispatch_request(request, response))
    return response


if __name__ == '__main__':
    from pulsar.apps.wsgi import WSGIServer
    WSGIServer(app, debug=True, reload=True).start()
