import logging
from trollius import async
from asyncio import Task, Future, coroutine
from werkzeug.routing import Map, Rule
from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Request
from functools import partial
from websockets import handshake, protocol

logger = logging.getLogger(__name__)


class App(object):
    def __init__(self):
        self.urls = Map()

    def route(self, pat):
        def decorator(fun):
            self.urls.add(Rule(pat, endpoint=fun))

        return decorator

    def dispatch_request(self, req, res):
        adapter = self.urls.bind_to_environ(req.environ)
        try:
            endpoint, values = adapter.match()
            return endpoint(req, res, **values)
        except HTTPException as e:
            return e

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = Response(environ, start_response)
        Task(self.dispatch_request(request, response))
        return response


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


class WebSocket(protocol.WebSocketCommonProtocol):
    def __init__(self, ws_handler, *, loop=None, **kwargs):
        self.handler = ws_handler
        super().__init__(**kwargs)
        async(self.run_handler())

    @classmethod
    def handshake(self, req, res):
        key = handshake.check_request(req.headers.__getitem__)
        res.headers['Sec-Websocket-Accept'] = handshake.accept(key)
        return key

    @coroutine
    def run_handler(self):
        try:
            yield from self.handler(self)
        except Exception:
            logger.error("Exception in connection handler", exc_info=True)
            yield from self.fail_connection(1011)
            raise

    def _data_received(self, data):
        self.data_received(data)

    def copy_many_times_events(self, *args):
        pass


def read_file(path):
    chunk_size = 64 * 1024
    with open(path, 'rb') as f:
        while True:
            chunk  = f.read(chunk_size)
            if chunk:
                yield chunk
            else:
                return


def serve_static(res, path):
    try:
        gen = read_file(path)
    except FileNotFoundError as e:
        res.status(404).send(b'File not found')
        return

    res.status(200).send(gen)
