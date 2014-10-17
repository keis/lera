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


urls = Map([
    Rule('/', endpoint=index),
    Rule('/lazy', endpoint=lazy)
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
